from __future__ import annotations

import time
from typing import Callable, Optional
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from ...domain.models import ItemContrato
from ...domain.errors import QuoteExtractionError, NavigationError
from ..dialog_guard import DialogGuard
from ..strategies.lactalis_strategy import extrair_numero_nf


class CotacoesPage:
    """Page Object para a rotina de Cotações de Frete (transp_cotacoesFrete)."""

    COTACOES_URL = "https://logtudo.e-login.net/versoes/versao5.0/rotinas/c.php?id=transp_cotacoesFrete"
    CONHECIMENTOS_URL = "https://logtudo.e-login.net/versoes/versao5.0/rotinas/c.php?id=trans_conhecimento"

    def __init__(self, page: Page, log_callback: Optional[Callable[[str, str], None]] = None):
        self.page = page
        self.log = log_callback or (lambda m, l="INFO": None)

    def extrair_metadados_cotacao(self, item: ItemContrato, delay_step: float = 0.05) -> None:
        """
        Acessa a listagem de cotações, filtra pela cotação/Ravex, abre detalhes e
        extrai o Nº do Pedido Real, Observação Interna e o número da NF.
        Em seguida, navega e abre o formulário de Conhecimento Manual.
        """
        nro = item.nro_cotacao
        self.log(f"[Prep] [Item {nro}] Consultando cotação de frete para extração de metadados...", "DEBUG")

        # 1. Navega para a tela de Cotações
        try:
            self.page.goto(self.COTACOES_URL, wait_until="load", timeout=45000)
        except Exception as e:
            raise NavigationError(f"Falha ao abrir tela de cotações: {e}", url=self.COTACOES_URL, step=f"Cotação {nro}")

        DialogGuard.dismiss_all_popups(self.page, self.log, f"Cotação {nro}")
        time.sleep(delay_step)

        # 2. Garante que o painel de filtros está expandido
        try:
            if self.page.locator(".rg-busca-rapida.rg-busca-rapida-close").is_visible(timeout=1500):
                self.log(f"[Prep] [Item {nro}] Expandindo painel de filtros...", "DEBUG")
                cabecalho = self.page.locator(".rg-busca-rapida__cabecalho, .fa.fa-chevron-up")
                if cabecalho.count() > 0:
                    cabecalho.first.click()
                time.sleep(delay_step)
        except Exception:
            pass

        # 3. Filtra pelo número da cotação
        try:
            self.page.locator('input[name="busca_nro"]').fill(str(nro))
            time.sleep(delay_step)
            self.page.locator('input[value="Filtrar"], button:has-text("Filtrar")').first.click()
            time.sleep(delay_step)
        except Exception as e:
            raise QuoteExtractionError(f"Falha ao submeter filtro de cotação: {e}", quote_number=nro)

        DialogGuard.dismiss_all_popups(self.page, self.log, f"Cotação {nro}")

        # 4. Verifica status de bloqueio da cotação
        err_loc = self.page.locator('div.error p:has-text("Status da cotação não permite editar a mesma")')
        if err_loc.count() > 0 and err_loc.first.is_visible():
            raise QuoteExtractionError("Status da cotação no sistema não permite edição.", quote_number=nro)

        # 5. Obtém o ID interno da cotação no resultado da busca
        checkbox_loc = self.page.locator('input[type="checkbox"][name="id"]')
        try:
            checkbox_loc.first.wait_for(state="attached", timeout=8000)
        except PlaywrightTimeoutError:
            raise QuoteExtractionError("Cotação não encontrada na listagem do sistema.", quote_number=nro)

        id_val = checkbox_loc.first.get_attribute("value")
        if not id_val:
            raise QuoteExtractionError("ID interno da cotação não localizado no grid.", quote_number=nro)

        self.log(f"[Prep] [Item {nro}] Cotação identificada (ID interno: {id_val}). Acessando detalhes...", "DEBUG")

        # 6. Acessa o formulário de detalhes da cotação
        detail_url = f"https://logtudo.e-login.net/versoes/versao5.0/rotinas/formulario.php?pop=&detail=&rotina=transp_cotacoesFrete&chave=&OP=O3&id={id_val}"
        try:
            self.page.goto(detail_url, wait_until="load", timeout=45000)
            time.sleep(delay_step)
        except Exception as e:
            raise NavigationError(f"Falha ao carregar detalhes da cotação: {e}", url=detail_url, step=f"Cotação {nro}")

        DialogGuard.dismiss_all_popups(self.page, self.log, f"Cotação {nro}")

        # 7. Extrai Nº Pedido Cliente
        try:
            pedido_input = self.page.locator('input[name="dados_nroPedidoCliente"]')
            pedido_input.wait_for(state="visible", timeout=15000)
            nro_pedido = pedido_input.input_value().strip()
        except Exception as e:
            raise QuoteExtractionError(f"Campo 'Nº Pedido Cliente' indisponível nos detalhes: {e}", quote_number=nro)

        if not nro_pedido:
            raise QuoteExtractionError("Nº Pedido Cliente está vazio nos detalhes da cotação.", quote_number=nro)

        item.extracted_nro_pedido = nro_pedido
        self.log(f"[Prep] [Item {nro}] Pedido Cliente extraído: '{nro_pedido}'", "DEBUG")

        # 8. Extrai Observação Interna
        obs_interna = ""
        for sel in [
            'textarea[name="dados_observacaoInterna"]',
            'textarea[name="dados_obsInterna"]',
            'textarea[name="dados_observacoesInternas"]',
        ]:
            try:
                ta = self.page.locator(sel)
                if ta.count() > 0 and ta.first.is_visible():
                    obs_interna = ta.first.input_value().strip()
                    if obs_interna:
                        break
            except Exception:
                continue

        if not obs_interna:
            # Fallback de busca em qualquer textarea contendo padrão de nota fiscal
            for ta in self.page.locator('textarea').all():
                val = ta.input_value()
                if "nf" in val.lower():
                    obs_interna = val.strip()
                    break

        if not obs_interna:
            raise QuoteExtractionError("Observação Interna vazia ou não encontrada na cotação.", quote_number=nro)

        item.extracted_obs_interna = obs_interna
        self.log(f"[Prep] [Item {nro}] Observação Interna extraída com sucesso.", "DEBUG")

        # 9. Extrai o número da NF
        nf = extrair_numero_nf(obs_interna)
        if not nf:
            raise QuoteExtractionError(f"Número de NF não identificado na observação: '{obs_interna}'", quote_number=nro)

        item.extracted_nf = nf
        self.log(f"[Prep] [Item {nro}] NF extraída: '{nf}'", "DEBUG")

        # 10. Navega para a rotina de Conhecimentos
        self.log(f"[Prep] [Item {nro}] Abrindo novo Conhecimento...", "DEBUG")
        try:
            self.page.goto(self.CONHECIMENTOS_URL, wait_until="load", timeout=30000)
            time.sleep(delay_step)
        except Exception as e:
            raise NavigationError(f"Falha ao navegar para Conhecimentos: {e}", url=self.CONHECIMENTOS_URL, step=f"Cotação {nro}")

        DialogGuard.dismiss_all_popups(self.page, self.log, f"Cotação {nro}")

        # 11. Clica no botão de Adicionar Conhecimento.
        # Paridade com o modelo antigo (lactalis.py): wait_for_selector no ID estável
        # antes do clique, fallback por texto/ícone. O locator CSS combinado com .first
        # pode resolver para um elemento não-clicável e dar timeout mesmo com a página correta.
        try:
            self.page.wait_for_selector('[id="_boop"] > a', timeout=10000)
            try:
                self.page.locator('[id="_boop"] > a').first.click(timeout=8000)
            except Exception:
                # O clique pode navegar/desanexar o elemento no meio do click()
                # (timeout espúrio) mesmo quando a ação teve efeito — não falhar aqui.
                self.log(f"[Prep] [Item {nro}] Timeout espúrio no clique de Adicionar Conhecimento; validando navegação...", "DEBUG")
        except Exception as e_add:
            self.log(f"[Prep] [Item {nro}] Clique por ID em Adicionar Conhecimento falhou ({e_add}). Tentando por ícone/texto...", "DEBUG")
            try:
                self.page.locator('a:has-text("Adicionar"), .fa-plus').first.click(timeout=8000)
            except Exception:
                self.log(f"[Prep] [Item {nro}] Fallback também falhou; validando se o formulário já abriu...", "DEBUG")
        time.sleep(max(delay_step, 1.0))

        # Validação por efeito: o clique é bem-sucedido se o formulário de Inclusão
        # (ou a escolha de Preenchimento Manual) estiver presente.
        form_aberto = self.page.locator('text=Conhecimentos de Transporte - Inclusão').first
        manual_disponivel = self.page.get_by_text("Preenchimento Manual", exact=False).first
        try:
            form_ou_manual = form_aberto.or_(manual_disponivel).first
            form_ou_manual.wait_for(state="visible", timeout=10000)
        except Exception as e:
            raise QuoteExtractionError(f"Falha ao clicar em 'Adicionar Conhecimento': formulário de Inclusão não abriu após o clique ({e})", quote_number=nro)

        # 12. Seleciona 'Preenchimento Manual' de forma semântica e não ordinal
        DialogGuard.dismiss_all_popups(self.page, self.log, f"Cotação {nro}")
        btn_manual = self.page.get_by_text("Preenchimento Manual", exact=False).first
        try:
            btn_manual.click(timeout=8000)
            time.sleep(delay_step)
        except Exception as e:
            raise QuoteExtractionError(f"Falha ao selecionar 'Preenchimento Manual': {e}", quote_number=nro)

        self.log(f"[Prep] [Item {nro}] Preparação e transição para o Conhecimento concluídas.", "DEBUG")
