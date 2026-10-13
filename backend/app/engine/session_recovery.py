from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional
from playwright.sync_api import BrowserContext, Page

from ..domain.errors import AutomationError
from .dialog_guard import DialogGuard
from .pages.login_page import LoginPage


class RecoveryStage(str, Enum):
    STAGE_1_SOFT_RELOAD = "soft_reload"
    STAGE_2_HARD_RESET = "hard_reset"
    STAGE_3_FRESH_PAGE = "fresh_page"


class RecoveryStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"


@dataclass(frozen=True)
class HealthCheckResult:
    healthy: bool
    reason: str


@dataclass(frozen=True)
class RecoveryResult:
    status: RecoveryStatus
    stage: RecoveryStage
    page: Page
    message: str
    error: Optional[Exception] = None


class SessionRecoveryManager:
    """
    Gerenciador determinístico e tipado de recuperação de sessão (Padrão Matt Pocock).
    Aplica estratégia graduada:
      - Estágio 1 (Leve): Limpeza de diálogos e recarregamento da rota base com checagem de saúde.
      - Estágio 2 (Última Instância): Reset completo via logout formal, limpeza de cookies e novo login.
      - Estágio 3 (Contingência): Descarte de página corrompida e abertura de nova aba autenticada.
    """

    def __init__(
        self,
        usuario: str,
        senha: str,
        url_form: str,
        log_callback: Optional[Callable[[str, str], None]] = None,
        delay: float = 0.1,
    ) -> None:
        self.usuario = usuario
        self.senha = senha
        self.url_form = url_form
        self.log = log_callback or (lambda m, l="INFO": None)
        self.delay = delay

    def check_form_health(self, page: Optional[Page]) -> HealthCheckResult:
        """Verifica a integridade funcional do formulário e da sessão ativa."""
        if not page or page.is_closed():
            return HealthCheckResult(healthy=False, reason="Página do navegador está fechada ou inacessível.")

        current_url = page.url.lower()
        if "login" in current_url and "rotinas" not in current_url:
            return HealthCheckResult(healthy=False, reason="Sessão desconectada (redirecionada para login).")

        DialogGuard.dismiss_all_popups(page, self.log, "HealthCheck")

        try:
            agencia_sel = page.locator('select[name="dados_agencias_id"]').first
            if agencia_sel.is_visible():
                return HealthCheckResult(healthy=True, reason="Formulário de Conhecimento visível e operacional.")
        except Exception as e:
            return HealthCheckResult(healthy=False, reason=f"Erro ao verificar seletores do formulário: {e}")

        return HealthCheckResult(healthy=False, reason="Campo principal do formulário (dados_agencias_id) não visível.")

    def _should_force_hard_reset(self, error: Optional[Exception], force_hard_reset: bool) -> tuple[bool, str]:
        """
        Determina se a recuperação deve executar obrigatoriamente o Reset Completo (logout -> login).
        No ERP LogTudo (PHP/BSoft), dados parciais inseridos são mantidos na sessão do servidor.
        Erros de valores não encontrados ou falhas de formulário NÃO são limpos por refresh.
        """
        if force_hard_reset:
            return True, "Reset forçado por parâmetro explícito."
        if error is not None:
            return True, f"Falha de processamento/dados residuais ({error}). Logout obrigatório para expurgar sessão do ERP."
        return False, "Nenhum erro de processamento informado; permitindo tentativa de recuperação leve."

    def recover(
        self,
        page: Optional[Page],
        context: Optional[BrowserContext] = None,
        error: Optional[Exception] = None,
        force_hard_reset: bool = False,
    ) -> RecoveryResult:
        """
        Executa o pipeline graduado de recuperação.
        Se houver erro de processamento/dados na cotação ou force_hard_reset=True,
        executa diretamente o Reset Completo (logout -> login) para expurgar dados residuais do ERP.
        Caso contrário, tenta primeiro a recuperação leve (soft reload).
        """
        self.log("[Recovery] Iniciando procedimento de recuperação de sessão...", "DEBUG")

        if not page or page.is_closed():
            self.log("[Recovery] Página nula ou fechada. Acionando criação de nova aba limpa...", "AVISO")
            return self._recover_fresh_page(context)

        should_hard_reset, reason = self._should_force_hard_reset(error, force_hard_reset)

        # 1. Se não requer hard reset, tenta primeiro a Recuperação Leve (Soft Reload)
        if not should_hard_reset:
            self.log("[Recovery] Estágio 1/2: Tentando recuperação leve (fechar modais e recarregar rota)...", "DEBUG")
            soft_health = self._execute_soft_reload(page)
            if soft_health.healthy:
                self.log(f"[Recovery] Recuperação leve bem-sucedida: {soft_health.reason}", "DEBUG")
                return RecoveryResult(
                    status=RecoveryStatus.SUCCESS,
                    stage=RecoveryStage.STAGE_1_SOFT_RELOAD,
                    page=page,
                    message=soft_health.reason,
                )
            self.log(f"[Recovery] Recuperação leve insuficiente: {soft_health.reason}", "AVISO")
        else:
            self.log(f"[Recovery] {reason}", "AVISO")

        # 2. Estágio 2: ÚLTIMA INSTÂNCIA - Reset Completo (Logout -> Login)
        self.log("[Recovery] Estágio 2/2 (ÚLTIMA INSTÂNCIA): Executando Reset formal da sessão (logout -> login)...", "INFO")
        hard_health = self._execute_hard_reset(page)
        if hard_health.healthy:
            self.log(f"[Recovery] Reset formal concluído com sucesso: {hard_health.reason}", "SUCESSO")
            return RecoveryResult(
                status=RecoveryStatus.SUCCESS,
                stage=RecoveryStage.STAGE_2_HARD_RESET,
                page=page,
                message=hard_health.reason,
            )

        # 3. Estágio 3: Contingência Extrema com Nova Aba Limpa
        self.log(f"[Recovery] Falha no reset na página ativa ({hard_health.reason}). Acionando contingência extrema...", "AVISO")
        return self._recover_fresh_page(context)


    def _execute_soft_reload(self, page: Page) -> HealthCheckResult:
        """Estágio 1: Descarta popups e recarrega a URL base."""
        try:
            DialogGuard.dismiss_all_popups(page, self.log, "SoftReload")
            page.goto(self.url_form, wait_until="load", timeout=25000)
            if self.delay > 0:
                time.sleep(self.delay)
            return self.check_form_health(page)
        except Exception as e:
            return HealthCheckResult(healthy=False, reason=f"Falha na navegação leve: {e}")

    def _execute_hard_reset(self, page: Page) -> HealthCheckResult:
        """Estágio 2 (Última Instância): Logout formal -> Novo Login."""
        try:
            login_page = LoginPage(page, log_callback=self.log)
            login_page.logout()
            login_page.login(self.usuario, self.senha, self.url_form)
            if self.delay > 0:
                time.sleep(self.delay)
            return self.check_form_health(page)
        except Exception as e:
            return HealthCheckResult(healthy=False, reason=f"Falha no fluxo de logout/login: {e}")

    def _recover_fresh_page(self, context: Optional[BrowserContext]) -> RecoveryResult:
        """Estágio 3: Cria nova aba limpa, limpa cookies e refaz autenticação."""
        if not context:
            err = AutomationError("Contexto do navegador indisponível para recuperação de sessão.")
            self.log(f"[Recovery] Erro fatal: {err}", "ERRO")
            raise err

        try:
            context.clear_cookies()
            new_page = context.new_page()
            login_page = LoginPage(new_page, log_callback=self.log)
            login_page.login(self.usuario, self.senha, self.url_form)
            health = self.check_form_health(new_page)
            if health.healthy:
                self.log("[Recovery] Nova página criada e autenticada com sucesso.", "SUCESSO")
                return RecoveryResult(
                    status=RecoveryStatus.SUCCESS,
                    stage=RecoveryStage.STAGE_3_FRESH_PAGE,
                    page=new_page,
                    message=health.reason,
                )
            raise AutomationError(f"Formulário não inicializou na nova aba: {health.reason}")
        except Exception as fatal_e:
            self.log(f"[Recovery] Falha crítica na contingência de nova aba: {fatal_e}", "ERRO")
            raise AutomationError(f"Falha irrecuperável de sessão: {fatal_e}") from fatal_e
