import re
import time
from typing import Callable
from playwright.sync_api import Page
from .base_company import BaseCompany

class LatamCompany(BaseCompany):
    def match(self, remetente: str) -> bool:
        rem = remetente.lower()
        return "latam" in rem or "tam" in rem or "02.012.862" in rem or "02012862" in rem

    def sincronizar_remetente_destinatario(
        self, page: Page, nro_cotacao: str, log_callback: Callable, atraso_etapas: float
    ) -> bool:
        """
        Regra atual da LATAM: Destinatário é cópia do Remetente (Busca pelo CNPJ e seleciona ID exato)
        """
        destinatario_selector = 'select[name="dados_enderecoDestinatario_id"]'
        remetente_selector = 'select[name="dados_enderecoRemetente_id"]'

        try:
            # 1. Espera o campo Remetente estar anexado/disponível
            page.wait_for_selector(remetente_selector, state='attached', timeout=5000)
            remetente_value = page.input_value(remetente_selector)

            if not remetente_value:
                log_callback(f"[F4] [Item {nro_cotacao}] ERRO: Remetente está vazio. Não é possível pesquisar o Destinatário.", "ERRO")
                return False

            # Tenta obter o texto do remetente para extrair o CNPJ
            remetente_text = "N/A"
            try:
                remetente_text = page.locator(f'{remetente_selector} option[value="{remetente_value}"]').inner_text().strip()
            except Exception:
                try:
                    remetente_text = page.evaluate('() => { const select = document.querySelector(\'select[name="dados_enderecoRemetente_id"]\'); return select ? select.options[select.selectedIndex].text : ""; }').strip()
                except Exception:
                    remetente_text = f"Valor {remetente_value}"

            # Extrai o CNPJ desconsiderando sinais
            # Padrão busca formato CNPJ ou sequência de 14 dígitos
            cnpj_match = re.search(r'(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})|(\d{14})', remetente_text)
            if cnpj_match:
                cnpj = re.sub(r'\D', '', cnpj_match.group(0))
            else:
                # Caso não encontre no padrão, tenta extrair todos os dígitos e pegar os primeiros 14
                digits = re.sub(r'\D', '', remetente_text)
                if len(digits) >= 14:
                    cnpj = digits[:14]
                else:
                    log_callback(f"[F4] [Item {nro_cotacao}] ERRO: Não foi possível obter o CNPJ do Remetente ('{remetente_text}').", "ERRO")
                    return False

            log_callback(f"[F4] [Item {nro_cotacao}] Etapa 1: Pesquisando Destinatário pelo CNPJ '{cnpj}' do Remetente...", "DEBUG")

            # Preenche o CNPJ no campo de pesquisa do Destinatário
            page.fill('input[name="pesquisa_enderecoDestinatario_id"]', cnpj)
            time.sleep(atraso_etapas)

            # Clica em Pesquisar
            page.click('i[name="botaoPesquisa_enderecoDestinatario_id"]')

            # Espera as opções do select carregarem
            page.wait_for_selector(f'{destinatario_selector} option[value]:not([value=""])', state='attached', timeout=10000)
            time.sleep(atraso_etapas)

            # 2. Siga o fluxo normalmente: comparar com o valor de Remetente e selecionar
            destinatario_value = page.input_value(destinatario_selector)

            if destinatario_value != remetente_value:
                log_callback(f"[F4] [Item {nro_cotacao}] AVISO: Destinatário diferente do Remetente. Tentando selecionar o valor exato do Remetente ('{remetente_text}')...", "AVISO")
                try:
                    # Seleciona a opção com valor idêntico ao remetente
                    page.select_option(destinatario_selector, value=remetente_value)
                    time.sleep(atraso_etapas)

                    # Verifica se a seleção funcionou
                    if page.input_value(destinatario_selector) == remetente_value:
                        log_callback(f"[F4] [Item {nro_cotacao}] Destinatário sincronizado com o Remetente com sucesso.", "INFO")
                    else:
                        log_callback(f"[F4] [Item {nro_cotacao}] ERRO: Não foi possível selecionar o valor do Remetente no campo Destinatário (opção não disponível).", "ERRO")
                        return False
                except Exception as e_sel:
                    log_callback(f"[F4] [Item {nro_cotacao}] ERRO ao tentar sincronizar Destinatário: {e_sel}", "ERRO")
                    return False
            else:
                log_callback(f"[F4] [Item {nro_cotacao}] Destinatário e Remetente estão sincronizados.", "INFO")

        except Exception as e:
            log_callback(f"[F4] [Item {nro_cotacao}] ERRO na Etapa 1 (Destinatário/Remetente LATAM): {e}", "ERRO")
            return False
            
        return True

    def get_termo_busca_perfil(self, cidade_planilha: str) -> str:
        cidade_lower = cidade_planilha.lower()
        if "vitória da conquista" in cidade_lower or "vitoria da conquista" in cidade_lower:
            return "vitoria"
        return cidade_planilha
