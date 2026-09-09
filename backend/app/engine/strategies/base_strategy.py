from __future__ import annotations

import abc
from typing import Callable, Optional
from playwright.sync_api import Page

from ...domain.models import ItemContrato


class BaseStrategy(abc.ABC):
    """Contrato base para estratégias polimórficas de clientes/remetentes."""

    @abc.abstractmethod
    def match(self, remetente: str) -> bool:
        """Retorna True se a estratégia for aplicável ao remetente da planilha."""
        pass

    def require_data_pagamento(self) -> bool:
        """Indica se a data de pagamento é obrigatória na planilha."""
        return True

    def require_validade(self) -> bool:
        """Indica se a data de validade é obrigatória na planilha."""
        return False

    def deve_emitir_recibo_frete(self) -> bool:
        """Retorna se o checkbox 'Emitir Recibo de Frete' deve ser marcado na Fase 3."""
        return True

    def get_complemento_pedido(self, item: ItemContrato) -> Optional[str]:
        """Valor a ser preenchido no campo dados_complementoPedido."""
        return item.nro_cotacao

    def get_cidade_origem(self, cidade_planilha: str) -> str:
        """Retorna o nome da cidade para busca no campo Origem (Fase 4)."""
        return cidade_planilha

    def get_regra_frete_id(self) -> str:
        """Retorna o ID do select da Regra de Frete (Fase 4). Padrão: 40 (Não realiza cálculos)."""
        return "40"

    def get_observacao_pv(self, item: ItemContrato) -> str:
        """Monta o texto para a observação PV (Fase 4). Padrão: 'Nome - Placa'."""
        partes = []
        if item.nome and item.nome != "NOME NÃO ENCONTRADO":
            partes.append(item.nome)
        if item.placa and item.placa != "PLACA NÃO ENCONTRADA":
            partes.append(item.placa)
        return " - ".join(partes)

    def get_fim_viagem(self, page: Page, item: ItemContrato) -> Optional[str]:
        """Retorna a data e hora do fim da viagem para a Fase 5."""
        if item.data_pagamento and item.data_pagamento != "DATA NÃO ENCONTRADA":
            return f"{item.data_pagamento} 12:00"
        return None

    def get_termo_busca_perfil(self, cidade_planilha: str) -> str:
        """Retorna o termo de busca para o Perfil de Apropriação (Fase 5)."""
        return cidade_planilha

    def get_valor_km(self, default_km: str = "20") -> str:
        """Retorna a quilometragem a ser preenchida na Fase 5."""
        return default_km

    def get_ncm_pesquisa(self) -> str:
        """Termo para pesquisar o NCM (Fase 5)."""
        return "vinho"

    def get_ncm_valor(self) -> str:
        """Valor do NCM a selecionar (Fase 5)."""
        return "2204."

    def get_observacao_contrato(self, item: ItemContrato) -> str:
        """Retorna o texto de observação final do contrato (Fase 5)."""
        return "Contrato Diária"

    def get_data_programada(self, item: ItemContrato) -> Optional[str]:
        """Retorna a data programada para o pagamento do saldo (Fase 5)."""
        return item.data_pagamento if item.data_pagamento != "DATA NÃO ENCONTRADA" else None
