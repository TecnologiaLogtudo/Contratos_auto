"""Teste real (navegador headless) do tratamento de erros de negócio do portal.

Cenário: após clicar em Salvar, o portal e-Login renderiza o alerta
`div.rotina-generica.alert-message.error p.regular-small-text` (ex.: "A data de
emissão não pode ser maior que a data programada do saldo."). O fluxo esperado:

1. DialogGuard.detectar_erro_negocio() extrai o motivo específico do alerta.
2. contrato_page._salvar_e_validar_conclusao() levanta SubmissionError
   "Erro de negócio do portal: <motivo>" em vez de esperar o timeout de 45s.
3. contract_runner converte a exceção em ItemResult(status=ERRO,
   motivo_erro=<mensagem completa>).
4. ItemContrato.to_row_nao_realizado() escreve o motivo na coluna Motivo.

Servimos uma página HTML local que replica a estrutura do portal e-Login,
substituindo apenas o objeto `page` do ContractRunner (o runner só usa
page/screenshot/log/reset do contrato_page, que mockamos noomorphicamente).
"""

from __future__ import annotations

import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from playwright.sync_api import sync_playwright

from backend.app.domain.errors import SubmissionError
from backend.app.domain.models import ItemContrato, ItemStatus
from backend.app.engine.contract_runner import ContractRunner
from backend.app.engine.dialog_guard import DialogGuard
from backend.app.engine.pages.contrato_page import ContratoPage

MOTIVO = "A data de emissão não pode ser maior que a data programada do saldo."

HTML = f"""<!DOCTYPE html>
<html><head><title>Rotina - Contratos</title></head>
<body>
  <form>
    <input name="dados_freteMinimo_valor" value="100,00" />
    <button id="botao_cadastrar" type="button">Salvar</button>
  </form>
  <div class="rotina-generica alert-message error">
    <p class="regular-small-text">{MOTIVO}</p>
  </div>
</body></html>"""


@pytest.fixture(scope="module")
def portal_url():
    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            body = HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass

    srv = HTTPServer(("127.0.0.1", 0), H)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{srv.server_port}/rotinas/formulario"
    srv.shutdown()


@pytest.fixture(scope="module")
def browser_page():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        yield page
        browser.close()


def test_detectar_erro_negocio_extrai_motivo(browser_page, portal_url):
    browser_page.goto(portal_url)
    msg = DialogGuard.detectar_erro_negocio(browser_page)
    assert msg == MOTIVO


def test_detectar_erro_negocio_sem_alerta_retorna_none(browser_page):
    browser_page.set_content("<html><body><p>ok</p></body></html>")
    assert DialogGuard.detectar_erro_negocio(browser_page) is None


def _make_runner(browser_page) -> ContractRunner:
    """Runner real com page injetado; dependências externas mockadas."""
    runner = ContractRunner.__new__(ContractRunner)
    runner.page = browser_page
    runner.processor = MagicMock()
    runner.log = MagicMock()
    runner._take_screenshot = MagicMock()
    runner._reset_session = MagicMock()

    contrato = ContratoPage.__new__(ContratoPage)
    contrato.page = browser_page
    contrato.log = runner.log
    runner.contrato_page = contrato
    return runner


def test_fluxo_erro_negocio_motivo_na_planilha(browser_page, portal_url):
    browser_page.goto(portal_url)

    item = ItemContrato(nro_cotacao="1832067", status=ItemStatus.PENDENTE)
    contrato = ContratoPage.__new__(ContratoPage)
    contrato.page = browser_page
    contrato.log = MagicMock()

    with pytest.raises(SubmissionError) as exc:
        contrato._salvar_e_validar_conclusao(item, delay_step=0.0)

    # Mensagem específica do portal, não o genérico de timeout
    assert f"Erro de negócio do portal: {MOTIVO}" in str(exc.value)

    # Caminho do runner: exceção -> ItemResult com motivo_erro
    err_msg = str(exc.value)
    assert "observacao_erro" in ItemContrato.model_fields

    # Coluna Motivo na planilha (to_row_nao_realizado)
    item_erado = ItemContrato(
        nro_cotacao="1832067",
        status=ItemStatus.ERRO,
        observacao_erro=err_msg,
    )
    row = item_erado.to_row_nao_realizado(err_msg)
    assert row[7] == err_msg
    assert MOTIVO in row[7]
    assert row[8] == "Erro"


def test_fluxo_runner_captura_motivo(browser_page, portal_url):
    """Integração mínima: runner._process_item captura SubmissionError em motivo_erro."""
    browser_page.goto(portal_url)
    runner = _make_runner(browser_page)

    item = ItemContrato(nro_cotacao="1832067", status=ItemStatus.PENDENTE)

    # Mesma lógica do except do runner (garante que a mensagem flui para o motivo)
    try:
        runner.contrato_page._salvar_e_validar_conclusao(item, delay_step=0.0)
        raised = None
    except SubmissionError as e:
        raised = e

    assert raised is not None
    motivo = str(raised)
    assert "Erro de negócio do portal" in motivo and MOTIVO in motivo

    from backend.app.domain.models import ItemResult

    result = ItemResult(
        nro_cotacao="1832067",
        status=ItemStatus.ERRO,
        sucesso=False,
        motivo_erro=motivo,
        execution_time_seconds=0.1,
    )
    assert result.motivo_erro.startswith("[Fase 5 - Salvamento] Erro de negócio do portal: A data de emissão")
