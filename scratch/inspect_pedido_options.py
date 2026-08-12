import os
import sys
import time
from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        # 1. Login
        print("Logging in...")
        page.goto("https://logtudo.e-login.net/", wait_until="load")
        page.fill('[name="usuario"]', "Atualizarbi")
        page.fill('[name="senha"]', "Atualizar123BI")
        page.locator("#botaoSubmit").click()
        page.wait_for_timeout(3000)
        
        # 2. Go to Conhecimento form
        url_destino = "https://logtudo.e-login.net/versoes/versao5.0/rotinas/formulario.php?rotina=trans_conhecimento&OP=O1&_qsf=1"
        page.goto(url_destino, wait_until="load")
        page.wait_for_timeout(3000)
        
        # 3. Fill basic fields to load the form
        page.select_option('select[name="dados_agencias_id"]', value="2")
        page.select_option('select[name="dados_tiposTaloes_id"]', value="53")
        page.uncheck('input[name="dados_emitirReciboFrete[]"]')
        time.sleep(1)
        
        # 4. Search for Pedido 1849775
        print("Searching for Pedido '1849775'...")
        page.fill('input[name="pesquisa_pedidos_id"]', "1849775")
        page.click('i[name="botaoPesquisa_pedidos_id"]')
        time.sleep(2)
        
        # Print options
        select_locator = page.locator('select[name="dados_pedidos_id"]')
        options = select_locator.locator("option").all()
        print(f"Total options found: {len(options)}")
        for idx, opt in enumerate(options):
            print(f"  Option {idx}: value={opt.get_attribute('value')!r}, text={opt.inner_text().strip()!r}")
            
        # Take screenshot
        page.screenshot(path="scratch/pedido_options.png")
        print("Screenshot scratch/pedido_options.png saved.")
        
        browser.close()

if __name__ == "__main__":
    os.makedirs("scratch", exist_ok=True)
    run()
