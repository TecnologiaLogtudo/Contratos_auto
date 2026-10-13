from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest

from backend.app.domain.errors import AutomationError
from backend.app.engine.session_recovery import (
    SessionRecoveryManager,
    RecoveryStage,
    RecoveryStatus,
    HealthCheckResult,
)
from backend.app.engine.pages.login_page import LoginPage


@pytest.fixture
def recovery_manager():
    return SessionRecoveryManager(
        usuario="usuario_teste",
        senha="senha_teste",
        url_form="https://logtudo.e-login.net/versoes/versao5.0/rotinas/formulario.php?rotina=trans_conhecimento",
        log_callback=lambda m, l="INFO": None,
        delay=0.0,
    )


def test_health_check_healthy_form(recovery_manager):
    mock_page = MagicMock()
    mock_page.is_closed.return_value = False
    mock_page.url = "https://logtudo.e-login.net/versoes/versao5.0/rotinas/formulario.php?rotina=trans_conhecimento"

    mock_select = MagicMock()
    mock_select.is_visible.return_value = True
    mock_page.locator.return_value.first = mock_select

    with patch("backend.app.engine.session_recovery.DialogGuard.dismiss_all_popups"):
        result = recovery_manager.check_form_health(mock_page)

    assert result.healthy is True
    assert "visível e operacional" in result.reason


def test_health_check_page_closed(recovery_manager):
    mock_page = MagicMock()
    mock_page.is_closed.return_value = True

    result = recovery_manager.check_form_health(mock_page)
    assert result.healthy is False
    assert "fechada" in result.reason


def test_health_check_redirected_to_login(recovery_manager):
    mock_page = MagicMock()
    mock_page.is_closed.return_value = False
    mock_page.url = "https://logtudo.e-login.net/login.php"

    result = recovery_manager.check_form_health(mock_page)
    assert result.healthy is False
    assert "desconectada" in result.reason


def test_health_check_agencia_select_missing(recovery_manager):
    mock_page = MagicMock()
    mock_page.is_closed.return_value = False
    mock_page.url = "https://logtudo.e-login.net/versoes/versao5.0/rotinas/formulario.php?rotina=trans_conhecimento"

    mock_select = MagicMock()
    mock_select.is_visible.return_value = False
    mock_page.locator.return_value.first = mock_select

    with patch("backend.app.engine.session_recovery.DialogGuard.dismiss_all_popups"):
        result = recovery_manager.check_form_health(mock_page)

    assert result.healthy is False
    assert "não visível" in result.reason


def test_recover_stage_1_success(recovery_manager):
    mock_page = MagicMock()
    mock_page.is_closed.return_value = False

    with patch.object(recovery_manager, "_execute_soft_reload", return_value=HealthCheckResult(True, "OK")) as mock_soft:
        with patch.object(recovery_manager, "_execute_hard_reset") as mock_hard:
            res = recovery_manager.recover(mock_page, force_hard_reset=False)

    assert res.status == RecoveryStatus.SUCCESS
    assert res.stage == RecoveryStage.STAGE_1_SOFT_RELOAD
    mock_soft.assert_called_once_with(mock_page)
    mock_hard.assert_not_called()


def test_recover_stage_2_last_resort_escalation(recovery_manager):
    mock_page = MagicMock()
    mock_page.is_closed.return_value = False

    # Estágio 1 falha -> Deve escalar automaticamente para a Última Instância (Estágio 2)
    with patch.object(recovery_manager, "_execute_soft_reload", return_value=HealthCheckResult(False, "Form corrompido")):
        with patch.object(recovery_manager, "_execute_hard_reset", return_value=HealthCheckResult(True, "Login ok")) as mock_hard:
            res = recovery_manager.recover(mock_page, force_hard_reset=False)

    assert res.status == RecoveryStatus.SUCCESS
    assert res.stage == RecoveryStage.STAGE_2_HARD_RESET
    mock_hard.assert_called_once_with(mock_page)


def test_recover_forced_hard_reset(recovery_manager):
    mock_page = MagicMock()
    mock_page.is_closed.return_value = False

    with patch.object(recovery_manager, "_execute_soft_reload") as mock_soft:
        with patch.object(recovery_manager, "_execute_hard_reset", return_value=HealthCheckResult(True, "Login ok")):
            res = recovery_manager.recover(mock_page, force_hard_reset=True)

    assert res.status == RecoveryStatus.SUCCESS
    assert res.stage == RecoveryStage.STAGE_2_HARD_RESET
    mock_soft.assert_not_called()


def test_recover_stage_3_fresh_page_contingency(recovery_manager):
    mock_page = MagicMock()
    mock_page.is_closed.return_value = False

    mock_context = MagicMock()
    new_page = MagicMock()
    mock_context.new_page.return_value = new_page

    with patch.object(recovery_manager, "_execute_soft_reload", return_value=HealthCheckResult(False, "Soft fail")):
        with patch.object(recovery_manager, "_execute_hard_reset", return_value=HealthCheckResult(False, "Hard fail")):
            with patch("backend.app.engine.session_recovery.LoginPage.login") as mock_login:
                with patch.object(recovery_manager, "check_form_health", return_value=HealthCheckResult(True, "Fresh OK")):
                    res = recovery_manager.recover(mock_page, context=mock_context)

    assert res.status == RecoveryStatus.SUCCESS
    assert res.stage == RecoveryStage.STAGE_3_FRESH_PAGE
    assert res.page == new_page
    mock_context.clear_cookies.assert_called_once()
    mock_login.assert_called_once()


def test_login_page_logout():
    mock_page = MagicMock()
    mock_context = MagicMock()
    mock_page.context = mock_context

    mock_menu = MagicMock()
    mock_menu.is_visible.return_value = True
    mock_sair = MagicMock()
    mock_sair.is_visible.return_value = True

    def locator_mock(selector):
        loc = MagicMock()
        if "dropbtn" in selector or "user-menu" in selector:
            loc.first = mock_menu
        elif "Sair" in selector:
            loc.first = mock_sair
        return loc

    mock_page.locator.side_effect = locator_mock

    login_page = LoginPage(mock_page)
    with patch("backend.app.engine.pages.login_page.DialogGuard.dismiss_all_popups"):
        login_page.logout()

    mock_menu.hover.assert_called_once()
    mock_sair.click.assert_called_once()
    mock_context.clear_cookies.assert_called_once()
