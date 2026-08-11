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
        
        # 2. Go to Cotações
        print("Navigating to Cotações list page...")
        page.goto("https://logtudo.e-login.net/versoes/versao5.0/rotinas/c.php?id=transp_cotacoesFrete", wait_until="load")
        page.wait_for_timeout(2000)
        
        # Take a screenshot before doing anything
        page.screenshot(path="scratch/step1_page_loaded.png")
        print("Screenshot step1_page_loaded.png saved.")
        
        # 3. Check and open filter
        print("Checking filter state...")
        closed_filter = page.locator(".rg-busca-rapida.rg-busca-rapida-close")
        if closed_filter.is_visible():
            print("Filter is closed. Opening it...")
            cabecalho = page.locator(".rg-busca-rapida__cabecalho")
            if cabecalho.is_visible():
                cabecalho.click()
            else:
                page.locator(".fa.fa-chevron-up").click()
            page.wait_for_timeout(1000)
        else:
            print("Filter is already open.")
            
        page.screenshot(path="scratch/step2_filter_opened.png")
        print("Screenshot step2_filter_opened.png saved.")
        
        # 4. Fill quotation number
        print("Filling quotation number '1849775'...")
        page.fill('input[name="busca_nro"]', "1849775")
        page.wait_for_timeout(500)
        
        # 5. Click Filtrar
        print("Clicking Filtrar...")
        page.click('input[value="Filtrar"], button:has-text("Filtrar")')
        page.wait_for_timeout(5000) # wait 5s for AJAX reload
        
        # Take a screenshot after click
        page.screenshot(path="scratch/step3_after_filter.png")
        print("Screenshot step3_after_filter.png saved.")
        
        # Print table HTML
        print(f"Total tables: {page.locator('table').count()}")
        chk = page.locator("input[type='checkbox']")
        print(f"Total checkboxes of any type: {chk.count()}")
        for i in range(chk.count()):
            print(f"Checkbox {i}: name={chk.nth(i).get_attribute('name')}, id={chk.nth(i).get_attribute('id')}, value={chk.nth(i).get_attribute('value')}, class={chk.nth(i).get_attribute('class')}")
            
        checkbox_selector = 'input[type="checkbox"][name="id"]'
        checkboxes = page.locator(checkbox_selector)
        count = checkboxes.count()
        print(f"Number of checkboxes found: {count}")
        
        if count > 0:
            print(f"Checkbox value: {checkboxes.first.get_attribute('value')}")
        else:
            # Let's find table rows or any text on the page
            print("No checkbox found. Printing body text preview...")
            body_text = page.inner_text("body")
            lines = [l.strip() for l in body_text.split("\n") if l.strip()]
            for l in lines[:30]:
                print("  ", l)
                
        browser.close()

if __name__ == "__main__":
    os.makedirs("scratch", exist_ok=True)
    run()
