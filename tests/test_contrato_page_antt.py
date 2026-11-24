from unittest.mock import MagicMock
import pytest
from backend.app.engine.pages.contrato_page import ContratoPage


def test_confirmar_frete_minimo_antt_sucesso_check():
    mock_page = MagicMock()
    mock_locator = MagicMock()
    mock_page.locator.return_value = mock_locator
    mock_locator.is_visible.return_value = True

    page_obj = ContratoPage(mock_page)
    page_obj._confirmar_frete_minimo_antt("123456", delay_step=0.0)

    mock_locator.check.assert_called_once_with(timeout=2500, force=True)
    mock_page.evaluate.assert_not_called()


def test_confirmar_frete_minimo_antt_fallback_js_quando_check_falha():
    mock_page = MagicMock()
    mock_locator = MagicMock()
    mock_page.locator.return_value = mock_locator
    mock_locator.is_visible.return_value = True
    mock_locator.check.side_effect = Exception("Element not clickable / timeout")

    page_obj = ContratoPage(mock_page)
    # Não deve levantar exceção!
    page_obj._confirmar_frete_minimo_antt("123456", delay_step=0.0)

    mock_locator.check.assert_called_once_with(timeout=2500, force=True)
    mock_page.evaluate.assert_called_once()


def test_confirmar_frete_minimo_antt_quando_invisivel():
    mock_page = MagicMock()
    mock_locator = MagicMock()
    mock_page.locator.return_value = mock_locator
    mock_locator.is_visible.return_value = False

    page_obj = ContratoPage(mock_page)
    page_obj._confirmar_frete_minimo_antt("123456", delay_step=0.0)

    mock_locator.check.assert_not_called()
    mock_page.evaluate.assert_not_called()


def test_configurar_destinatario_contrato_com_popup_interceptor():
    mock_page = MagicMock()
    mock_btn = MagicMock()
    # Primeiro click falha (interceptado por popup), segundo click (force) funciona
    mock_btn.click.side_effect = [Exception("intercepted by ui-widget-overlay"), None]

    mock_dest_sel = MagicMock()
    mock_dest_sel.select_option.return_value = None

    def locator_side_effect(sel):
        if "botaoPesquisa" in sel:
            return mock_btn
        if "dados_enderecoDestinatarioContrato_id" in sel:
            return mock_dest_sel
        return MagicMock()

    mock_page.locator.side_effect = locator_side_effect

    from backend.app.domain.models import ItemContrato
    item = MagicMock(spec=ItemContrato)
    item.nro_cotacao = "1361611"

    page_obj = ContratoPage(mock_page)
    page_obj._configurar_destinatario_contrato(item, delay_step=0.0)

    # Verificou que tentou clicar duas vezes (primeira normal, segunda com force=True)
    assert mock_btn.click.call_count == 2
    mock_dest_sel.select_option.assert_called_once()

