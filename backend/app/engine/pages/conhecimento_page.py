from __future__ import annotations

import time
from typing import Callable, Optional
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from ...domain.models import ItemContrato
from ...domain.errors import FormFillError, NavigationError
from ..dialog_guard import DialogGuard
from ..strategies.base_strategy import BaseStrategy


class ConhecimentoPage:
    """Page Object para a Fase 3 - Preenchimento Básico do Conhecimento."""

    def __init__(self, page: Page, log_callback: Optional[Callable[[str, str], None]] = None):
        self.page = page
        self.log = log_callback or (lambda m, l="INFO": None)

    def preencher_fase3(
        self,
        item: ItemContrato,
        strategy: BaseStrategy,
        delay_step: float = 0.05,
    ) -> None:
        nro = item.nro_cotacao
        self.log(f"[F3] [Item {nro}] --- INÍCIO: PREENCHIMENTO BÁSICO DO CONHECIMENTO ---", "FASE")

        DialogGuard.dismiss_all_popups(self.page, self.log, f"Item {nro}")

        # 1. Seleciona Agência (LOGTUDO MATRIZ - BAHIA -> value "2")
        self.log(f"[F3] [Item {nro}] Etapa 1: Selecionando Agência...", "DEBUG")
        try:
            agencia_sel = self.page.locator('select[name="dados_agencias_id"]')
            agencia_sel.wait_for(state="visible", timeout=10000)
            agencia_sel.select_option(value="2")
            time.sleep(delay_step)
        except Exception as e:
            raise FormFillError(f"Falha ao selecionar Agência: {e}", field_name="dados_agencias_id", step="Fase 3")

        # 2. Seleciona Talão (Encarte Bahia -> value "53")
        self.log(f"[F3] [Item {nro}] Etapa 2: Selecionando Talão...", "DEBUG")
        try:
            talao_sel = self.page.locator('select[name="dados_tiposTaloes_id"]')
            talao_sel.select_option(value="53")
            time.sleep(delay_step)
        except Exception as e:
            raise FormFillError(f"Falha ao selecionar Talão: {e}", field_name="dados_tiposTaloes_id", step="Fase 3")

        # 3. Checkbox 'Emitir Recibo de Frete'
        # .first: a página pode ter múltiplos inputs com o mesmo name (strict mode violation)
        chk_recibo = self.page.locator('input[name="dados_emitirReciboFrete[]"]').first
        try:
            if strategy.deve_emitir_recibo_frete():
                self.log(f"[F3] [Item {nro}] Etapa 3: Marcando 'Emitir Recibo'...", "DEBUG")
                chk_recibo.check()
            else:
                self.log(f"[F3] [Item {nro}] Etapa 3: Desmarcando 'Emitir Recibo'...", "DEBUG")
                chk_recibo.uncheck()
            time.sleep(delay_step)
        except Exception as e:
            self.log(f"[F3] [Item {nro}] Aviso ao configurar checkbox Emitir Recibo: {e}", "AVISO")

        # 4. Pesquisa e Seleciona Cotação / Pedido
        self.log(f"[F3] [Item {nro}] Etapa 4: Pesquisando e vinculando cotação/pedido...", "DEBUG")
        self._vincular_cotacao(item, strategy, delay_step)

        # 5. Preenche Complemento do Pedido
        comp_val = strategy.get_complemento_pedido(item)
        if comp_val:
            self.log(f"[F3] [Item {nro}] Etapa 5: Preenchendo Complemento com '{comp_val}'...", "DEBUG")
            try:
                self.page.locator('input[name="dados_complementoPedido"]').fill(str(comp_val))
                time.sleep(delay_step)
            except Exception as e:
                self.log(f"[F3] [Item {nro}] Aviso ao preencher complemento: {e}", "AVISO")

        # 6. Avança para a Fase 4
        self.log(f"[F3] [Item {nro}] Etapa 6: Avançando para a Fase 4...", "DEBUG")
        try:
            self.page.locator('#botao_avancar, button:has-text("Avançar")').first.click()
        except Exception as e:
            raise FormFillError(f"Falha ao clicar no botão Avançar: {e}", field_name="botao_avancar", step="Fase 3")

        # 7. Aguarda transição com fechamento ativo de pop-ups
        self._aguardar_transicao_fase4(item)
        self.log(f"[F3] [Item {nro}] Fase 3 concluída com sucesso.", "SUCESSO")

    def _vincular_cotacao(self, item: ItemContrato, strategy: BaseStrategy, delay_step: float) -> None:
        nro = item.nro_cotacao
        search_target = item.extracted_nro_pedido or item.nro_cotacao

        try:
            self.page.locator('input[name="pesquisa_pedidos_id"]').fill(str(search_target))
            time.sleep(delay_step)
            self.page.locator('i[name="botaoPesquisa_pedidos_id"]').click()
            
            # Aguarda o AJAX de busca de pedidos popular as opções no select (state="attached")
            try:
                self.page.wait_for_selector(
                    'select[name="dados_pedidos_id"] option:not(:text("Carregando...")):not(:text("Carregando dados ..."))',
                    state="attached",
                    timeout=6000,
                )
            except Exception:
                pass

            select_loc = self.page.locator('select[name="dados_pedidos_id"]')
            select_loc.wait_for(state="attached", timeout=6000)

            options = select_loc.locator("option").all()
            opts_text = [opt.inner_text().strip() for opt in options]

            # Se a busca por pedido extraído retornou 'Nenhum registro', tenta fallback para a cotação
            if (
                any("Nenhum registro encontrado!" in t for t in opts_text)
                or (select_loc.get_attribute("title") or "").strip() == "Nenhum registro encontrado!"
            ) and search_target != item.nro_cotacao:
                self.log(f"[F3] [Item {nro}] Pedido '{search_target}' não encontrado. Tentando fallback para cotação '{item.nro_cotacao}'...", "DEBUG")
                search_target = item.nro_cotacao
                self.page.locator('input[name="pesquisa_pedidos_id"]').fill(str(search_target))
                time.sleep(delay_step)
                self.page.locator('i[name="botaoPesquisa_pedidos_id"]').click()
                try:
                    self.page.wait_for_selector(
                        'select[name="dados_pedidos_id"] option:not(:text("Carregando...")):not(:text("Carregando dados ..."))',
                        state="attached",
                        timeout=6000,
                    )
                except Exception:
                    pass
                options = select_loc.locator("option").all()
                opts_text = [opt.inner_text().strip() for opt in options]

            if any("Nenhum registro encontrado!" in t for t in opts_text):
                raise FormFillError(
                    f"Pedido/Cotação '{search_target}' não encontrado no ERP (nenhum registro retornado na busca).",
                    field_name="dados_pedidos_id", step="Fase 3")

            # Busca por prefixo ou correspondência do número pesquisado
            target_prefix = f"{search_target} /"
            target_val = None
            for opt in options:
                txt = opt.inner_text().strip()
                val = opt.get_attribute("value")
                if not val:
                    continue
                if (
                    txt.startswith(target_prefix)
                    or txt.startswith(f"{search_target} -")
                    or txt == str(search_target)
                    or str(search_target) in txt
                ):
                    target_val = val
                    break

            if not target_val and len(options) > 1:
                # Pega a primeira opção válida se houver
                for opt in options:
                    v = opt.get_attribute("value")
                    if v:
                        target_val = v
                        break

            if target_val:
                select_loc.select_option(value=target_val)
                self.log(f"[F3] [Item {nro}] Cotação vinculada com sucesso (value: {target_val}).", "DEBUG")
            else:
                raise FormFillError(
                    f"Opção correspondente a '{search_target}' não encontrada no select de pedidos.",
                    field_name="dados_pedidos_id", step="Fase 3")

            # Se houver NF extraída (Lactalis Especial / Diária), preenche e vincula o campo de NF auxiliar
            if item.extracted_nf:
                self.log(f"[F3] [Item {nro}] Vinculando Nota Fiscal '{item.extracted_nf}'...", "DEBUG")
                try:
                    # Usa seletor visível estrito (#pswobj3 ou input visível de notas)
                    input_nf = self.page.locator('#pswobj3:visible, input[name="pesquisa_dados_notas_carregamento_id"]:visible').first
                    if input_nf.count() > 0:
                        input_nf.fill(str(item.extracted_nf))
                        try:
                            input_nf.dispatch_event("change")
                        except Exception:
                            pass
                        time.sleep(delay_step)

                        # Botão de pesquisa de NF visível
                        btn_nf = self.page.locator('.swrepp:visible i.fa-solid, i[name="botaoPesquisa_dados_notas_carregamento_id"]:visible, #pswobj3 + em i').first
                        if btn_nf.count() > 0:
                            btn_nf.click()

                        select_nf_selector = '#cswobj3:visible, select[name*="dados_notas_carregamento_id"]:visible'
                        try:
                            self.page.wait_for_selector(
                                f'{select_nf_selector} option:not(:text("Carregando...")):not(:text("Carregando dados ..."))',
                                state="attached",
                                timeout=8000,
                            )
                        except Exception:
                            pass

                        select_nf = self.page.locator(select_nf_selector).first
                        if select_nf.count() > 0:
                            select_nf.wait_for(state="attached", timeout=5000)
                            options_nf = select_nf.locator("option").all()
                            target_nf_val = None
                            for opt in options_nf:
                                v = opt.get_attribute("value")
                                txt = opt.inner_text().strip()
                                if v and (str(item.extracted_nf) in txt or v != ""):
                                    target_nf_val = v
                                    if str(item.extracted_nf) in txt:
                                        break
                            if target_nf_val:
                                select_nf.select_option(value=target_nf_val)
                                try:
                                    select_nf.dispatch_event("change")
                                except Exception:
                                    pass
                                self.log(f"[F3] [Item {nro}] Nota Fiscal '{item.extracted_nf}' vinculada no select (value: {target_nf_val}).", "DEBUG")
                            time.sleep(delay_step)
                except Exception as e_nf:
                    safe_msg = str(e_nf).encode('ascii', errors='replace').decode('ascii')
                    self.log(f"[F3] [Item {nro}] Aviso ao pesquisar NF auxiliar: {safe_msg}", "AVISO")

        except FormFillError:
            raise
        except Exception as e:
            raise FormFillError(f"Erro ao pesquisar/vincular cotação: {e}", field_name="pesquisa_pedidos_id", step="Fase 3")

    def _aguardar_transicao_fase4(self, item: ItemContrato) -> None:
        nro = item.nro_cotacao
        primeiro_campo_fase4 = 'input[name="pesquisa_enderecoDestinatario_id"], select[name="dados_enderecoDestinatario_id"]'
        timeout_limit = time.time() + 30

        while time.time() < timeout_limit:
            DialogGuard.dismiss_all_popups(self.page, self.log, f"Item {nro}")
            # Aborta cedo se o portal exibiu um erro de negócio
            erro_negocio = DialogGuard.detectar_erro_negocio(self.page, self.log, f"[Item {nro}] ")
            if erro_negocio:
                raise NavigationError(f"Erro de negócio do portal na transição Fase 3->4: {erro_negocio}", url=self.page.url, step="Transição Fase 3->4")
            try:
                if self.page.locator(primeiro_campo_fase4).first.is_visible(timeout=300):
                    return
            except Exception:
                pass
            time.sleep(0.2)

        DialogGuard.dismiss_all_popups(self.page, self.log, f"Item {nro}")
        try:
            self.page.locator(primeiro_campo_fase4).first.wait_for(state="visible", timeout=5000)
        except PlaywrightTimeoutError:
            raise NavigationError("Timeout aguardando carregamento da Fase 4.", url=self.page.url, step="Transição Fase 3->4")
