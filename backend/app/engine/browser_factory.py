from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional, Tuple
from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright

from ..domain.errors import AutomationError


@dataclass
class BrowserConfig:
    headless: bool = True
    browser_channel: Optional[str] = "chrome"
    timeout_ms: int = 45000
    viewport_width: int = 1366
    viewport_height: int = 768
    locale: str = "pt-BR"
    record_video_dir: Optional[str] = None
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    browser_args: list[str] = field(
        default_factory=lambda: [
            "--disable-blink-features=AutomationControlled",
            "--no-first-run",
            "--no-default-browser-check",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
        ]
    )


class BrowserFactory:
    """Fábrica responsável por instanciar e configurar o navegador Playwright."""

    @staticmethod
    def create_browser(
        config: Optional[BrowserConfig] = None,
        log_callback: Optional[Callable[[str, str], None]] = None,
    ) -> Tuple[Playwright, Browser, BrowserContext, Page]:
        log = log_callback or (lambda m, l="INFO": None)
        cfg = config or BrowserConfig()

        log("[Browser] Inicializando Playwright Chromium...", "DEBUG")
        pw = sync_playwright().start()

        launch_args: dict = {
            "headless": cfg.headless,
            "args": cfg.browser_args,
        }
        if cfg.browser_channel:
            launch_args["channel"] = cfg.browser_channel

        try:
            browser = pw.chromium.launch(**launch_args)
        except Exception as e:
            # Fallback se channel chrome não estiver disponível (usa chromium nativo do playwright)
            if cfg.browser_channel:
                log(f"[Browser] Canal '{cfg.browser_channel}' falhou ({e}). Tentando Chromium padrão...", "AVISO")
                launch_args.pop("channel", None)
                browser = pw.chromium.launch(**launch_args)
            else:
                pw.stop()
                raise AutomationError(f"Falha ao iniciar navegador: {e}", step="Browser Setup")

        context_args: dict = {
            "viewport": {"width": cfg.viewport_width, "height": cfg.viewport_height},
            "user_agent": cfg.user_agent,
            "locale": cfg.locale,
            "extra_http_headers": {
                "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
                "DNT": "1",
            },
        }
        if cfg.record_video_dir:
            Path(cfg.record_video_dir).mkdir(parents=True, exist_ok=True)
            context_args["record_video_dir"] = cfg.record_video_dir

        context = browser.new_context(**context_args)
        page = context.new_page()
        page.set_default_timeout(cfg.timeout_ms)
        page.set_default_navigation_timeout(cfg.timeout_ms)

        # Injeta script anti-detecção básico
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            Object.defineProperty(navigator, 'languages', { get: () => ['pt-BR', 'pt', 'en-US', 'en'] });
            window.chrome = { runtime: {} };
        """)

        log(f"[Browser] Sessão iniciada com sucesso (Headless={cfg.headless}).", "DEBUG")
        return pw, browser, context, page
