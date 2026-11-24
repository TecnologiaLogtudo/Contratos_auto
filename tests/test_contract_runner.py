from __future__ import annotations

import tempfile
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from backend.app.domain.models import ItemContrato, ItemStatus, ItemResult
from backend.app.domain.errors import AutomationError
from backend.app.engine.excel_processor import ExcelProcessor
from backend.app.engine.contract_runner import ContractRunner, URL_CONHECIMENTO_FORM
from backend.app.engine.browser_factory import BrowserConfig


def test_contract_runner_lifecycle_with_mocked_browser():
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / "input.xlsx"
        output_path = Path(tmpdir) / "output.xlsx"

        # Prepara processor com 1 item válido e 1 com erro simulado
        processor = ExcelProcessor(input_path)
        item1 = ItemContrato(
            nro_cotacao="101",
            nome="MOTORISTA TESTE",
            placa="ABC1234",
            cidade="Salvador",
            uf="BA",
            remetente="Latam",
            data_pagamento="10/08/2026",
            status=ItemStatus.PENDENTE,
        )
        item2 = ItemContrato(
            nro_cotacao="102",
            nome="MOTORISTA DOIS",
            placa="XYZ9876",
            cidade="Salvador",
            uf="BA",
            remetente="Latam",
            data_pagamento="10/08/2026",
            status=ItemStatus.PENDENTE,
        )
        processor.items = [item1, item2]
        processor.load_and_parse = MagicMock(return_value=[item1, item2])

        logs = []
        progress_events = []

        runner = ContractRunner(
            usuario="test_user",
            senha="test_pass",
            excel_processor=processor,
            output_filepath=output_path,
            log_callback=lambda m, l="INFO": logs.append((l, m)),
            progress_callback=lambda c, t, m: progress_events.append((c, t, m)),
        )

        # Mock das páginas e do browser
        mock_page = MagicMock()
        mock_page.url = "https://logtudo.e-login.net/versoes/versao5.0/rotinas/formulario.php?rotina=trans_conhecimento"
        mock_page.is_closed.return_value = False

        mock_pw = MagicMock()
        mock_browser = MagicMock()
        mock_ctx = MagicMock()

        with patch("backend.app.engine.contract_runner.BrowserFactory.create_browser", return_value=(mock_pw, mock_browser, mock_ctx, mock_page)):
            with patch("backend.app.engine.contract_runner.LoginPage.login"):
                with patch("backend.app.engine.contract_runner.ConhecimentoPage.preencher_fase3") as mock_f3:
                    with patch("backend.app.engine.contract_runner.FretePage.preencher_fase4") as mock_f4:
                        with patch("backend.app.engine.contract_runner.ContratoPage.preencher_e_salvar_fase5") as mock_f5:
                            # Faz item 2 falhar na Fase 4
                            mock_f4.side_effect = [None, RuntimeError("Falha simulada no frete")]

                            summary = runner.run()

                            assert summary.total == 2
                            assert summary.sucessos == 1
                            assert summary.erros == 1
                            assert summary.taxa_sucesso == 50.0

                            # Verifica se o arquivo de output foi salvo
                            assert output_path.exists()
                            assert item1.status == ItemStatus.CONCLUIDO
                            assert item2.status == ItemStatus.ERRO
                            assert "Falha simulada no frete" in (item2.observacao_erro or "")


def test_contract_runner_reset_session_delegates_to_recovery_manager():
    runner = ContractRunner(
        usuario="admin",
        senha="123",
        log_callback=lambda m, l="INFO": None,
    )
    mock_page = MagicMock()
    mock_ctx = MagicMock()
    runner.page = mock_page
    runner.context = mock_ctx

    new_page = MagicMock()
    fake_recovery_result = MagicMock()
    fake_recovery_result.page = new_page

    with patch("backend.app.engine.contract_runner.SessionRecoveryManager") as MockRecoveryMgr:
        instance = MockRecoveryMgr.return_value
        instance.recover.return_value = fake_recovery_result

        runner._reset_session(force_hard_reset=False)

        MockRecoveryMgr.assert_called_once_with(
            usuario="admin",
            senha="123",
            url_form="https://logtudo.e-login.net/versoes/versao5.0/rotinas/formulario.php?rotina=trans_conhecimento&OP=O1&_qsf=1",
            log_callback=runner.log,
            delay=runner.delay_fases,
        )
        instance.recover.assert_called_once_with(
            page=mock_page,
            context=mock_ctx,
            error=None,
            force_hard_reset=False,
        )
        assert runner.page == new_page
        assert runner.conhecimento_page is not None
        assert runner.frete_page is not None
        assert runner.contrato_page is not None
        assert runner.cotacoes_page is not None


def test_contract_runner_reset_session_passes_error_to_recovery():
    runner = ContractRunner(
        usuario="admin",
        senha="123",
        log_callback=lambda m, l="INFO": None,
    )
    mock_page = MagicMock()
    mock_ctx = MagicMock()
    runner.page = mock_page
    runner.context = mock_ctx

    simulated_err = RuntimeError("Erro simulado")
    with patch("backend.app.engine.contract_runner.SessionRecoveryManager") as MockRecoveryMgr:
        instance = MockRecoveryMgr.return_value
        instance.recover.return_value = MagicMock(page=mock_page)

        runner._reset_session(error=simulated_err)

        instance.recover.assert_called_once_with(
            page=mock_page,
            context=mock_ctx,
            error=simulated_err,
            force_hard_reset=False,
        )


def test_process_single_item_navigates_to_clean_form_unconditionally():
    """Valida R2: A navegação para URL_CONHECIMENTO_FORM e dismiss_all_popups ocorre incondicionalmente."""
    runner = ContractRunner(usuario="u", senha="p")
    mock_page = MagicMock()
    # Simula URL já estando na rota de formulário do item anterior
    mock_page.url = "https://logtudo.e-login.net/versoes/versao5.0/rotinas/formulario.php?rotina=trans_conhecimento"
    mock_page.is_closed.return_value = False
    runner.page = mock_page
    runner.conhecimento_page = MagicMock()
    runner.frete_page = MagicMock()
    runner.contrato_page = MagicMock()
    runner.cotacoes_page = MagicMock()

    item = ItemContrato(nro_cotacao="555", remetente="Latam", status=ItemStatus.PENDENTE)

    with patch("backend.app.engine.contract_runner.DialogGuard.dismiss_all_popups") as mock_dismiss:
        res = runner.process_single_item(item)

    assert res.sucesso is True
    assert res.status == ItemStatus.CONCLUIDO
    # Verifica que page.goto foi chamado incondicionalmente com URL_CONHECIMENTO_FORM
    mock_page.goto.assert_called_once_with(URL_CONHECIMENTO_FORM, wait_until="load", timeout=45000)
    mock_dismiss.assert_called_once_with(mock_page, runner.log, "Item 555")


def test_process_single_item_returns_error_even_if_reset_session_raises():
    """Valida R3: Se _reset_session falhar no bloco except, process_single_item ainda retorna ItemResult(status=ERRO)."""
    runner = ContractRunner(usuario="u", senha="p")
    mock_page = MagicMock()
    mock_page.url = URL_CONHECIMENTO_FORM
    mock_page.is_closed.return_value = False
    runner.page = mock_page
    runner.conhecimento_page = MagicMock()
    runner.frete_page = MagicMock()
    runner.contrato_page = MagicMock()
    runner.cotacoes_page = MagicMock()

    # Simula falha na Fase 4
    runner.frete_page.preencher_fase4.side_effect = RuntimeError("Falha simulada na Fase 4")

    # Simula falha catastrófica no reset de sessão
    runner._reset_session = MagicMock(side_effect=AutomationError("Falha irrecuperável de sessão"))

    item = ItemContrato(nro_cotacao="9999", remetente="Latam", status=ItemStatus.PENDENTE)
    result = runner.process_single_item(item)

    assert result.sucesso is False
    assert result.status == ItemStatus.ERRO
    assert result.nro_cotacao == "9999"
    assert "Falha simulada na Fase 4" in result.motivo_erro
    runner._reset_session.assert_called_once()



