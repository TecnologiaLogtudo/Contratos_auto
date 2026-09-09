from __future__ import annotations

import re
from datetime import datetime, date
from typing import Optional
from playwright.sync_api import Page

from ...domain.models import ItemContrato
from ...domain.errors import QuoteExtractionError
from .base_strategy import BaseStrategy


def extrair_numero_nf(obs_interna: str) -> Optional[str]:
    """Extrai o número da Nota Fiscal a partir da observação com regex flexível."""
    if not obs_interna:
        return None
    # Suporta: nf-123, nf: 123, nf 123, nfe 123, danfe 123, nf-012345
    match = re.search(r'(?:nf|nfe|danfe)[-:\s]*(\d+)', obs_interna, re.IGNORECASE)
    if match:
        return match.group(1)
    return None


class LactalisBaseStrategy(BaseStrategy):
    """Regras base compartilhadas por todas as modalidades Lactalis."""

    def match(self, remetente: str) -> bool:
        rem = (remetente or "").lower()
        return "lactalis" in rem or "43.340.312" in rem or "43340312" in rem

    def require_data_pagamento(self) -> bool:
        return False

    def require_validade(self) -> bool:
        return True

    def get_termo_busca_perfil(self, cidade_planilha: str) -> str:
        return "lactalis BA"

    def get_valor_km(self, default_km: str = "20") -> str:
        return "1"

    def get_ncm_pesquisa(self) -> str:
        return "0403"

    def get_ncm_valor(self) -> str:
        return "0403."

    def get_data_programada(self, item: ItemContrato) -> Optional[str]:
        """
        Calcula a data programada da Lactalis baseada na Validade:
        - Dia <= 15: dia 05 do mês seguinte.
        - Dia > 15: dia 20 do mês seguinte.
        """
        if not item.validade:
            return None

        val_raw = item.validade.strip()
        try:
            val_date: Optional[datetime] = None
            match_pt = re.search(r'(\d{1,2})[-/](\d{1,2})[-/](\d{4})', val_raw)
            match_en = re.search(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', val_raw)

            if match_pt:
                val_date = datetime(int(match_pt.group(3)), int(match_pt.group(2)), int(match_pt.group(1)))
            elif match_en:
                val_date = datetime(int(match_en.group(1)), int(match_en.group(2)), int(match_en.group(3)))
            
            if not val_date:
                return None

            novo_mes = val_date.month + 1
            novo_ano = val_date.year
            if novo_mes > 12:
                novo_mes = 1
                novo_ano += 1

            novo_dia = 5 if val_date.day <= 15 else 20
            return f"{novo_dia:02d}/{novo_mes:02d}/{novo_ano}"
        except Exception:
            return None


class LactalisDiariaParadaStrategy(LactalisBaseStrategy):
    """Estratégia Lactalis: Diária Parado."""

    def match(self, remetente: str) -> bool:
        rem = (remetente or "").lower()
        return super().match(remetente) and not any(kw in rem for kw in ["pernoite", "diaria em rota", "diaria no cliente", "diaria garantida"])

    def get_complemento_pedido(self, item: ItemContrato) -> str:
        return "DIARIA PARADO"

    def get_regra_frete_id(self) -> str:
        return "146"  # Cotação Varejo (146)

    def get_fim_viagem(self, page: Page, item: ItemContrato) -> Optional[str]:
        try:
            return page.input_value('input[name="dados_dtEmissaoRF"]')
        except Exception:
            return None

    def get_observacao_contrato(self, item: ItemContrato) -> str:
        val_str = item.validade or ""
        return f"DIARIA PARADA {val_str}".strip()


class LactalisSpecialBaseStrategy(LactalisBaseStrategy):
    """Estratégia base para fluxos Lactalis especiais (Pernoite, Diária em Rota, Diária Garantida)."""

    def get_cidade_origem(self, cidade_planilha: str) -> str:
        return "Simões filho"

    def get_complemento_pedido(self, item: ItemContrato) -> str:
        rem = (item.remetente or "").lower()
        if "diaria garantida" in rem:
            return "Diaria Garantida"
        return "Diaria no cliente"

    def get_observacao_pv(self, item: ItemContrato) -> str:
        return item.extracted_obs_interna or item.nro_cotacao

    def get_fim_viagem(self, page: Page, item: ItemContrato) -> Optional[str]:
        try:
            return page.input_value('input[name="dados_dtEmissaoRF"]')
        except Exception:
            return None

    def get_observacao_contrato(self, item: ItemContrato) -> str:
        obs_text = item.extracted_obs_interna or ""
        validade_str = item.validade or ""
        
        # Normaliza a data da observação para a data da validade
        if validade_str and obs_text:
            cleaned = re.sub(r'\d{2}/\d{2}/\d{4}', validade_str, obs_text)
            cleaned = re.sub(r'\d{2}/\d{2}/\d{2}(?!\d)', validade_str, cleaned)
            return " ".join(cleaned.split())
        return obs_text


class LactalisPernoiteStrategy(LactalisSpecialBaseStrategy):
    def match(self, remetente: str) -> bool:
        rem = (remetente or "").lower()
        return super().match(remetente) and any(kw in rem for kw in ["pernoite", "diaria em rota", "diaria no cliente"])


class LactalisDiariaGarantidaStrategy(LactalisSpecialBaseStrategy):
    def match(self, remetente: str) -> bool:
        rem = (remetente or "").lower()
        return super().match(remetente) and "diaria garantida" in rem
