from pathlib import Path
from playwright.sync_api import Browser, BrowserContext, Page, Error
from typing import Callable, Optional, Tuple
import os
import traceback

from Conectividade.playwright_vps_connect import PlaywrightVPSClient, PlaywrightVPSConfig

ARTIFACTS_TEMP_DIR = Path(__file__).resolve().parents[1] / "data" / "artifacts" / "tmp"


def launch_browser(log_callback: Callable) -> Optional[Tuple[any, Browser, BrowserContext]]:
    """
    Inicia o Playwright e o navegador configurado.
    """
    try:
        log_callback("[F2] Iniciando Playwright (config VPS)...", "DEBUG")
        ARTIFACTS_TEMP_DIR.mkdir(parents=True, exist_ok=True)

        headless_env = os.getenv("PLAYWRIGHT_HEADLESS", "false")
        headless = headless_env.strip().lower() == "true"
        modo_navegador = "headless" if headless else "visivel"
        log_callback(f"[F2] Modo do navegador: {modo_navegador} (PLAYWRIGHT_HEADLESS={headless_env!r}).", "DEBUG")
        cfg = PlaywrightVPSConfig(
            headless=headless,
            browser_channel=os.getenv("PLAYWRIGHT_BROWSER_CHANNEL", "chrome").strip() or None,
            record_video_dir=str(ARTIFACTS_TEMP_DIR),
        )

        client = PlaywrightVPSClient(cfg)
        client.start()
        browser = client.browser
        context = client.context
        log_callback("[F2] Navegador Chrome iniciado.", "DEBUG")
        
        return client.playwright, browser, context
        
    except Exception as e:
        log_callback("[F2] Erro ao iniciar o Playwright.", "ERRO")
        if "Executable doesn't exist" in str(e):
            log_callback("[F2] Possível causa: binários do Playwright ausentes na imagem/container.", "ERRO")
            log_callback("[F2] Rebuild a imagem do backend para instalar Chrome e FFmpeg: docker compose build backend.", "ERRO")
        log_callback(f"Detalhe: {e!r}", "DEBUG")
        log_callback(f"Traceback: {traceback.format_exc()}", "DEBUG")
        return None, None, None

def perform_login(
    browser_context: BrowserContext,
    login: str,
    senha: str,
    url_destino: str,
    log_callback: Callable,
    existing_page: Optional[Page] = None,
    browser_log_callback: Optional[Callable[[str, str], None]] = None,
) -> Optional[Page]:
    """
    Abre uma nova página (ou usa uma existente), realiza o login e navega para a URL de destino.
    """
    try:
        if existing_page:
            page = existing_page
            log_callback("[F2] Reutilizando página existente para login.", "DEBUG")
        elif browser_context.pages:
            page = browser_context.pages[0]
            log_callback("[F2] Reutilizando página existente criada no setup do navegador.", "DEBUG")
            if browser_log_callback:
                page.on("pageerror", lambda err: browser_log_callback(str(err), "ERROR"))
                page.on("console", lambda msg: browser_log_callback(msg.text, msg.type.upper()))
        else:
            page = browser_context.new_page() # Cria uma nova página se não houver uma existente
            log_callback("[F2] Nova página aberta para login inicial.", "DEBUG")
            if browser_log_callback:
                page.on("pageerror", lambda err: browser_log_callback(str(err), "ERROR"))
                page.on("console", lambda msg: browser_log_callback(msg.text, msg.type.upper()))
        
        log_callback("[F2] Navegando para a página de login...", "INFO")
        page.goto("https://logtudo.e-login.net/", wait_until="load")

        log_callback("[F2] Preenchendo usuário...", "DEBUG")

        # Usamos seletores CSS [name="..."]
        page.fill('[name="usuario"]', login)
        
        log_callback("[F2] Preenchendo senha...", "DEBUG")
        page.fill('[name="senha"]', senha) # <-- CORREÇÃO: Estava 'login', mudei para 'senha'

        # ETAPA 2: Clicar em Entrar
        log_callback("[F2] Clicando em 'Entrar' (#botaoSubmit)...", "INFO")
        
        # Usamos o ID #botaoSubmit que é mais confiável
        botao_submit = page.locator("#botaoSubmit")
        
        try:
            botao_submit.wait_for(state="visible", timeout=10000)
        except Error:
            log_callback("[F2] Erro: Botão de submit '#botaoSubmit' não está visível.", "ERRO")
            return None

        # Combina o clique com a monitoração de erros ou mudança de rota
        try:
            botao_submit.click()
            
            login_sucesso = False
            url_login_inicial = page.url
            
            for _ in range(60): # Aguarda até 60 segundos
                # 1. Verifica se apareceu erro de texto na interface
                error_p = page.locator("p.error-message")
                if error_p.is_visible():
                    msg = error_p.text_content().strip()
                    log_callback(f"[F2] Erro de Login (UI): {msg}", "ERRO")
                    return None
                    
                # 2. Verifica erro no SweetAlert
                swal_erro = page.locator(".swal2-html-container")
                if swal_erro.is_visible():
                    msg = swal_erro.text_content().strip()
                    if "inválida" in msg.lower() or "incorret" in msg.lower() or "expirada" in msg.lower():
                        log_callback(f"[F2] Erro de Login (Alerta): {msg}", "ERRO")
                        return None
                
                # 3. Verifica se solicitou 2FA
                token_field = page.locator('input[name="token"]')
                if token_field.is_visible():
                    log_callback("[F2] Validação 2FA detectada. Aguardando 30s para intervenção manual...", "AVISO")
                    try:
                        page.wait_for_navigation(timeout=30000, wait_until="load")
                        login_sucesso = True
                        break
                    except Error:
                        log_callback("[F2] Timeout aguardando intervenção no 2FA.", "ERRO")
                        return None
                
                # 4. Verifica se saiu da tela de login
                if page.url != url_login_inicial and "login" not in page.url.lower():
                    login_sucesso = True
                    break
                    
                page.wait_for_timeout(1000)

            if not login_sucesso:
                log_callback("[F2] Erro: Timeout aguardando o login concluir. A tela permaneceu inalterada ou travou.", "ERRO")
                return None

        except Error as e_login:
             log_callback(f"[F2] Falha ao executar login: {e_login}", "ERRO")
             return None

        log_callback("[F2] Login (aparentemente) bem-sucedido.", "SUCESSO")

        # ETAPA 3: Navegar para a URL de destino
        log_callback("[F2] Navegando para a URL de destino...", "INFO")
        # Alterado para 'load' e timeout aumentado para 2 minutos.
        # 'load' espera a página e todos os recursos (imagens, CSS) serem carregados.
        # É mais robusto que 'networkidle' para páginas com atividade em background.
        page.goto(url_destino, wait_until="load", timeout=120000)
        
        page_title = page.title()
        log_callback(f"[F2] Página de destino '{page_title}' carregada.", "SUCESSO")
        
        return page

    except Error as e:
        log_callback(f"Erro de Playwright na Fase 2: {e}", "ERRO")
        return None
    except Exception as e:
        log_callback(f"Erro inesperado na Fase 2: {e}", "ERRO")
        import traceback
        log_callback(f"Traceback: {traceback.format_exc()}", "DEBUG")
        return None
