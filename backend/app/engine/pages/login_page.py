from __future__ import annotations

import time
from typing import Callable, Optional
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from ...domain.errors import AuthenticationError, NavigationError
from ..dialog_guard import DialogGuard


class LoginPage:
    """Page Object para a tela de autenticação do portal LogTudo (e-Login)."""

    LOGIN_URL = "https://logtudo.e-login.net/"

    def __init__(self, page: Page, log_callback: Optional[Callable[[str, str], None]] = None):
        self.page = page
        self.log = log_callback or (lambda m, l="INFO": None)

    def login(self, usuario: str, senha: str, url_destino: str) -> None:
        """Executa a autenticação e aguarda o redirecionamento."""
        if not usuario or not senha:
            raise AuthenticationError("Usuário e senha são obrigatórios.", reason="Dados Vazios")

        self.log("[F2] Navegando para a página de login...", "INFO")
        try:
            self.page.goto(self.LOGIN_URL, wait_until="commit", timeout=30000)
        except Exception as e:
            raise NavigationError(f"Falha ao carregar página de login: {e}", url=self.LOGIN_URL, step="Fase 2 - Login")

        # 1. Preenche usuário e senha assim que o formulário estiver visível no DOM
        self.log("[F2] Preenchendo credenciais...", "DEBUG")
        try:
            usr_input = self.page.locator('input[name="usuario"]')
            usr_input.wait_for(state="visible", timeout=15000)
            usr_input.fill(usuario)
            self.page.locator('input[name="senha"]').fill(senha)
        except Exception as e:
            raise AuthenticationError(f"Erro ao preencher campos de login: {e}", reason="Campos Inacessíveis")

        # 2. Clica no botão Entrar
        btn_submit = self.page.locator("#botaoSubmit, button:has-text('Entrar'), input[type='submit']")
        try:
            btn_submit.first.click()
        except Exception as e:
            raise AuthenticationError(f"Erro ao submeter formulário de login: {e}", reason="Botão Indisponível")

        # 3. Monitoramento de resposta e validação
        self.log("[F2] Validando autenticação...", "DEBUG")
        login_ok = False
        for _ in range(30):
            DialogGuard.dismiss_all_popups(self.page, self.log, "Login")

            # Erro na UI
            err_el = self.page.locator("p.error-message, .alert-danger")
            if err_el.count() > 0 and err_el.first.is_visible():
                msg = err_el.first.inner_text().strip()
                raise AuthenticationError(f"Erro de login: {msg}", reason=msg)

            # Erro no SweetAlert
            swal_el = self.page.locator(".swal2-html-container")
            if swal_el.count() > 0 and swal_el.first.is_visible():
                msg = swal_el.first.inner_text().strip()
                if any(w in msg.lower() for w in ["inválid", "incorret", "expirad"]):
                    raise AuthenticationError(f"Alerta de autenticação: {msg}", reason=msg)

            # Validação 2FA
            token_field = self.page.locator('input[name="token"]')
            if token_field.count() > 0 and token_field.first.is_visible():
                self.log("[F2] 2FA detectado. Aguardando até 30s para inserção manual...", "AVISO")
                try:
                    self.page.wait_for_navigation(timeout=30000, wait_until="load")
                    login_ok = True
                    break
                except PlaywrightTimeoutError:
                    raise AuthenticationError("Timeout aguardando 2FA.", reason="2FA Timeout")

            # Botão sumiu -> Login avançou
            if not self.page.locator("#botaoSubmit").is_visible():
                time.sleep(0.5)
                if not self.page.locator("p.error-message").is_visible():
                    login_ok = True
                    break

            time.sleep(0.5)

        if not login_ok:
            raise AuthenticationError("Timeout ao concluir autenticação.", reason="Timeout Geral")

        self.log("[F2] Login realizado com sucesso.", "SUCESSO")

        # 4. Navegação para URL de destino se informada
        if url_destino:
            self.log("[F2] Navegando para o módulo de Conhecimentos...", "INFO")
            try:
                self.page.goto(url_destino, wait_until="domcontentloaded", timeout=30000)
            except Exception as e:
                raise NavigationError(f"Falha ao carregar destino: {e}", url=url_destino, step="Fase 2 - Destino")

    def logout(self) -> None:
        """
        Executa logout formal da sessão no ERP LogTudo.
        Descarta popups pendentes, tenta clicar em Sair na interface e
        garante limpeza defensiva dos cookies do contexto.
        """
        self.log("[F2] Executando logout formal da sessão...", "INFO")
        DialogGuard.dismiss_all_popups(self.page, self.log, "Logout")

        # 1. Tenta acionar o menu do usuário e clicar no botão 'Sair'
        try:
            user_menu = self.page.locator("button.dropbtn, .dropbtn, .user-menu, #menu-usuario").first
            if user_menu.is_visible():
                user_menu.hover(timeout=3000)

            sair_locator = self.page.locator("a:has-text('Sair'), button:has-text('Sair'), text='Sair'").first
            if sair_locator.is_visible():
                sair_locator.click(timeout=3000)
                self.page.wait_for_timeout(500)
        except Exception as e:
            self.log(f"[F2] Aviso ao interagir com menu de logout: {e}", "DEBUG")

        # 2. Limpeza defensiva de cookies para assegurar término da sessão no cliente
        try:
            if self.page.context:
                self.page.context.clear_cookies()
        except Exception as e_cookies:
            self.log(f"[F2] Aviso ao limpar cookies de sessão: {e_cookies}", "DEBUG")

        self.log("[F2] Logout e limpeza de cookies concluídos.", "SUCESSO")

