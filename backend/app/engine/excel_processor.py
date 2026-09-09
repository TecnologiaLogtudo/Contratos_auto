from __future__ import annotations

import os
import re
import threading
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, List, Optional, Tuple

import openpyxl
from openpyxl.styles import PatternFill
import xlrd

from ..domain.models import ItemContrato, ItemStatus
from ..domain.errors import SpreadsheetValidationError
from .sanitizer import sanitize_bsoft_xls, sanitize_bsoft_xlsx, NormalizedSpreadsheet

# Regex aprimorado para placas brasileiras com word boundaries
PLACA_REGEX = re.compile(
    r'\b((?:[A-Z]{3}[ -]?(?:\d{4}|\d[A-Z]\d{2}))|(?:[A-Z]{3} ?[A-Z]{2}\d{2}))\b',
    re.IGNORECASE
)

# Regex para limpar ruídos comuns do campo Nome/Motorista
NOME_CLEANUP_REGEX = re.compile(
    r'(\d{1,2}:\d{2}|\d{1,2}h\d{2}|\d{1,2}h(?!\d)|h(?!\w)|VIAGEM EXTRA|RASTREADOR)',
    re.IGNORECASE
)

# Regex para encontrar datas de pagamento (DD/MM/AA ou DD/MM/AAAA)
DATA_PAGAMENTO_REGEX = re.compile(r'(\d{2}/\d{2}/\d{2,4})')

# Cabeçalhos padrão para as abas de resultado
HEADERS_PROCESSADOS = [
    "Nro cotação", "Categoria veículo", "Cidade", "UF", "Nome", "Placa",
    "Data pagamento", "Viagem extra", "Remetente", "Validade", "Frete a pagar",
    "Frete negociado", "Status"
]

HEADERS_NAO_REALIZADO = [
    "Nro cotação", "Categoria veículo", "Cidade", "UF", "Nome", "Placa",
    "Data pagamento", "Observação", "Status"
]

GREEN_FILL = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")


def _remover_acentos(texto: str) -> str:
    nfkd_form = unicodedata.normalize('NFKD', str(texto or ""))
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])


def padronizar_cidade(cidade: str) -> str:
    """Padroniza nomes de cidades para compatibilidade com o sistema LogTudo."""
    mapeamento = {
        "JOAO PESSOA": "J. Pessoa",
        "BAYEUX": "J. Pessoa",
        "CAMACARI": "Salvador",
        "SIMOES FILHO": "Salvador",
        "SALVADOR": "Salvador",
        "SERRA": "Vitória",
        "CARIACICA": "Vitória",
        "VILA VELHA": "Vitória",
        "VITORIA": "Vitória",
    }
    normalizada = _remover_acentos(cidade).strip().upper()
    return mapeamento.get(normalizada, str(cidade).strip())


def processar_cidade_uf(raw_val: Any, line_num: int = 0) -> Tuple[str, str]:
    """Separa 'Cidade/UF' em duas strings e padroniza a cidade."""
    if not raw_val or not isinstance(raw_val, str) or "/" not in raw_val:
        cidade_bruta = str(raw_val or "").strip()
        return padronizar_cidade(cidade_bruta) if cidade_bruta else "CIDADE NÃO ENCONTRADA", "UF NÃO ENCONTRADA"
    
    parts = raw_val.split("/")
    cidade = parts[0].strip()
    uf = parts[1].strip() if len(parts) > 1 else ""
    return padronizar_cidade(cidade), uf


def processar_nome_placa(raw_val: Any, line_num: int = 0) -> Tuple[str, str, str, str]:
    """
    Extrai do campo bruto: Nome limpo, Placa formatada, Data de pagamento e flag de Viagem Extra.
    """
    raw_str = str(raw_val or "").strip()
    if not raw_str:
        return "NOME NÃO ENCONTRADO", "PLACA NÃO ENCONTRADA", "DATA NÃO ENCONTRADA", "Não"

    # 1. Viagem extra
    viagem_extra = "Sim" if re.search(r'viagem\s+extra', raw_str, re.IGNORECASE) else "Não"

    # Limpa ruídos operacionais prévios para evitar colisões no regex de placa
    str_sanitizada = re.sub(r'\b(pernoite|di[aá]ria\s+garantida|nf\s*-?\s*\d+|sr\s*-?\s*\d+|\d{5,})\b', '', raw_str, flags=re.IGNORECASE).strip()

    # 2. Placa
    placa = "PLACA NÃO ENCONTRADA"
    nome_bruto = str_sanitizada
    match_placa = PLACA_REGEX.search(str_sanitizada)
    if match_placa:
        placa = match_placa.group(1).upper().replace(" ", "").replace("-", "")
        nome_bruto = PLACA_REGEX.sub('', str_sanitizada).strip()
    else:
        # Fallback na string original
        match_orig = PLACA_REGEX.search(raw_str)
        if match_orig:
            placa = match_orig.group(1).upper().replace(" ", "").replace("-", "")
            nome_bruto = PLACA_REGEX.sub('', str_sanitizada).strip()

    # 3. Data de pagamento
    data_pagamento = "DATA NÃO ENCONTRADA"
    match_data = DATA_PAGAMENTO_REGEX.search(nome_bruto)
    if match_data:
        data_pagamento = match_data.group(1)
        nome_bruto = DATA_PAGAMENTO_REGEX.sub('', nome_bruto).strip()

    # 4. Limpeza do Nome
    nome = "NOME NÃO ENCONTRADO"
    if nome_bruto:
        nome_limpo = re.sub(r'\b(pernoite|di[aá]ria\s+garantida|nf\s*-?\s*\d+|sr\s*-?\s*\d+|\d{5,})\b', '', nome_bruto, flags=re.IGNORECASE)
        nome_limpo = re.sub(r'(as|às)\s+(?=\d{1,2}:\d{2}|\d{1,2}h\d{2}|\d{1,2}h(?!\d)|h(?!\w))', '', nome_limpo, flags=re.IGNORECASE)
        nome_limpo = NOME_CLEANUP_REGEX.sub('', nome_limpo)
        nome_limpo = nome_limpo.replace('-', '')
        nome_limpo = re.sub(r'\s+', ' ', nome_limpo).strip()

        if nome_limpo and not (re.search(r'\d', nome_limpo) or '&#' in nome_limpo):
            nome = nome_limpo

    return nome, placa, data_pagamento, viagem_extra


@dataclass
class PreValidationReport:
    is_valid: bool
    total_rows: int
    valid_rows_count: int
    invalid_rows_count: int
    already_completed_count: int = 0
    pending_rows_count: int = 0
    missing_mandatory_columns: list[str] = field(default_factory=list)
    row_errors: list[dict] = field(default_factory=list)
    preview: list[dict] = field(default_factory=list)


class ExcelProcessor:
    """
    Manipulador de planilhas in-memory com sanitização BSoft integrada e persistência atômica.
    Suporta layouts variáveis, cabeçalhos deslocados e validação pré-upload rigorosa.
    """

    def __init__(self, filepath: str | Path, log_callback: Optional[Callable[[str, str], None]] = None):
        self.filepath = Path(filepath)
        self.log_callback = log_callback or (lambda m, l="INFO": None)
        self.items: list[ItemContrato] = []
        self.validation_errors: list[Tuple[ItemContrato, str]] = []
        self._lock = threading.RLock()
        self.is_already_treated = False

    def emit(self, message: str, level: str = "INFO") -> None:
        self.log_callback(message, level)

    def validate_upload(self) -> PreValidationReport:
        """
        Executa validação prévia detalhada da planilha antes de liberar o botão de emissão.
        Verifica presença de colunas obrigatórias, preenchimento de campos essenciais e formatos.
        """
        if not self.filepath.exists():
            return PreValidationReport(
                is_valid=False, total_rows=0, valid_rows_count=0, invalid_rows_count=0,
                missing_mandatory_columns=["Arquivo não encontrado"]
            )

        try:
            items = self.load_and_parse()
        except Exception as e:
            return PreValidationReport(
                is_valid=False, total_rows=0, valid_rows_count=0, invalid_rows_count=0,
                missing_mandatory_columns=[f"Erro ao ler arquivo: {e}"]
            )

        total_rows = len(items) + len(self.validation_errors)
        valid_rows = len(items)
        invalid_rows = len(self.validation_errors)
        already_completed = sum(1 for i in items if i.status == ItemStatus.CONCLUIDO)
        pending_rows = sum(1 for i in items if i.status == ItemStatus.PENDENTE)

        row_errors = []
        for item, motivo in self.validation_errors:
            row_errors.append({
                "row_index": item.row_index,
                "nro_cotacao": item.nro_cotacao,
                "motivo": motivo,
            })

        preview = [i.model_dump() for i in items[:10]]

        # É considerado válido para emissão se houver ao menos 1 item válido
        is_valid = valid_rows > 0

        return PreValidationReport(
            is_valid=is_valid,
            total_rows=total_rows,
            valid_rows_count=valid_rows,
            invalid_rows_count=invalid_rows,
            already_completed_count=already_completed,
            pending_rows_count=pending_rows,
            row_errors=row_errors,
            preview=preview,
        )

    def load_and_parse(self) -> list[ItemContrato]:
        """Carrega, sanitiza e trata a planilha de origem."""
        with self._lock:
            self.items.clear()
            self.validation_errors.clear()

            if not self.filepath.exists():
                raise FileNotFoundError(f"Arquivo não encontrado: {self.filepath}")

            suffix = self.filepath.suffix.lower()
            if suffix not in {".xlsx", ".xls"}:
                raise SpreadsheetValidationError(f"Extensão não suportada: {suffix}")

            self.is_already_treated = self._check_is_treated()
            if self.is_already_treated:
                self.emit("[F1] Planilha já tratada detectada. Carregando dados diretamente...", "INFO")
                self._load_already_treated()
            else:
                self.emit("[F1] Aplicando auto-detecção de cabeçalho e sanitização BSoft...", "INFO")
                normalized = sanitize_bsoft_xls(self.filepath) if suffix == ".xls" else sanitize_bsoft_xlsx(self.filepath)
                self._process_normalized_spreadsheet(normalized)

            self.emit(f"[F1] Leitura concluída: {len(self.items)} itens válidos, {len(self.validation_errors)} com falha de validação.", "SUCESSO")
            return self.items

    def _check_is_treated(self) -> bool:
        """Verifica se os cabeçalhos correspondem exatamente a uma planilha já tratada."""
        try:
            if self.filepath.suffix.lower() == ".xls":
                wb = xlrd.open_workbook(str(self.filepath), formatting_info=False)
                sheet = wb.sheet_by_index(0)
                if sheet.nrows > 0:
                    headers = [str(c).strip() for c in sheet.row_values(0) if str(c).strip()]
                    return headers == HEADERS_PROCESSADOS
            else:
                wb = openpyxl.load_workbook(self.filepath, read_only=True, data_only=True)
                ws = wb.active
                if ws and ws.max_row > 0:
                    headers = [str(c.value).strip() for c in ws[1] if c.value is not None and str(c.value).strip()]
                    wb.close()
                    return headers == HEADERS_PROCESSADOS
        except Exception:
            pass
        return False

    def _load_already_treated(self) -> None:
        """Carrega dados de uma planilha previamente tratada."""
        if self.filepath.suffix.lower() == ".xls":
            wb = xlrd.open_workbook(str(self.filepath), formatting_info=False)
            sheet = wb.sheet_by_index(0)
            headers = [str(c).strip() for c in sheet.row_values(0)]
            for r in range(1, sheet.nrows):
                row = sheet.row_values(r)
                row_dict = {headers[i]: row[i] for i in range(min(len(headers), len(row)))}
                self._add_treated_row(row_dict, r + 1)
        else:
            wb = openpyxl.load_workbook(self.filepath, data_only=True)
            ws = wb.active
            headers = [str(c.value).strip() if c.value is not None else "" for c in ws[1]]
            for idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                row_dict = {headers[i]: row[i] for i in range(min(len(headers), len(row)))}
                self._add_treated_row(row_dict, idx)
            wb.close()

    def _add_treated_row(self, row_dict: dict, row_index: int) -> None:
        nro = str(row_dict.get("Nro cotação", "")).strip()
        if not nro or nro.lower() == "none":
            return
        status_raw = str(row_dict.get("Status", "Pendente")).strip().capitalize()
        status_enum = ItemStatus.PENDENTE
        if "Conclu" in status_raw:
            status_enum = ItemStatus.CONCLUIDO
        elif "Erro" in status_raw:
            status_enum = ItemStatus.ERRO

        item = ItemContrato(
            nro_cotacao=nro,
            categoria_veiculo=str(row_dict.get("Categoria veículo", "") or ""),
            cidade=str(row_dict.get("Cidade", "") or ""),
            uf=str(row_dict.get("UF", "") or ""),
            nome=str(row_dict.get("Nome", "") or ""),
            placa=str(row_dict.get("Placa", "") or ""),
            data_pagamento=str(row_dict.get("Data pagamento", "") or ""),
            viagem_extra=str(row_dict.get("Viagem extra", "Não") or "Não"),
            remetente=str(row_dict.get("Remetente", "") or ""),
            validade=str(row_dict.get("Validade", "") or "") or None,
            frete_a_pagar=str(row_dict.get("Frete a pagar", "") or "") or None,
            frete_negociado=str(row_dict.get("Frete negociado", "") or "") or None,
            status=status_enum,
            row_index=row_index,
        )

        if status_enum == ItemStatus.PENDENTE:
            erros = []
            if not item.nome or item.nome == "NOME NÃO ENCONTRADO":
                erros.append("Nome")
            if not item.placa or item.placa == "PLACA NÃO ENCONTRADA":
                erros.append("Placa")

            is_lactalis = "lactalis" in item.remetente.lower() or "43.340.312" in item.remetente or "43340312" in item.remetente
            if not is_lactalis and (not item.data_pagamento or item.data_pagamento == "DATA NÃO ENCONTRADA"):
                erros.append("Data pagamento")
            if is_lactalis and (not item.validade or str(item.validade).lower() in ("none", "", "nan")):
                erros.append("Validade")

            if erros:
                motivo = f"Dados faltantes: {', '.join(erros)}"
                item.status = ItemStatus.FALHA_VALIDACAO
                item.observacao_erro = motivo
                self.validation_errors.append((item, motivo))
                self.emit(f"[F1] Linha {row_index} (Cotação {nro}): Movida para 'Contrato não realizado'. Motivo: {motivo}", "AVISO")
                return

        self.items.append(item)

    def _process_normalized_spreadsheet(self, norm: NormalizedSpreadsheet) -> None:
        """Processa as linhas normalizadas mapeando colunas dinamicamente."""
        mapping = norm.column_mapping

        # Índices mapeados com fallback padrão para layout clássico BSoft
        idx_status = mapping.get("status")
        idx_cotacao = mapping.get("nro_cotacao", 1)
        idx_categoria = mapping.get("categoria_veiculo", 10)
        idx_cidade_uf = mapping.get("cidade_uf", 12)
        idx_nome_placa = mapping.get("nome_placa", 22)
        idx_remetente = mapping.get("remetente", 11)
        idx_validade = mapping.get("validade", 6)
        idx_frete_pagar = mapping.get("frete_a_pagar", 16)
        idx_frete_neg = mapping.get("frete_negociado", 18)

        start_row_offset = norm.header_row_index + 2

        for r_idx, row in enumerate(norm.rows, start=start_row_offset):
            if not row:
                continue

            def get_col(i: int) -> Any:
                return row[i] if i < len(row) and row[i] is not None else None

            nro_val = get_col(idx_cotacao)
            if nro_val is None or str(nro_val).strip() in ("", "None", "nan"):
                continue

            nro_cotacao = str(nro_val).strip()
            categoria = str(get_col(idx_categoria) or "").strip()
            cidade_uf_raw = str(get_col(idx_cidade_uf) or "").strip()
            nome_placa_raw = str(get_col(idx_nome_placa) or "").strip()
            remetente_raw = str(get_col(idx_remetente) or "N/A").strip()
            validade_raw = str(get_col(idx_validade) or "").strip() or None
            frete_pagar_raw = str(get_col(idx_frete_pagar) or "").strip() or None
            frete_negociado_raw = str(get_col(idx_frete_neg) or "").strip() or None

            # Detecção de status da linha (Concluído / Pendente / Erro)
            status_val = ""
            if idx_status is not None:
                status_val = str(get_col(idx_status) or "").strip()
            elif len(row) > 0 and isinstance(row[0], str):
                status_val = str(row[0]).strip()

            status_lower = status_val.lower()
            is_concluido = any(kw in status_lower for kw in ("conclu", "emitid", "finaliz", "ok", "sucesso"))
            is_erro = any(kw in status_lower for kw in ("erro", "falha", "cancelad"))

            # Fallback adicional: verificar primeira coluna se idx_status não capturou
            if not is_concluido and not is_erro and len(row) > 0:
                first_col_str = str(row[0] or "").strip().lower()
                if any(kw in first_col_str for kw in ("conclu", "emitid", "finaliz", "sucesso")):
                    is_concluido = True
                elif any(kw in first_col_str for kw in ("erro", "falha", "cancelad")):
                    is_erro = True

            item_status = ItemStatus.PENDENTE
            if is_concluido:
                item_status = ItemStatus.CONCLUIDO
            elif is_erro:
                item_status = ItemStatus.ERRO

            cidade, uf = processar_cidade_uf(cidade_uf_raw, r_idx)
            nome, placa, data_pagamento, viagem_extra = processar_nome_placa(nome_placa_raw, r_idx)

            item = ItemContrato(
                nro_cotacao=nro_cotacao,
                categoria_veiculo=categoria,
                cidade=cidade,
                uf=uf,
                nome=nome,
                placa=placa,
                data_pagamento=data_pagamento,
                viagem_extra=viagem_extra,
                remetente=remetente_raw,
                validade=validade_raw,
                frete_a_pagar=frete_pagar_raw,
                frete_negociado=frete_negociado_raw,
                status=item_status,
                row_index=r_idx,
            )

            # Se o item já foi concluído anteriormente no BSoft/ERP, preserva e não reprova na validação
            if item_status == ItemStatus.CONCLUIDO:
                self.items.append(item)
                continue

            # Validação dos dados para itens pendentes
            erros = []
            if nome == "NOME NÃO ENCONTRADO":
                erros.append("Nome")
            if placa == "PLACA NÃO ENCONTRADA":
                erros.append("Placa")

            is_lactalis = "lactalis" in remetente_raw.lower() or "43.340.312" in remetente_raw or "43340312" in remetente_raw
            if not is_lactalis and data_pagamento == "DATA NÃO ENCONTRADA":
                erros.append("Data pagamento")
            if is_lactalis and (not validade_raw or validade_raw.lower() == "none"):
                erros.append("Validade")

            if erros:
                motivo = f"Dados faltantes: {', '.join(erros)}"
                item.status = ItemStatus.FALHA_VALIDACAO
                item.observacao_erro = motivo
                self.validation_errors.append((item, motivo))
                self.emit(f"[F1] Linha {r_idx} (Cotação {nro_cotacao}): Movida para 'Contrato não realizado'. Motivo: {motivo}", "AVISO")
            else:
                self.items.append(item)

    def mark_success(self, nro_cotacao: str) -> None:
        """Marca o item como concluído com sucesso."""
        with self._lock:
            for item in self.items:
                if item.nro_cotacao == nro_cotacao:
                    item.status = ItemStatus.CONCLUIDO
                    item.observacao_erro = None
                    break

    def mark_error(self, nro_cotacao: str, motivo: str) -> None:
        """Marca o item como erro e registra a causa detalhada."""
        with self._lock:
            for item in self.items:
                if item.nro_cotacao == nro_cotacao:
                    item.status = ItemStatus.ERRO
                    item.observacao_erro = motivo
                    break

    def save_output(self, output_path: str | Path) -> Path:
        """Salva a planilha consolidada em disco com tratamento transacional atômico."""
        with self._lock:
            target = Path(output_path)
            target.parent.mkdir(parents=True, exist_ok=True)

            wb = openpyxl.Workbook()
            ws_proc = wb.active
            ws_proc.title = "Dados Processados"
            ws_proc.append(HEADERS_PROCESSADOS)

            ws_err = wb.create_sheet("Contrato não realizado")
            ws_err.sheet_properties.tabColor = "FF0000"
            ws_err.append(HEADERS_NAO_REALIZADO)

            for item in self.items:
                if item.status == ItemStatus.CONCLUIDO:
                    row_data = item.to_row_processados()
                    ws_proc.append(row_data)
                    last_row_idx = ws_proc.max_row
                    for col_idx in range(1, len(row_data) + 1):
                        ws_proc.cell(row=last_row_idx, column=col_idx).fill = GREEN_FILL
                elif item.status == ItemStatus.ERRO:
                    ws_err.append(item.to_row_nao_realizado(item.observacao_erro or "Erro na automação"))
                else:
                    ws_proc.append(item.to_row_processados())

            for item, motivo in self.validation_errors:
                ws_err.append(item.to_row_nao_realizado(motivo))

            tmp_target = target.with_suffix(".tmp.xlsx")
            wb.save(tmp_target)
            wb.close()

            if target.exists():
                target.unlink()
            tmp_target.rename(target)

            self.emit(f"[Output] Planilha consolidada salva em: {target.name}", "DEBUG")
            return target
