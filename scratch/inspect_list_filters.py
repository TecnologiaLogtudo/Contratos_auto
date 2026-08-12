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
        
        # 2. Go to Conhecimentos list
        url_destino = "https://logtudo.e-login.net/versoes/versao5.0/rotinas/c.php?id=trans_conhecimento"
        print(f"Navigating to: {url_destino}")
        page.goto(url_destino, wait_until="load")
        page.wait_for_timeout(3000)
        
        # Take screenshot of the list page
        page.screenshot(path="scratch/list_filters.png")
        print("Screenshot scratch/list_filters.png saved.")
        
        # Dump all inputs on the list page
        print("\nDumping inputs on list page:")
        inputs = page.locator("input").all()
        for inp in inputs:
            name = inp.get_attribute("name")
            id_attr = inp.get_attribute("id")
            val = inp.get_attribute("value")
            placeholder = inp.get_attribute("placeholder")
            outer_html = inp.evaluate("el => el.outerHTML")
            parent_text = inp.evaluate("el => el.parentElement ? el.parentElement.innerText.trim() : ''")
            print(f"Input: name={name}, id={id_attr}, value={val}, placeholder={placeholder}, parentText={parent_text!r}, html={outer_html}")
            
        browser.close()

if __name__ == "__main__":
    os.makedirs("scratch", exist_ok=True)
    run()
