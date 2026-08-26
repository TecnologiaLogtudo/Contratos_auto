import time
from typing import Callable
from playwright.sync_api import Page
from .lactalis import LactalisBaseCompany

class DPACompany(LactalisBaseCompany):
    def match(self, remetente: str) -> bool:
        rem = remetente.lower()
        return "dpa" in rem or "dairy partners" in rem or "05.300.331" in rem or "05300331" in rem

    def match_cotacao_opcao(self, option_text: str, nro_cotacao: str) -> bool:
        return (
            option_text.strip().startswith(f"{nro_cotacao} /") 
            and ("dpa" in option_text.lower() or "dairy partners" in option_text.lower())
        )

    def format_cotacao_erro_msg(self, target_option_prefix: str) -> str:
        return f"'{target_option_prefix}' contendo 'DPA'"

    def sincronizar_remetente_destinatario(
        self, page: Page, nro_cotacao: str, log_callback: Callable, atraso_etapas: float
    ) -> bool:
        try:
            log_callback(f"[F4] [Item {nro_cotacao}] Aplicando regra de destinatário DPA...", "DEBUG")
            
            # 1. Remetente: Pesquisar '05.300.331/0014-85'
            page.fill('input[name="pesquisa_enderecoRemetente_id"]', '05.300.331/0014-85')
            time.sleep(atraso_etapas)
            page.click('i[name="botaoPesquisa_enderecoRemetente_id"]')
            
            remetente_selector = 'select[name="dados_enderecoRemetente_id"]'
            page.wait_for_selector(f'{remetente_selector} option[value]:not([value=""])', state='attached', timeout=10000)
            time.sleep(atraso_etapas)
            
            # Selecionar o segundo elemento da lista
            options_remetente = page.locator(remetente_selector).locator("option").all()
            remetentes_encontrados = []
            for opt in options_remetente:
                text = opt.inner_text().strip()
                if "05.300.331/0014-85" in text or "DAIRY PARTNERS" in text.upper():
                    remetentes_encontrados.append(opt)
                    
            remetente_value = None
            if len(remetentes_encontrados) >= 2:
                remetente_value = remetentes_encontrados[1].get_attribute("value")
                log_callback(f"[F4] [Item {nro_cotacao}] Selecionando o segundo remetente DPA da lista: '{remetentes_encontrados[1].inner_text().strip()}'", "DEBUG")
            elif len(remetentes_encontrados) == 1:
                remetente_value = remetentes_encontrados[0].get_attribute("value")
                log_callback(f"[F4] [Item {nro_cotacao}] AVISO: Apenas um remetente DPA encontrado. Selecionando o primeiro: '{remetentes_encontrados[0].inner_text().strip()}'", "AVISO")
                
            if remetente_value:
                page.select_option(remetente_selector, value=remetente_value)
                log_callback(f"[F4] [Item {nro_cotacao}] Remetente DPA selecionado com sucesso.", "INFO")
            else:
                log_callback(f"[F4] [Item {nro_cotacao}] ERRO: Remetente DPA não encontrado nas opções.", "ERRO")
                return False
                
            time.sleep(atraso_etapas)

            # 2. Destinatário: Pesquisar '20511709000169'
            page.fill('input[name="pesquisa_enderecoDestinatario_id"]', '20511709000169')
            time.sleep(atraso_etapas)
            page.click('i[name="botaoPesquisa_enderecoDestinatario_id"]')
            
            destinatario_selector = 'select[name="dados_enderecoDestinatario_id"]'
            page.wait_for_selector(f'{destinatario_selector} option[value]:not([value=""])', state='attached', timeout=10000)
            time.sleep(atraso_etapas)
            
            options_destinatario = page.locator(destinatario_selector).locator("option").all()
            destinatario_value = None
            for opt in options_destinatario:
                text = opt.inner_text().strip()
                val = opt.get_attribute("value")
                if val and val != "":
                    destinatario_value = val
                    log_callback(f"[F4] [Item {nro_cotacao}] Selecionando primeiro destinatário DPA com valor: '{text}'", "DEBUG")
                    break
                    
            if destinatario_value:
                page.select_option(destinatario_selector, value=destinatario_value)
                log_callback(f"[F4] [Item {nro_cotacao}] Destinatário DPA selecionado com sucesso.", "INFO")
            else:
                log_callback(f"[F4] [Item {nro_cotacao}] ERRO: Destinatário DPA não encontrado nas opções.", "ERRO")
                return False

            return True
        except Exception as e:
            log_callback(f"[F4] [Item {nro_cotacao}] ERRO na Etapa 1 (Remetente/Destinatário DPA): {e}", "ERRO")
            return False

    def get_termo_busca_perfil(self, cidade_planilha: str) -> str:
        return "dpa BA"
