from __future__ import annotations

import os
import threading
import time
import traceback
from pathlib import Path
from typing import Callable, Optional
from playwright.sync_api import Browser, BrowserContext, Page, Playwright

from ..domain.models import ItemContrato, ItemStatus, ItemResult, ExecutionSummary
from ..domain.errors import AutomationError, AuthenticationError
from .browser_factory import BrowserFactory, BrowserConfig
from .excel_processor import ExcelProcessor
from .dialog_guard import DialogGuard
from .strategies.strategy_factory import get_strategy
from .strategies.lactalis_strategy import LactalisSpecialBaseStrategy
from .pages.login_page import LoginPage
from .pages.cotacoes_page import CotacoesPage
from .pages.conhecimento_page import ConhecimentoPage
from .pages.frete_page import FretePage
from .pages.contrato_page import ContratoPage

URL_CONHECIMENTO_FORM = "https://logtudo.e-login.net/versoes/versao5.0/rotinas/formulario.php?rotina=trans_conhecimento&OP=O1&_qsf=1"


class ContractRunner:
    """
    Orquestrador unificado de execução de contratos com Playwright.
    Garante isolamento de transação por item, captura de evidências e tratamento exaustivo de erros.
    """

    def __init__(
        self,
        usuario: str,
        senha: str,
        excel_processor: Optional[ExcelProcessor] = None,
        output_filepath: Optional[str | Path] = None,
        headless: Optional[bool] = None,
        throttle_seconds: float = 2.5,
        log_callback: Optional[Callable[[str, str], None]] = None,
        screenshot_callback: Optional[Callable[[str], None]] = None,
        progress_callback: Optional[Callable[[int, int, Any], None]] = None,
        browser_config: Optional[BrowserConfig] = None,
        delay_fases: float = 0.1,
        delay_etapas: float = 0.05,
        dados_km: str = "20",
        aceitar_frete_minimo_antt: bool = True,
        stop_event: Optional[threading.Event] = None,
        pause_event: Optional[threading.Event] = None,
    ):
        self.usuario = usuario
        self.senha = senha
        self.processor = excel_processor
        self.output_filepath = Path(output_filepath) if output_filepath else None
        headless_env = os.getenv("PLAYWRIGHT_HEADLESS", "true").strip().lower() == "true"
        self.headless = headless if headless is not None else headless_env
        self.throttle_seconds = throttle_seconds
        self.log = log_callback or (lambda m, l="INFO": None)
        self.on_screenshot = screenshot_callback or (lambda name: None)
        self.on_progress = progress_callback or (lambda cur, tot, msg: None)
        self.browser_config = browser_config or BrowserConfig(headless=self.headless)
        self.delay_fases = delay_fases
        self.delay_etapas = delay_etapas
        self.dados_km = dados_km
        self.aceitar_frete_minimo_antt = aceitar_frete_minimo_antt
        self.stop_event = stop_event or threading.Event()
        self.pause_event = pause_event or threading.Event()
        if not self.pause_event.is_set():
            self.pause_event.set()

        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

        # Page Objects instanciados após login
        self.cotacoes_page: Optional[CotacoesPage] = None
        self.conhecimento_page: Optional[ConhecimentoPage] = None
        self.frete_page: Optional[FretePage] = None
        self.contrato_page: Optional[ContratoPage] = None

    def login(self) -> None:
        """Inicializa o navegador e realiza o login único compartilhado para o lote."""
        self.log("[F1] Inicializando navegador Playwright...", "INFO")
        self.playwright, self.browser, self.context, self.page = BrowserFactory.create_browser(
            config=self.browser_config, log_callback=self.log
        )
        login_page = LoginPage(self.page, log_callback=self.log)
        self.log("[F1] Executando autenticação no ERP LogTudo...", "INFO")
        login_page.login(self.usuario, self.senha, URL_CONHECIMENTO_FORM)
        self._take_screenshot("login_sucesso")

        self.cotacoes_page = CotacoesPage(self.page, log_callback=self.log)
        self.conhecimento_page = ConhecimentoPage(self.page, log_callback=self.log)
        self.frete_page = FretePage(self.page, log_callback=self.log)
        self.contrato_page = ContratoPage(self.page, log_callback=self.log)
        self.log("[F1] Login concluído com sucesso e sessão autenticada.", "SUCESSO")

    def process_single_item(self, item: ItemContrato) -> ItemResult:
        """Processa um único item/cotação pelas Fases 2 a 5 de forma isolada."""
        nro = item.nro_cotacao
        strategy = get_strategy(item.remetente)
        item_start = time.time()

        if not self.page or self.page.is_closed():
            self.login()

        self.log(f"[F2] Iniciando cotação {nro} (Remetente: {item.remetente}, Cidade: {item.cidade}/{item.uf})", "INFO")

        try:
            # Fase 2: Extração de Metadados (se Lactalis Especial)
            if isinstance(strategy, LactalisSpecialBaseStrategy) and self.cotacoes_page:
                self.cotacoes_page.extrair_metadados_cotacao(item, delay_step=self.delay_etapas)
            else:
                if "/rotinas/formulario.php" not in self.page.url or "trans_conhecimento" not in self.page.url:
                    self.page.goto(URL_CONHECIMENTO_FORM, wait_until="load", timeout=45000)
                    time.sleep(self.delay_fases)

            # Fase 3: Conhecimento
            if self.conhecimento_page:
                self.conhecimento_page.preencher_fase3(item, strategy, delay_step=self.delay_etapas)
            time.sleep(self.delay_fases)

            # Fase 4: Frete
            if self.frete_page:
                self.frete_page.preencher_fase4(item, strategy, delay_step=self.delay_etapas)
            time.sleep(self.delay_fases)

            # Fase 5: Contrato
            if self.contrato_page:
                self.contrato_page.preencher_e_salvar_fase5(
                    item,
                    strategy,
                    delay_step=self.delay_etapas,
                    dados_km=self.dados_km,
                    aceitar_frete_minimo_antt=self.aceitar_frete_minimo_antt,
                )

            self._take_screenshot(f"sucesso_contrato_cotacao_{nro}")
            duration = time.time() - item_start
            self.log(f"[F5] Cotação {nro} emitida com sucesso em {duration:.1f}s!", "SUCESSO")
            return ItemResult(
                nro_cotacao=nro,
                status=ItemStatus.CONCLUIDO,
                sucesso=True,
                cte_number=item.extracted_nro_pedido or "EMITIDO",
                execution_time_seconds=duration,
            )

        except Exception as err:
            err_msg = str(err)
            duration = time.time() - item_start
            self.log(f"[F5] FALHA na cotação {nro}: {err_msg}", "ERRO")
            self._take_screenshot(f"falha_cotacao_{nro}")
            self._reset_session()
            return ItemResult(
                nro_cotacao=nro,
                status=ItemStatus.ERRO,
                sucesso=False,
                motivo_erro=err_msg,
                execution_time_seconds=duration,
            )

    def close(self) -> None:
        """Fecha o navegador e limpa instâncias."""
        self._close_browser()

    def run(self) -> ExecutionSummary:
        start_time = time.time()
        summary = ExecutionSummary()

        try:
            # 1. Carrega e prepara itens da planilha
            items = self.processor.load_and_parse()
            pendentes = [i for i in items if i.status == ItemStatus.PENDENTE]
            summary.total = len(pendentes)

            if not pendentes:
                self.log("Nenhum contrato pendente para processamento.", "AVISO")
                self.processor.save_output(self.output_filepath)
                return summary

            # 2. Inicializa o Browser
            self.playwright, self.browser, self.context, self.page = BrowserFactory.create_browser(
                config=self.browser_config, log_callback=self.log
            )

            # 3. Executa Login Inicial
            login_page = LoginPage(self.page, log_callback=self.log)
            login_page.login(self.usuario, self.senha, URL_CONHECIMENTO_FORM)
            self._take_screenshot("login_sucesso")

            # 4. Instancia Page Objects
            cotacoes_page = CotacoesPage(self.page, log_callback=self.log)
            conhecimento_page = ConhecimentoPage(self.page, log_callback=self.log)
            frete_page = FretePage(self.page, log_callback=self.log)
            contrato_page = ContratoPage(self.page, log_callback=self.log)

            # 5. Processamento item a item
            total = len(pendentes)
            for idx, item in enumerate(pendentes, start=1):
                if self.stop_event.is_set():
                    self.log("Execução interrompida pelo usuário.", "AVISO")
                    break

                self._check_pause()
                nro = item.nro_cotacao
                strategy = get_strategy(item.remetente)

                self.on_progress(idx - 1, total, f"Processando cotação {nro}")
                self.log(f"================== Item {idx}/{total} (Cotação: {nro} | Remetente: {item.remetente}) ==================", "INFO")

                item_start = time.time()
                try:
                    # Preparação (se Lactalis Especial)
                    if isinstance(strategy, LactalisSpecialBaseStrategy):
                        cotacoes_page.extrair_metadados_cotacao(item, delay_step=self.delay_etapas)
                    else:
                        # Navega direto para o formulário de Conhecimento
                        if "/rotinas/formulario.php" not in self.page.url or "trans_conhecimento" not in self.page.url:
                            self.page.goto(URL_CONHECIMENTO_FORM, wait_until="load", timeout=45000)
                            time.sleep(self.delay_fases)

                    self._check_pause()
                    # Fase 3 - Conhecimento
                    conhecimento_page.preencher_fase3(item, strategy, delay_step=self.delay_etapas)
                    time.sleep(self.delay_fases)

                    self._check_pause()
                    # Fase 4 - Frete
                    frete_page.preencher_fase4(item, strategy, delay_step=self.delay_etapas)
                    time.sleep(self.delay_fases)

                    self._check_pause()
                    # Fase 5 - Contrato
                    contrato_page.preencher_e_salvar_fase5(
                        item,
                        strategy,
                        delay_step=self.delay_etapas,
                        dados_km=self.dados_km,
                        aceitar_frete_minimo_antt=self.aceitar_frete_minimo_antt,
                    )

                    # Sucesso
                    summary.sucessos += 1
                    self.processor.mark_success(nro)
                    self._take_screenshot(f"sucesso_contrato_cotacao_{nro}")
                    self.processor.save_output(self.output_filepath)
                    self.on_progress(idx, total, f"Cotação {nro} concluída com sucesso")
                    self.log(f"[Item {nro}] Concluído em {round(time.time() - item_start, 1)}s.", "SUCESSO")

                except Exception as err:
                    summary.erros += 1
                    err_msg = str(err)
                    self.log(f"[Item {nro}] FALHA: {err_msg}", "ERRO")
                    self._take_screenshot(f"falha_cotacao_{nro}")
                    self.processor.mark_error(nro, err_msg)
                    self.processor.save_output(self.output_filepath)

                    # Reset de sessão seguro após erro para não contaminar a próxima cotação
                    self._reset_session()

                time.sleep(self.delay_fases)

            summary.pendentes = summary.total - (summary.sucessos + summary.erros)
            self.log(f"Processamento concluído: {summary.sucessos} sucessos, {summary.erros} erros. Taxa: {summary.taxa_sucesso}%", "SUCESSO")

        except Exception as fatal_err:
            self.log(f"Erro fatal na execução: {fatal_err}", "ERRO")
            self.log(traceback.format_exc(), "DEBUG")
            self._take_screenshot("erro_fatal_execucao")
        finally:
            summary.duracao_segundos = time.time() - start_time
            self.processor.save_output(self.output_filepath)
            self._close_browser()

        return summary

    def _check_pause(self) -> None:
        while not self.pause_event.is_set():
            if self.stop_event.is_set():
                break
            time.sleep(0.2)

    def _reset_session(self) -> None:
        if self.stop_event.is_set():
            return
        self.log("[Session] Realizando reset e recarregamento da sessão...", "DEBUG")
        try:
            DialogGuard.dismiss_all_popups(self.page, self.log, "Reset")
            self.page.goto(URL_CONHECIMENTO_FORM, wait_until="load", timeout=30000)
            time.sleep(self.delay_fases)
        except Exception:
            try:
                login_page = LoginPage(self.page, log_callback=self.log)
                login_page.login(self.usuario, self.senha, URL_CONHECIMENTO_FORM)
            except Exception as e_login:
                self.log(f"[Session] Falha no relogin de reset: {e_login}", "AVISO")

    def _take_screenshot(self, name: str) -> None:
        try:
            if self.page and not self.page.is_closed():
                self.on_screenshot(name)
        except Exception:
            pass

    def _close_browser(self) -> None:
        try:
            if self.context:
                self.context.close()
        except Exception:
            pass
        try:
            if self.browser:
                self.browser.close()
        except Exception:
            pass
        try:
            if self.playwright:
                self.playwright.stop()
        except Exception:
            pass
        self.page = None
        self.context = None
        self.browser = None
        self.playwright = None
