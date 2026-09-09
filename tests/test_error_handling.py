from __future__ import annotations

import pytest
from backend.app.domain.errors import (
    AutomationError,
    SpreadsheetValidationError,
    AuthenticationError,
    QuoteExtractionError,
    FormFillError,
    SubmissionError,
)
from backend.app.domain.models import ItemContrato, ItemStatus


def test_error_hierarchy():
    err1 = SpreadsheetValidationError("Campos ausentes", missing_fields=["Placa", "Nome"], row_index=12)
    assert "[Validação Planilha (Linha 12)]" in str(err1)
    assert "Campos: Placa, Nome" in str(err1)

    err2 = AuthenticationError("Credenciais inválidas", reason="Senha incorreta")
    assert "[Fase 2 - Login]" in str(err2)
    assert "Senha incorreta" in str(err2)

    err3 = QuoteExtractionError("Cotação bloqueada", quote_number="1832067", details="Status da cotação não permite edição")
    assert "[Cotação 1832067]" in str(err3)
    assert "Status da cotação não permite edição" in str(err3)

    err4 = FormFillError("Select de motorista vazio", field_name="dados_motorista_id", step="Fase 4")
    assert "[Fase 4]" in str(err4)
    assert "dados_motorista_id" in str(err4)

    err5 = SubmissionError("Timeout ao salvar contrato", reason="Rede lenta")
    assert "[Fase 5 - Salvamento]" in str(err5)


def test_item_to_row_nao_realizado():
    item = ItemContrato(
        nro_cotacao="1832067",
        categoria_veiculo="TOCO",
        cidade="Salvador",
        uf="BA",
        nome="MOTORISTA TESTE",
        placa="JRK1055",
        data_pagamento="15/08/2026",
        status=ItemStatus.ERRO,
    )
    row = item.to_row_nao_realizado("Cotação não encontrada no sistema")
    assert row[0] == "1832067"
    assert row[7] == "Cotação não encontrada no sistema"
    assert row[8] == "Erro"
