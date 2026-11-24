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
