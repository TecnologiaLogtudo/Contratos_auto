from __future__ import annotations

import tempfile
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from backend.app.domain.models import ItemContrato, ItemStatus
from backend.app.engine.excel_processor import ExcelProcessor
from backend.app.engine.contract_runner import ContractRunner
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
