from __future__ import annotations

import time
from typing import Callable, Optional
from playwright.sync_api import Page


class DialogGuard:
    """
    Guardião e interceptor ativo de diálogos, popups modais (jQuery UI, SweetAlert2)
    e alertas do portal e-Login, garantindo que eventos de ponteiro nunca fiquem bloqueados.
    """

    @staticmethod
    def dismiss_all_popups(
        page: Page,
        log_callback: Optional[Callable[[str, str], None]] = None,
        context_prefix: str = "",
        max_wait_ms: int = 1500,
    ) -> bool:
        """
        Detecta e fecha de forma resiliente modais jQuery UI, SweetAlert e overlays de bloqueio.
        Retorna True se algum diálogo foi fechado.
        """
        prefix = f"[{context_prefix}] " if context_prefix else ""
        dismissed = False

        # 1. jQuery UI Dialog (.ui-dialog)
        try:
            dialog_loc = page.locator('.ui-dialog:visible')
            if dialog_loc.count() > 0:
                dismissed = True
                msg = ""
                try:
                    for sel in ['.swconfirm', '.ui-dialog-content', '.ui-dialog-title']:
                        loc = dialog_loc.locator(sel).first
                        if loc.is_visible(timeout=200):
                            msg = loc.inner_text().strip()
                            if msg:
                                break
                except Exception:
                    pass

                if msg and log_callback:
                    clean_msg = " ".join(msg.split())
                    log_callback(f"[Popup] {prefix}Modal detectado: \"{clean_msg}\". Fechando...", "AVISO")
                elif log_callback:
                    log_callback(f"[Popup] {prefix}Modal jQuery UI detectado. Fechando...", "AVISO")

                # Clica em botões de confirmação/fechamento
                btn_selectors = [
                    'div[aria-describedby="dialogo_distancia_km"] button',
                    '#dialogo_distancia_km ~ .ui-dialog-buttonpane button',
                    '.ui-dialog:visible .ui-dialog-buttonpane button:has-text("OK")',
                    '.ui-dialog:visible .ui-dialog-buttonpane button:has-text("Sim")',
                    '.ui-dialog:visible .ui-dialog-buttonpane button:has-text("Confirmar")',
                    '.ui-dialog:visible .ui-dialog-buttonpane button:has-text("Continuar")',
                    '.ui-dialog:visible .ui-dialog-buttonpane button:has-text("Prosseguir")',
                    '.ui-dialog:visible .ui-dialog-buttonpane button:has-text("Ciente")',
                    '.ui-dialog:visible .ui-dialog-buttonpane button:has-text("Aceitar")',
                    '.ui-dialog:visible .ui-dialog-buttonpane button',
                    '.ui-dialog:visible .ui-dialog-buttonset button:has-text("OK")',
                    '.ui-dialog:visible .ui-dialog-buttonset button:has-text("Sim")',
                    '.ui-dialog:visible .ui-dialog-buttonset button:has-text("Confirmar")',
                    '.ui-dialog:visible .ui-dialog-buttonset button:has-text("Continuar")',
                    '.ui-dialog:visible button:has-text("OK")',
                    '.ui-dialog:visible .ui-button:has-text("OK")',
                    '.ui-dialog:visible button:has-text("Sim")',
                    '.ui-dialog:visible button:has-text("Confirmar")',
                    '.ui-dialog:visible button:has-text("Continuar")',
                    '.ui-dialog:visible button:has-text("Prosseguir")',
                    '.ui-dialog:visible button:has-text("Ciente")',
                    '.ui-dialog:visible button:has-text("Aceitar")',
                    '.ui-dialog:visible button.ui-dialog-titlebar-close',
                    '.ui-dialog:visible .ui-dialog-titlebar-close',
                ]
                for btn_sel in btn_selectors:
                    try:
                        btn = page.locator(btn_sel).first
                        if btn.is_visible(timeout=300):
                            btn.click(timeout=1500)
                            break
                    except Exception:
                        continue

                # Contingência DOM se overlay persistir
                page.wait_for_timeout(200)
                try:
                    if page.locator('.ui-dialog:visible, .ui-widget-overlay:visible, .swal2-container:visible, .sweet-overlay:visible, [aria-describedby="dialogo_distancia_km"]:visible').count() > 0:
                        page.evaluate("""() => {
                            if (window.jQuery && window.jQuery.fn && window.jQuery.fn.dialog) {
                                try { window.jQuery('#dialogo_distancia_km').dialog('close'); } catch (e) {}
                                try { window.jQuery('.ui-dialog-content').dialog('close'); } catch (e) {}
                            }
                            document.querySelectorAll('.ui-widget-overlay, .swal2-container, .sweet-overlay, .modal-backdrop, .blockUI').forEach(el => el.remove());
                            document.querySelectorAll('.ui-dialog').forEach(el => el.style.display = 'none');
                        }""")
                except Exception:
                    pass

                return True
        except Exception:
            pass

        # 2. SweetAlert (v1 e v2) & Modais Genéricos / Bootstrap
        other_selectors = [
            # SweetAlert 2
            '.swal2-confirm',
            '.swal2-actions button.swal2-confirm',
            '.swal2-actions button:not(.swal2-cancel)',
            '.swal2-modal button',
            # SweetAlert 1
            '.sweet-alert button.confirm',
            '.sweet-alert .sa-confirm-button-container button',
            # Botões afirmativos comuns
            'button:has-text("OK")',
            'button:has-text("Sim")',
            'button:has-text("Confirmar")',
            'button:has-text("Continuar")',
            'button:has-text("Prosseguir")',
            'button:has-text("Ciente")',
            'button:has-text("Aceitar")',
            'button:has-text("Concordo")',
            'button:has-text("Entendi")',
            'input[type="button"][value="OK"]',
            'input[type="button"][value="Sim"]',
            'input[type="button"][value="Confirmar"]',
            'input[type="button"][value="Continuar"]',
            'input[type="submit"][value="OK"]',
            'input[type="submit"][value="Sim"]',
            'input[type="submit"][value="Confirmar"]',
            'a:has-text("OK")',
            'a:has-text("Sim")',
            'a:has-text("Confirmar")',
            'a:has-text("Continuar")',
            'a:has-text("Prosseguir")',
            '.modal:visible .modal-footer button.btn-primary',
            '.modal:visible .modal-footer button:not(.btn-secondary)',
            '.modal-footer button',
        ]
        for sel in other_selectors:
            try:
                loc = page.locator(sel)
                if loc.count() > 0 and loc.first.is_visible(timeout=150):
                    if log_callback and not dismissed:
                        log_callback(f"[Popup] {prefix}Alerta fechado ({sel}).", "AVISO")
                    loc.first.click(timeout=1000)
                    dismissed = True
                    break
            except Exception:
                continue

        # 3. Remoção de overlays bloqueadores remanescentes
        try:
            overlay_loc = page.locator('.ui-widget-overlay:visible, .swal2-container:visible, .sweet-overlay:visible, .modal-backdrop:visible, .blockUI:visible')
            if overlay_loc.count() > 0:
                page.evaluate("""() => {
                    document.querySelectorAll('.ui-widget-overlay, .swal2-container, .sweet-overlay, .modal-backdrop, .blockUI').forEach(el => el.remove());
                }""")
                dismissed = True
        except Exception:
            pass

        return dismissed

    @staticmethod
    def detectar_erro_negocio(
        page: Page,
        log_callback: Optional[Callable[[str, str], None]] = None,
        context_prefix: str = "",
    ) -> Optional[str]:
        """
        Detecta o alerta genérico de erro de negócio do portal e-Login
        (div.rotina-generica.alert-message.error, SweetAlert, alertas Bootstrap, etc.)
        e extrai o motivo específico. Retorna a mensagem ou None se não houver erro.
        """
        error_selectors = [
            'div.rotina-generica.alert-message.error p.regular-small-text',
            'div.rotina-generica.alert-message.error',
            '.alert-danger:visible',
            '.alert-error:visible',
            '.swal2-html-container:visible',
            '.sweet-alert p:visible',
        ]
        for sel in error_selectors:
            try:
                loc = page.locator(sel)
                if loc.count() > 0 and loc.first.is_visible():
                    raw_text = loc.first.inner_text().strip()
                    msg = " ".join(raw_text.split())
                    if msg:
                        if log_callback:
                            log_callback(f"[ErroNegocio] {context_prefix}{msg}".strip(), "ERRO")
                        return msg
            except Exception:
                continue
        return None

    @staticmethod
    def wait_and_dismiss(
        page: Page,
        log_callback: Optional[Callable[[str, str], None]] = None,
        context_prefix: str = "",
        duration_seconds: float = 1.5,
        interval_seconds: float = 0.2,
    ) -> bool:
        """Verifica e fecha popups repetidamente durante um breve intervalo."""
        start = time.time()
        any_dismissed = False
        while time.time() - start < duration_seconds:
            if DialogGuard.dismiss_all_popups(page, log_callback, context_prefix):
                any_dismissed = True
            time.sleep(interval_seconds)
        return any_dismissed
