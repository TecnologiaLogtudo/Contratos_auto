from __future__ import annotations

import tempfile
from pathlib import Path
import openpyxl
import pytest

from backend.app.engine.excel_processor import (
    processar_cidade_uf,
    processar_nome_placa,
    padronizar_cidade,
    ExcelProcessor,
)
from backend.app.domain.models import ItemContrato, ItemStatus


def test_processar_placas():
    # Placa Antiga
    nome, placa, dt, extra = processar_nome_placa("JOAO DA SILVA ABC-1234 15/08/2026")
    assert placa == "ABC1234"
    assert "JOAO DA SILVA" in nome
    assert dt == "15/08/2026"
    assert extra == "Não"

    # Placa Mercosul
    nome, placa, dt, extra = processar_nome_placa("MARIA SOUZA BRA2E19 10/09/2026 VIAGEM EXTRA")
    assert placa == "BRA2E19"
    assert "MARIA SOUZA" in nome
    assert dt == "10/09/2026"
    assert extra == "Sim"

    # Placa com espaço
    nome, placa, dt, extra = processar_nome_placa("CARLOS PEREIRA XYZ 9876")
    assert placa == "XYZ9876"
    assert "CARLOS PEREIRA" in nome


def test_limpeza_nome_motorista():
    # Remove pernoite, NF, horários
    raw = "pernoite 53640535 nf-115452 FELIPE LEAL FERREIRA JRK-1055 14h30"
    nome, placa, dt, extra = processar_nome_placa(raw)
    assert placa == "JRK1055"
    assert "FELIPE LEAL FERREIRA" in nome
    assert "pernoite" not in nome.lower()
    assert "nf" not in nome.lower()


def test_limpeza_nome_com_pipes():
    raw = "VALDENI RAIMUNDO | EXD-9D67 | 25/11/2026"
    nome, placa, dt, extra = processar_nome_placa(raw)
    assert placa == "EXD9D67"
    assert nome == "VALDENI RAIMUNDO"
    assert dt == "25/11/2026"
    assert extra == "Não"


def test_padronizar_cidades():
    assert padronizar_cidade("JOAO PESSOA") == "J. Pessoa"
    assert padronizar_cidade("João Pessoa") == "J. Pessoa"
    assert padronizar_cidade("Bayeux") == "J. Pessoa"
    assert padronizar_cidade("CAMACARI") == "Salvador"
    assert padronizar_cidade("Camaçari") == "Salvador"
    assert padronizar_cidade("SIMOES FILHO") == "Salvador"
    assert padronizar_cidade("Simões Filho") == "Salvador"
    assert padronizar_cidade("SERRA") == "Vitória"
    assert padronizar_cidade("Vila Velha") == "Vitória"
    assert padronizar_cidade("Feira de Santana") == "Feira de Santana"


def test_processar_cidade_uf():
    cid, uf = processar_cidade_uf("CAMACARI / BA")
    assert cid == "Salvador"
    assert uf == "BA"

    cid, uf = processar_cidade_uf("JOAO PESSOA / PB")
    assert cid == "J. Pessoa"
    assert uf == "PB"


def test_excel_processor_save_output():
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "resultado_test.xlsx"
        dummy_in = Path(tmpdir) / "dummy.xlsx"

        # Cria planilha dummy
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Dados Processados"
        wb.save(dummy_in)
        wb.close()

        processor = ExcelProcessor(dummy_in)
        item1 = ItemContrato(
            nro_cotacao="1001",
            nome="MOTORISTA UM",
            placa="ABC1234",
            cidade="Salvador",
            uf="BA",
            remetente="Lactalis",
            status=ItemStatus.CONCLUIDO,
        )
        item2 = ItemContrato(
            nro_cotacao="1002",
            nome="MOTORISTA DOIS",
            placa="XYZ9876",
            cidade="Vitória",
            uf="ES",
            remetente="Latam",
            status=ItemStatus.ERRO,
            observacao_erro="Cotação bloqueada",
        )

        processor.items = [item1, item2]
        saved_file = processor.save_output(out_path)

        assert saved_file.exists()

        # Verifica conteúdo salvo
        wb_check = openpyxl.load_workbook(saved_file)
        assert "Dados Processados" in wb_check.sheetnames
        assert "Contrato não realizado" in wb_check.sheetnames

        ws_proc = wb_check["Dados Processados"]
        ws_err = wb_check["Contrato não realizado"]

        # Item 1 deve estar em Dados Processados
        rows_proc = list(ws_proc.iter_rows(values_only=True))
        assert any(r[0] == "1001" for r in rows_proc[1:])

        # Item 2 deve estar em Contrato não realizado com o motivo
        rows_err = list(ws_err.iter_rows(values_only=True))
        assert any(r[0] == "1002" and "Cotação bloqueada" in r[7] for r in rows_err[1:])

        wb_check.close()


def test_sanitize_bsoft_xlsx_date_cells():
    import datetime
    from backend.app.engine.sanitizer import sanitize_bsoft_xlsx

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "teste_datas.xlsx"
        wb = openpyxl.Workbook()
        ws = wb.active
        # Cabeçalhos
        ws.append(["Nro cotação", "Validade", "Categoria veículo", "Remetente", "Cidade/UF", "Nome/Placa"])
        # Linha com datetime nativo
        dt_val = datetime.date(2026, 10, 1)
        ws.append(["1925000", dt_val, "BONGO", "LACTALIS REFRIGERADO", "Salvador/BA", "GUSTAVO PLU2I87"])
        wb.save(test_file)
        wb.close()

        norm = sanitize_bsoft_xlsx(test_file)
        assert len(norm.rows) == 1
        validade_str = norm.rows[0][norm.column_mapping["validade"]]
        assert validade_str == "01/10/2026"


def test_populate_from_db_and_save_output():
    with tempfile.TemporaryDirectory() as tmpdir:
        dummy_in = Path(tmpdir) / "input.xlsx"
        wb = openpyxl.Workbook()
        wb.save(dummy_in)
        wb.close()

        processor = ExcelProcessor(dummy_in)
        items_data = [
            {
                "nro_cotacao": "2001",
                "categoria_veiculo": "TOCO",
                "cidade": "Salvador",
                "uf": "BA",
                "nome": "MOTORISTA SUCESSO",
                "placa": "ABC1234",
                "data_pagamento": "10/10/2026",
                "viagem_extra": "Não",
                "remetente": "Lactalis",
                "validade": "01/10/2026",
                "frete_a_pagar": "1500,00",
                "frete_negociado": "1500,00",
                "status": "Concluído",
                "error_message": None,
                "row_index": 2,
            },
            {
                "nro_cotacao": "2002",
                "categoria_veiculo": "TRUCK",
                "cidade": "Feira de Santana",
                "uf": "BA",
                "nome": "MOTORISTA ERRO",
                "placa": "XYZ5678",
                "data_pagamento": "11/10/2026",
                "viagem_extra": "Sim",
                "remetente": "LATAM",
                "validade": "02/10/2026",
                "frete_a_pagar": "2000,00",
                "frete_negociado": "2000,00",
                "status": "Erro",
                "error_message": "Cotação bloqueada no ERP",
                "row_index": 3,
            },
            {
                "nro_cotacao": "2003",
                "categoria_veiculo": "CARRETA",
                "cidade": "Vitória",
                "uf": "ES",
                "nome": "NOME NÃO ENCONTRADO",
                "placa": "PLACA NÃO ENCONTRADA",
                "data_pagamento": "DATA NÃO ENCONTRADA",
                "viagem_extra": "Não",
                "remetente": "LogTudo",
                "validade": None,
                "frete_a_pagar": None,
                "frete_negociado": None,
                "status": "Falha Validação",
                "error_message": "Dados faltantes: Nome, Placa",
                "row_index": 4,
            },
        ]

        processor.populate_from_db(items_data)

        assert len(processor.items) == 2
        assert len(processor.validation_errors) == 1

        out_path = Path(tmpdir) / "relatorio_final.xlsx"
        saved = processor.save_output(out_path)
        assert saved.exists()

        wb_out = openpyxl.load_workbook(saved)
        assert "Dados Processados" in wb_out.sheetnames
        assert "Contrato não realizado" in wb_out.sheetnames

        ws_proc = wb_out["Dados Processados"]
        ws_err = wb_out["Contrato não realizado"]

        proc_rows = list(ws_proc.iter_rows(values_only=True))
        err_rows = list(ws_err.iter_rows(values_only=True))

        # Aba Dados Processados: 1 cabeçalho + 1 item concluído
        assert len(proc_rows) == 2
        assert proc_rows[1][0] == "2001"
        assert proc_rows[1][4] == "MOTORISTA SUCESSO"
        assert proc_rows[1][12] == "Concluído"

        # Aba Contrato não realizado: 1 cabeçalho + 2 itens (1 com erro de execução + 1 com falha de validação)
        assert len(err_rows) == 3
        cots_err = [r[0] for r in err_rows[1:]]
        assert "2002" in cots_err
        assert "2003" in cots_err

        wb_out.close()


def test_sync_with_db():
    dummy_in = Path("dummy.xlsx")
    processor = ExcelProcessor(dummy_in)
    item = ItemContrato(
        nro_cotacao="3001",
        nome="MOTORISTA TESTE",
        placa="BRA2E19",
        status=ItemStatus.PENDENTE,
    )
    processor.items = [item]

    db_data = [
        {
            "nro_cotacao": "3001",
            "status": "Concluído",
            "error_message": None,
        }
    ]
    processor.sync_with_db(db_data)
    assert processor.items[0].status == ItemStatus.CONCLUIDO
