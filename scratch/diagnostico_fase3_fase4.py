"""Script de diagnóstico ajustado para testar os seletores visíveis de NF na Fase 3 e verificar o comportamento na Fase 4."""

from __future__ import annotations

import os
import sys
import time
import traceback
from pathlib import Path

# Adiciona a raiz ao PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from backend.app.engine.excel_processor import ExcelProcessor
from backend.app.engine.strategies.strategy_factory import get_strategy
from backend.app.engine.pages.login_page import LoginPage
from backend.app.engine.browser_factory import BrowserFactory, BrowserConfig
from backend.app.engine.dialog_guard import DialogGuard

def run_diagnostico():
    excel_path = r"C:\Users\felipe\Downloads\relatorio (12).xls"
    print(f"[*] Carregando planilha: {excel_path}")
    processor = ExcelProcessor(excel_path, log_callback=lambda m, l="INFO": print(f"[{l}] {m}"))
    items = processor.load_and_parse()
    
    if not items:
        print("[!] Nenhum item encontrado na planilha.")
        return
        
    item = items[0]
    print(f"\n=======================================================")
    print(f"[*] ITEM SELECIONADO PARA DIAGNÓSTICO:")
    print(f"    - Cotação: {item.nro_cotacao}")
    print(f"    - Remetente: {item.remetente}")
    print(f"    - Pedido extraído: {item.extracted_nro_pedido}")
    print(f"    - NF extraída: {item.extracted_nf}")
    print(f"    - Observação: {item.extracted_obs_interna}")
    print(f"=======================================================\n")
    
    strategy = get_strategy(item.remetente)
    print(f"[*] Estratégia identificada: {strategy.__class__.__name__}")
    
    config = BrowserConfig(headless=True)
    playwright, browser, context, page = BrowserFactory.create_browser(config=config, log_callback=print)
    
    try:
        login_page = LoginPage(page, log_callback=print)
        login_url = "https://logtudo.e-login.net/versoes/versao5.0/rotinas/formulario.php?rotina=trans_conhecimento&OP=O1&_qsf=1"
        print("[*] Efetuando Login no ERP...")
        login_page.login("Atualizarbi", "Atualizar123", login_url)
        print("[+] Login com sucesso!")
        
        # --- FASE 3: INVESTIGAÇÃO DETALHADA ---
        print("\n--- [DIAGNÓSTICO FASE 3] Analisando DOM e Campos de Conhecimento / NF ---")
        DialogGuard.dismiss_all_popups(page, print, f"Item {item.nro_cotacao}")
        
        # 1. Agência e Talão
        page.locator('select[name="dados_agencias_id"]').wait_for(state="visible", timeout=10000)
        page.locator('select[name="dados_agencias_id"]').select_option(value="2")
        page.locator('select[name="dados_tiposTaloes_id"]').select_option(value="53")
        time.sleep(0.5)
        
        # 2. Recibo de Frete
        chk_recibo = page.locator('input[name="dados_emitirReciboFrete[]"]').first
        if strategy.deve_emitir_recibo_frete():
            chk_recibo.check()
        else:
            chk_recibo.uncheck()
            
        # 3. Pesquisa e Seleção de Pedido / Cotação
        # Testa primeiro pelo pedido extraído; se der nenhum registro, tenta pela cotação
        search_target = item.extracted_nro_pedido or item.nro_cotacao
        print(f"[*] Preenchendo pesquisa de pedido com: {search_target}")
        page.locator('input[name="pesquisa_pedidos_id"]').fill(str(search_target))
        time.sleep(0.3)
        page.locator('i[name="botaoPesquisa_pedidos_id"]').click()
        time.sleep(1.5)
        
        select_loc = page.locator('select[name="dados_pedidos_id"]')
        select_loc.wait_for(state="attached", timeout=8000)
        options = select_loc.locator("option").all()
        opts_text = [opt.inner_text().strip() for opt in options]
        print(f"[*] Opções encontradas com search_target '{search_target}': {opts_text}")
        
        if any("Nenhum registro" in t for t in opts_text) and search_target != item.nro_cotacao:
            print(f"[*] Tentando fallback de pesquisa com o número da Cotação: {item.nro_cotacao}")
            search_target = item.nro_cotacao
            page.locator('input[name="pesquisa_pedidos_id"]').fill(str(search_target))
            time.sleep(0.3)
            page.locator('i[name="botaoPesquisa_pedidos_id"]').click()
            time.sleep(1.5)
            options = select_loc.locator("option").all()
            opts_text = [opt.inner_text().strip() for opt in options]
            print(f"[*] Opções encontradas com cotação '{search_target}': {opts_text}")
            
        target_val = None
        for opt in options:
            txt = opt.inner_text().strip()
            val = opt.get_attribute("value")
            if val and (str(search_target) in txt or txt.startswith(f"{search_target} /")):
                target_val = val
                break
        if not target_val and len(options) > 1:
            for opt in options:
                v = opt.get_attribute("value")
                if v:
                    target_val = v
                    break
                    
        if target_val:
            select_loc.select_option(value=target_val)
            print(f"[+] Pedido selecionado com sucesso (value={target_val})")
        else:
            print(f"[!] Não foi possível encontrar opção de pedido para '{search_target}'")
            
        time.sleep(1.0)
        
        # 4. PREENCHIMENTO DA NOTA FISCAL (usando seletores visíveis corretos)
        if item.extracted_nf:
            print(f"\n[*] Tentando preencher e vincular NF '{item.extracted_nf}' com seletor :visible:")
            
            # Seletor estrito para o input visível
            input_nf_vis = page.locator('input[name="pesquisa_dados_notas_carregamento_id"]:visible, #pswobj3:visible').first
            print(f"    - input_nf_vis count: {input_nf_vis.count()}")
            
            if input_nf_vis.count() > 0:
                input_nf_vis.fill(str(item.extracted_nf))
                time.sleep(0.3)
                
                # Botão de pesquisa associado ao input visível
                btn_nf = page.locator('.swrepp:visible i.fa-solid, i[name="botaoPesquisa_dados_notas_carregamento_id"]:visible, #pswobj3 + em i').first
                print(f"    - btn_nf count: {btn_nf.count()}")
                if btn_nf.count() > 0:
                    btn_nf.click()
                    print("    - Clicado no botão de pesquisa de NF. Aguardando AJAX...")
                    time.sleep(2.5)
                    
                # Select visível de NF
                select_nf_vis = page.locator('select[name*="dados_notas_carregamento_id"]:visible, #cswobj3:visible').first
                print(f"    - select_nf_vis count: {select_nf_vis.count()}")
                if select_nf_vis.count() > 0:
                    options_nf = select_nf_vis.locator("option").all()
                    print(f"    - Opções no select de NF: {[o.inner_text().strip() for o in options_nf]}")
                    
                    target_nf_val = None
                    for opt in options_nf:
                        val = opt.get_attribute("value")
                        txt = opt.inner_text().strip()
                        if val and (str(item.extracted_nf) in txt or val != ""):
                            target_nf_val = val
                            if str(item.extracted_nf) in txt:
                                break
                                
                    if target_nf_val:
                        select_nf_vis.select_option(value=target_nf_val)
                        print(f"[+] NF {item.extracted_nf} vinculada com sucesso no select! (value={target_nf_val})")
                        time.sleep(1.0)
                    else:
                        print(f"[!] Nenhuma opção válida encontrada no select para a NF {item.extracted_nf}")
                        
        # Salva screenshot da Fase 3 preenchida
        Path("scratch").mkdir(exist_ok=True)
        page.screenshot(path="scratch/diag_fase3_preenchida_ok.png", full_page=True)
        print("[+] Screenshot salva: scratch/diag_fase3_preenchida_ok.png")
        
        # 5. Preenche complemento do pedido
        comp_val = strategy.get_complemento_pedido(item)
        if comp_val:
            try:
                page.locator('input[name="dados_complementoPedido"]').fill(str(comp_val))
                time.sleep(0.3)
            except Exception:
                pass
                
        # 6. Avança para a Fase 4
        print("\n[*] Clicando em Avançar para a Fase 4...")
        page.locator('#botao_avancar, button:has-text("Avançar")').first.click()
        
        # Aguarda transição para a Fase 4 e trata eventuais popups/sweetalerts
        timeout_limit = time.time() + 30
        while time.time() < timeout_limit:
            DialogGuard.dismiss_all_popups(page, print, f"Item {item.nro_cotacao}")
            try:
                if page.locator('select[name="dados_enderecoDestinatario_id"]').is_visible(timeout=500):
                    break
            except Exception:
                pass
            time.sleep(0.3)
            
        print("\n--- [DIAGNÓSTICO FASE 4] Analisando Estado de Remetente e Destinatário ---")
        time.sleep(1.5)
        page.screenshot(path="scratch/diag_fase4_estado.png", full_page=True)
        print("[+] Screenshot salva: scratch/diag_fase4_estado.png")
        
        # Remetente
        rem_sel = page.locator('select[name="dados_enderecoRemetente_id"]')
        if rem_sel.count() > 0:
            rem_val = rem_sel.input_value()
            rem_opts = [o.inner_text().strip() for o in rem_sel.locator("option").all() if o.get_attribute("value") == rem_val]
            print(f"[*] Remetente selecionado na Fase 4: value='{rem_val}', texto='{rem_opts}'")
            
        # Destinatário
        dest_sel = page.locator('select[name="dados_enderecoDestinatario_id"]')
        if dest_sel.count() > 0:
            dest_val = dest_sel.input_value()
            dest_all_opts = [o.inner_text().strip() for o in dest_sel.locator("option").all()]
            dest_sel_text = [o.inner_text().strip() for o in dest_sel.locator("option").all() if o.get_attribute("value") == dest_val]
            print(f"[*] Destinatário selecionado na Fase 4: value='{dest_val}', texto='{dest_sel_text}'")
            print(f"[*] Todas as opções disponíveis no select de Destinatário: {dest_all_opts}")
            
        print("\n=================== DIAGNÓSTICO CONCLUÍDO COM SUCESSO ===================")
        
    except Exception as e:
        print(f"\n[ERRO DURANTE DIAGNÓSTICO]: {e}")
        traceback.print_exc()
        try:
            page.screenshot(path="scratch/diag_erro.png", full_page=True)
            print("[+] Screenshot de erro salva: scratch/diag_erro.png")
        except Exception:
            pass
    finally:
        browser.close()
        playwright.stop()

if __name__ == "__main__":
    run_diagnostico()
