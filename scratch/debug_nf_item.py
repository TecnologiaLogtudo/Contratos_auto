"""Script de debug para executar apenas o primeiro item do relatorio (12).xls ate a Fase 4."""

import os
import sys
import time
from pathlib import Path

# Adiciona o diretorio raiz ao PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.engine.excel_processor import ExcelProcessor
from backend.app.engine.contract_runner import ContractRunner
from backend.app.engine.strategies.strategy_factory import get_strategy
from backend.app.engine.pages.login_page import LoginPage
from backend.app.engine.pages.cotacoes_page import CotacoesPage
from backend.app.engine.pages.conhecimento_page import ConhecimentoPage
from backend.app.engine.pages.frete_page import FretePage
from backend.app.engine.browser_factory import BrowserFactory, BrowserConfig

def run_debug():
    filepath = r"C:\Users\felipe\Downloads\relatorio (12).xls"
    processor = ExcelProcessor(filepath, log_callback=lambda m, l: print(f"[{l}] {m}", flush=True))
    items = processor.load_and_parse()

    if not items:
        print("Nenhum item encontrado no arquivo Excel.")
        return

    item = items[0]
    print(f"\n--- ITEM PARA DEBUG ---", flush=True)
    print(f"Linha: {item.row_index} | Cotação: {item.nro_cotacao} | Remetente: {item.remetente} | Cidade: {item.cidade}/{item.uf}", flush=True)
    print(f"Extracted Obs Interna: '{item.extracted_obs_interna}'", flush=True)
    print(f"Extracted Pedido: '{item.extracted_nro_pedido}'", flush=True)
    print(f"Extracted NF inicial: '{item.extracted_nf}'", flush=True)

    # Configura modo headless para execução sem dependência de janela GUI
    config = BrowserConfig(headless=True)
    playwright, browser, context, page = BrowserFactory.create_browser(config=config, log_callback=print)

    try:
        login_page = LoginPage(page, log_callback=print)
        login_page.login("Atualizarbi", "Atualizar123", CotacoesPage.COTACOES_URL)

        cotacoes_page = CotacoesPage(page, log_callback=print)
        conhecimento_page = ConhecimentoPage(page, log_callback=print)
        frete_page = FretePage(page, log_callback=print)

        strategy = get_strategy(item.remetente)
        print(f"Estratégia selecionada: {strategy.__class__.__name__}")

        # Fase 2: Extração de Metadados (apenas se a NF ainda não veio da planilha)
        if not item.extracted_nf:
            print("\n--- INICIANDO FASE 2 (Extração Metadados) ---", flush=True)
            cotacoes_page.extrair_metadados_cotacao(item, delay_step=0.2)
        else:
            print("\n--- PULANDO FASE 2: NF e Pedido já extraídos da planilha ---", flush=True)
            page.goto("https://logtudo.e-login.net/versoes/versao5.0/rotinas/formulario.php?rotina=trans_conhecimento&OP=O1&_qsf=1", wait_until="domcontentloaded")

        print(f"Extracted Pedido: '{item.extracted_nro_pedido}'", flush=True)
        print(f"Extracted NF: '{item.extracted_nf}'", flush=True)

        # Fase 3: Conhecimento
        print("\n--- INICIANDO FASE 3 (Conhecimento) ---", flush=True)
        conhecimento_page.preencher_fase3(item, strategy, delay_step=0.2)
        print(f"Fase 3 concluída com sucesso! URL atual: {page.url}", flush=True)

        page.screenshot(path="scratch/fase3_concluida.png")
        print("Screenshot salva em scratch/fase3_concluida.png")

        # Fase 4: Frete
        print("\n--- INICIANDO FASE 4 (Frete) ---")
        frete_page.preencher_fase4(item, strategy, delay_step=0.2)
        print(f"Fase 4 concluída! URL atual: {page.url}")

        page.screenshot(path="scratch/fase4_concluida.png")
        print("Screenshot salva em scratch/fase4_concluida.png")

    except Exception as e:
        print(f"\n[ERRO DEBUG] {e}")
        import traceback
        traceback.print_exc()
        try:
            page.screenshot(path="scratch/erro_debug.png")
            print("Screenshot de erro salva em scratch/erro_debug.png")
        except Exception:
            pass
    finally:
        browser.close()
        playwright.stop()

if __name__ == "__main__":
    run_debug()
