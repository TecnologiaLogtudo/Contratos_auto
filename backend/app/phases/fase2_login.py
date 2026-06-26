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

        # Combina o clique com a espera pela navegação
        try:
            with page.expect_navigation(timeout=60000, wait_until="load"):
                botao_submit.click()
                
        except Error as e_timeout:
            # Handle de Timeout (pode ser 2FA ou senha errada)
            log_callback(f"[F2] Timeout ao esperar navegação pós-login: {e_timeout}", "AVISO")
            
            # Verifica se é erro de senha
            try:
                erro_box = page.locator(".swal2-html-container")
                if erro_box.is_visible(timeout=3000): # Espera curta pelo erro
                    if "Usuário ou Senha inválida" in erro_box.text_content():
                        log_callback("[F2] Erro de Login: Usuário ou Senha inválida.", "ERRO")
                        return None
            except Error:
                pass # Ignora se não achar a caixa de erro

            # Verifica se é 2FA
            try:
                # Tenta localizar um campo comum de 2FA (ex: 'token')
                # (Ajuste 'input[name="token"]' se o seletor for outro)
                token_field = page.locator('input[name="token"]') 
                if token_field.is_visible(timeout=5000):
                    log_callback("[F2] Validação 2FA detectada. Aguardando 30s para intervenção manual...", "AVISO")
                    log_callback("[F2] Por favor, complete o 2FA no navegador.", "AVISO")
                    # Espera a próxima navegação (usuário completou o 2FA)
                    page.wait_for_navigation(timeout=30000, wait_until="load")
                else:
                    log_callback("[F2] Não foi possível detectar 2FA, mas o login travou.", "ERRO")
                    return None
            except Error:
                 log_callback("[F2] Login falhou (possível timeout ou erro desconhecido).", "ERRO")
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
