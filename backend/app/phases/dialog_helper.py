import time
from typing import Callable, Optional
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError, Error as PlaywrightError


def fechar_popups_alerta(
    page: Page,
    log_callback: Optional[Callable[[str, str], None]] = None,
    nro_cotacao: str = "",
    timeout_ms: int = 1500
) -> bool:
    """
    Verifica se há popups, caixas de diálogo ou modais visíveis na tela (jQuery UI Dialog,
    SweetAlert, avisos de NF duplicada, confirmações de rotina, etc.), registra o conteúdo
    no log da automação e fecha o diálogo com segurança para que os eventos de ponteiro
    (cliques e foco) não fiquem bloqueados.

    Retorna True se algum popup foi detectado e fechado, False caso contrário.
    """
    item_prefix = f"[Item {nro_cotacao}] " if nro_cotacao else ""
    popup_encontrado = False

    # 1. Tratamento específico para jQuery UI Dialog (.ui-dialog)
    try:
        dialog_locator = page.locator('.ui-dialog:visible')
        if dialog_locator.count() > 0:
            popup_encontrado = True
            
            # Tenta capturar a mensagem do diálogo para enriquecer o log
            mensagem_dialogo = ""
            try:
                for selector in ['.swconfirm', '.ui-dialog-content', '.ui-dialog-title']:
                    loc = dialog_locator.locator(selector).first
                    if loc.is_visible(timeout=300):
                        txt = loc.inner_text().strip()
                        if txt:
                            mensagem_dialogo = txt
                            break
            except Exception:
                pass

            if mensagem_dialogo:
                # Normaliza espaços/quebras de linha para o log
                msg_limpa = " ".join(mensagem_dialogo.split())
                if log_callback:
                    log_callback(f"[Popup] {item_prefix}Pop-up detectado: \"{msg_limpa}\". Fechando...", "AVISO")
            else:
                if log_callback:
                    log_callback(f"[Popup] {item_prefix}Pop-up modal (jQuery UI) detectado na tela. Fechando...", "AVISO")

            # Tenta clicar no botão 'OK' do diálogo
            clicado = False
            botoes_ok_selectors = [
                '.ui-dialog:visible .ui-dialog-buttonpane button:has-text("OK")',
                '.ui-dialog:visible .ui-dialog-buttonset button:has-text("OK")',
                '.ui-dialog:visible button:has-text("OK")',
                '.ui-dialog:visible .ui-button:has-text("OK")',
                '.ui-dialog:visible button.ui-dialog-titlebar-close',
                '.ui-dialog:visible .ui-dialog-titlebar-close'
            ]
            for btn_sel in botoes_ok_selectors:
                try:
                    btn = page.locator(btn_sel).first
                    if btn.is_visible(timeout=500):
                        btn.click(timeout=2000)
                        clicado = True
                        break
                except Exception:
                    continue

            # Fallback JavaScript se o clique não fechar ou se o overlay persistir
            page.wait_for_timeout(300)
            try:
                # Se o diálogo ou overlay ainda estiver visível, força o fechamento via DOM/jQuery
                dialog_ainda_visivel = page.locator('.ui-dialog:visible, .ui-widget-overlay:visible').count() > 0
                if dialog_ainda_visivel:
                    page.evaluate("""() => {
                        // Tenta fechar via jQuery UI se disponível
                        if (window.jQuery && window.jQuery.fn && window.jQuery.fn.dialog) {
                            try {
                                window.jQuery('.ui-dialog-content').dialog('close');
                            } catch (e) {}
                        }
                        // Remove overlays e oculta diálogos remanescentes
                        document.querySelectorAll('.ui-widget-overlay').forEach(el => el.remove());
                        document.querySelectorAll('.ui-dialog').forEach(el => {
                            el.style.display = 'none';
                        });
                    }""")
                    if log_callback and not clicado:
                        log_callback(f"[Popup] {item_prefix}Pop-up fechado via contingência DOM/JavaScript.", "DEBUG")
            except Exception:
                pass

            page.wait_for_timeout(300)
            return True

    except Exception as e_dlg:
        # Se houver erro na checagem de diálogo, continua para outros seletores
        pass

    # 2. Tratamento para outros tipos de modais e alertas (SweetAlert, Bootstrap, etc.)
    outros_seletores = [
        'button:has-text("OK")',
        'input[type="button"][value="OK"]',
        'input[type="submit"][value="OK"]',
        'a:has-text("OK")',
        '.swal2-confirm',
        '.swal2-modal button',
        '.modal-footer button',
        '.ui-dialog-buttonpane button',
    ]

    for sel in outros_seletores:
        try:
            loc = page.locator(sel)
            if loc.count() > 0 and loc.first.is_visible(timeout=200):
                if log_callback and not popup_encontrado:
                    log_callback(f"[Popup] {item_prefix}Pop-up de alerta detectado ({sel}). Fechando...", "AVISO")
                loc.first.click(timeout=1000)
                page.wait_for_timeout(300)
                popup_encontrado = True
                break
        except Exception:
            continue

    # 3. Garante que nenhum overlay bloqueador (.ui-widget-overlay) fique ativo
    try:
        overlay_loc = page.locator('.ui-widget-overlay:visible')
        if overlay_loc.count() > 0:
            page.evaluate("""() => {
                document.querySelectorAll('.ui-widget-overlay').forEach(el => el.remove());
            }""")
            popup_encontrado = True
    except Exception:
        pass

    return popup_encontrado


def esperar_e_fechar_popups(
    page: Page,
    log_callback: Optional[Callable[[str, str], None]] = None,
    nro_cotacao: str = "",
    duracao_segundos: float = 2.0,
    intervalo_segundos: float = 0.3
) -> bool:
    """
    Executa verificação periódica por um breve período para capturar popups
    que possam ser carregados de forma assíncrona após transições de página ou submissões AJAX.
    """
    inicio = time.time()
    fechou_algum = False
    while time.time() - inicio < duracao_segundos:
        if fechar_popups_alerta(page, log_callback, nro_cotacao):
            fechou_algum = True
        time.sleep(intervalo_segundos)
    return fechou_algum
