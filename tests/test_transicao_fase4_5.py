"""Testes unitários para o requisito R5: Mitigação de Timeout e Modais na Transição Fase 4 -> 5."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch, call
import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from backend.app.domain.models import ItemContrato, ItemStatus
from backend.app.domain.errors import NavigationError, FormFillError
from backend.app.engine.dialog_guard import DialogGuard
from backend.app.engine.pages.frete_page import FretePage


@pytest.fixture
def dummy_item():
    return ItemContrato(
        nro_cotacao="17691611",
        remetente="4000 - LACTALIS BA - DIÁRIA PARADO",
        cidade="Salvador",
        uf="BA",
        status=ItemStatus.PENDENTE,
    )


def test_aguardar_transicao_fase5_sucesso_imediato(dummy_item):
    """Valida retorno bem-sucedido quando o elemento da Fase 5 já está visível de imediato."""
    mock_page = MagicMock()
    mock_page.url = "https://logtudo.e-login.net/versoes/versao5.0/rotinas/formulario.php?rotina=trans_conhecimento"

    def locator_mock(selector):
        loc = MagicMock()
        if "dados_dtFimViagem" in selector or "Emitir contrato" in selector:
            loc.is_visible.return_value = True
        elif ".swstatus-input-error" in selector:
            loc.count.return_value = 0
        else:
            loc.count.return_value = 0
            loc.first.is_visible.return_value = False
        return loc

    mock_page.locator.side_effect = locator_mock

    logs = []
    frete_page = FretePage(mock_page, log_callback=lambda m, l="INFO": logs.append((l, m)))

    with patch.object(DialogGuard, "dismiss_all_popups", return_value=False) as mock_dismiss:
        with patch.object(DialogGuard, "detectar_erro_negocio", return_value=None):
            frete_page._aguardar_transicao_fase5(dummy_item)

    mock_dismiss.assert_called()


def test_aguardar_transicao_fase5_com_modal_sweetalert_confirmacao(dummy_item):
    """Valida fechamento ativo de modal SweetAlert de confirmação durante a transição."""
    mock_page = MagicMock()
    mock_page.url = "https://logtudo.e-login.net/versoes/versao5.0/rotinas/formulario.php?rotina=trans_conhecimento"

    call_count = {"fase5": 0}

    def locator_mock(selector):
        loc = MagicMock()
        if "dados_dtFimViagem" in selector or "Emitir contrato" in selector:
            # Torna visível na segunda verificação (após fechamento do modal)
            call_count["fase5"] += 1
            loc.is_visible.return_value = (call_count["fase5"] >= 2)
        elif ".swstatus-input-error" in selector:
            loc.count.return_value = 0
        else:
            loc.count.return_value = 0
            loc.first.is_visible.return_value = False
        return loc

    mock_page.locator.side_effect = locator_mock

    logs = []
    frete_page = FretePage(mock_page, log_callback=lambda m, l="INFO": logs.append((l, m)))

    dismiss_results = [True, False]
    with patch.object(DialogGuard, "dismiss_all_popups", side_effect=lambda *args, **kwargs: dismiss_results.pop(0) if dismiss_results else False) as mock_dismiss:
        with patch.object(DialogGuard, "detectar_erro_negocio", return_value=None):
            frete_page._aguardar_transicao_fase5(dummy_item)

    assert mock_dismiss.call_count >= 1


def test_aguardar_transicao_fase5_com_aviso_peso_cubagem(dummy_item):
    """Valida transição quando há diálogo de aviso de mercadoria sem peso/cubagem."""
    mock_page = MagicMock()
    mock_page.url = "https://logtudo.e-login.net/versoes/versao5.0/rotinas/formulario.php"

    fase5_visible = {"val": False}

    def locator_mock(selector):
        loc = MagicMock()
        if "dados_dtFimViagem" in selector or "Emitir contrato" in selector:
            loc.is_visible.return_value = fase5_visible["val"]
        elif ".swstatus-input-error" in selector:
            loc.count.return_value = 0
        else:
            loc.count.return_value = 0
            loc.first.is_visible.return_value = False
        return loc

    mock_page.locator.side_effect = locator_mock

    def fake_dismiss(page, log, tag):
        # Simula o clique no botão "Continuar" / "Sim" do diálogo de peso/cubagem
        fase5_visible["val"] = True
        return True

    frete_page = FretePage(mock_page)

    with patch.object(DialogGuard, "dismiss_all_popups", side_effect=fake_dismiss):
        with patch.object(DialogGuard, "detectar_erro_negocio", return_value=None):
            frete_page._aguardar_transicao_fase5(dummy_item)

    assert fase5_visible["val"] is True


def test_aguardar_transicao_fase5_aborta_cedo_com_erro_negocio(dummy_item):
    """Valida interrupção imediata da espera quando o portal exibe alerta de erro de negócio."""
    mock_page = MagicMock()
    mock_page.url = "https://logtudo.e-login.net/versoes/versao5.0/rotinas/formulario.php?message_collection_id=123"

    frete_page = FretePage(mock_page)

    with patch.object(DialogGuard, "dismiss_all_popups", return_value=False):
        with patch.object(
            DialogGuard,
            "detectar_erro_negocio",
            return_value="A data de emissão não pode ser maior que a data programada do saldo.",
        ):
            with pytest.raises(NavigationError) as exc_info:
                frete_page._aguardar_transicao_fase5(dummy_item)

    err = exc_info.value
    assert "A data de emissão não pode ser maior que a data programada do saldo." in str(err)
    assert err.step == "Transição Fase 4->5"


def test_aguardar_transicao_fase5_aborta_cedo_com_validacao_input_fase4(dummy_item):
    """Valida detecção precoce de campos obrigatórios com erro na Fase 4 sem esperar timeout de 30s."""
    mock_page = MagicMock()
    mock_page.url = "https://logtudo.e-login.net/versoes/versao5.0/rotinas/formulario.php"

    mock_err_input = MagicMock()
    mock_err_input.get_attribute.side_effect = lambda attr: "dados_enderecoDestinatario_id" if attr == "name" else None

    mock_err_loc = MagicMock()
    mock_err_loc.count.return_value = 1
    mock_err_loc.nth.return_value = mock_err_input

    def locator_mock(selector):
        loc = MagicMock()
        if ".swstatus-input-error" in selector:
            return mock_err_loc
        elif "dados_dtFimViagem" in selector:
            loc.is_visible.return_value = False
        else:
            loc.count.return_value = 0
            loc.first.is_visible.return_value = False
        return loc

    mock_page.locator.side_effect = locator_mock

    frete_page = FretePage(mock_page)

    with patch.object(DialogGuard, "dismiss_all_popups", return_value=False):
        with patch.object(DialogGuard, "detectar_erro_negocio", return_value=None):
            with pytest.raises(FormFillError) as exc_info:
                frete_page._aguardar_transicao_fase5(dummy_item)

    err = exc_info.value
    assert "dados_enderecoDestinatario_id" in str(err)
    assert err.step == "Fase 4"


def test_aguardar_transicao_fase5_timeout_com_diagnostico_estruturado(dummy_item, monkeypatch):
    """Valida geração de log estruturado de diagnóstico antes do lançamento do NavigationError no timeout."""
    mock_page = MagicMock()
    mock_page.url = "https://logtudo.e-login.net/versoes/versao5.0/rotinas/formulario.php?SWU=&OP=O1"
    mock_page.title.return_value = "LogTudo e-Login - Conhecimento de Transporte"

    mock_loc = MagicMock()
    mock_loc.is_visible.return_value = False
    mock_loc.count.return_value = 0
    mock_loc.wait_for.side_effect = PlaywrightTimeoutError("Timeout simulado")
    mock_page.locator.return_value = mock_loc

    # Força timeout imediato fazendo o tempo avançar além dos 30s
    cur_time = [100.0]
    def fake_time():
        t = cur_time[0]
        cur_time[0] += 35.0
        return t

    monkeypatch.setattr(time, "time", fake_time)

    logs = []
    frete_page = FretePage(mock_page, log_callback=lambda m, l="INFO": logs.append((l, m)))

    with patch.object(DialogGuard, "dismiss_all_popups", return_value=False):
        with patch.object(DialogGuard, "detectar_erro_negocio", return_value=None):
            with pytest.raises(NavigationError) as exc_info:
                frete_page._aguardar_transicao_fase5(dummy_item)

    err = exc_info.value
    assert "Timeout aguardando carregamento da Fase 5." in str(err)
    # Verifica registro de diagnóstico estruturado
    diag_logs = [m for l, m in logs if "DIAGNÓSTICO TIMEOUT FASE 4->5" in m]
    assert len(diag_logs) > 0
    assert "URL: https://logtudo.e-login.net" in diag_logs[0]


def test_dialog_guard_dismiss_all_popups_variacoes_botoes():
    """Valida que o DialogGuard reconhece e clica em botões afirmativos variados e SweetAlert."""
    mock_page = MagicMock()

    # Simula nenhum diálogo jQuery UI aberto, mas SweetAlert com botão 'Sim' visível
    mock_dialog_loc = MagicMock()
    mock_dialog_loc.count.return_value = 0

    mock_btn_sim = MagicMock()
    mock_btn_sim.count.return_value = 1
    mock_btn_sim.first.is_visible.return_value = True

    mock_overlay = MagicMock()
    mock_overlay.count.return_value = 1

    def locator_mock(selector):
        if ".ui-dialog:visible" in selector:
            return mock_dialog_loc
        elif 'button:has-text("Sim")' in selector or '.swal2-confirm' in selector:
            return mock_btn_sim
        elif ".swal2-container:visible" in selector or ".ui-widget-overlay:visible" in selector:
            return mock_overlay
        loc = MagicMock()
        loc.count.return_value = 0
        loc.first.is_visible.return_value = False
        return loc

    mock_page.locator.side_effect = locator_mock

    res = DialogGuard.dismiss_all_popups(mock_page)

    assert res is True
    mock_btn_sim.first.click.assert_called_once()
    mock_page.evaluate.assert_called()


def test_dialog_guard_detectar_erro_negocio_fontes_variadas():
    """Valida detecção de mensagens de erro em caixas de erro padrão, SweetAlert e Bootstrap."""
    mock_page = MagicMock()

    mock_error_loc = MagicMock()
    mock_error_loc.count.return_value = 1
    mock_error_loc.first.is_visible.return_value = True
    mock_error_loc.first.inner_text.return_value = "  Mercadoria sem peso ou cubagem informada.  "

    def locator_mock(selector):
        if ".swal2-html-container:visible" in selector:
            return mock_error_loc
        loc = MagicMock()
        loc.count.return_value = 0
        loc.first.is_visible.return_value = False
        return loc

    mock_page.locator.side_effect = locator_mock

    msg = DialogGuard.detectar_erro_negocio(mock_page)
    assert msg == "Mercadoria sem peso ou cubagem informada."
