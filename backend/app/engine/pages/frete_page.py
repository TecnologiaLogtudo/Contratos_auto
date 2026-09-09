from __future__ import annotations

import re
import time
from typing import Callable, Optional
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from ...domain.models import ItemContrato
from ...domain.errors import FormFillError, NavigationError
from ..dialog_guard import DialogGuard
from ..strategies.base_strategy import BaseStrategy
from ..strategies.lactalis_strategy import LactalisBaseStrategy, LactalisSpecialBaseStrategy
from ..strategies.dpa_strategy import DPAStrategy


class FretePage:
    """Page Object para a Fase 4 - Dados do Frete, Motorista e Veículo."""

    def __init__(self, page: Page, log_callback: Optional[Callable[[str, str], None]] = None):
        self.page = page
        self.log = log_callback or (lambda m, l="INFO": None)

    def preencher_fase4(
        self,
        item: ItemContrato,
        strategy: BaseStrategy,
        delay_step: float = 0.05,
    ) -> None:
        nro = item.nro_cotacao
        self.log(f"[F4] [Item {nro}] --- INÍCIO: DADOS DO FRETE E TRANSPORTE ---", "FASE")

        DialogGuard.dismiss_all_popups(self.page, self.log, f"Item {nro}")

        # 1. Sincronização de Remetente e Destinatário
        self.log(f"[F4] [Item {nro}] Etapa 1: Configurando Remetente e Destinatário...", "DEBUG")
        self._sincronizar_remetente_destinatario(item, strategy, delay_step)

        # 2. Cidade / Origem
        self.log(f"[F4] [Item {nro}] Etapa 2: Configurando Município de Origem...", "DEBUG")
        self._configurar_cidade_origem(item, strategy, delay_step)

        # 3. Natureza da Operação (CFOP)
        self.log(f"[F4] [Item {nro}] Etapa 3: Selecionando Natureza da Operação...", "DEBUG")
        self._configurar_natureza_operacao(item, delay_step)

        # 4. Motorista pela Placa
        self.log(f"[F4] [Item {nro}] Etapa 4: Buscando e vinculando Motorista (Placa: {item.placa})...", "DEBUG")
        self._configurar_motorista(item, delay_step)

        # 5. Tabela e Tipo de Carga
        self.log(f"[F4] [Item {nro}] Etapa 5: Selecionando Transporte Rodoviário e Carga Geral...", "DEBUG")
        try:
            self.page.locator('select[name="dados_freteMinimo_tabela"]').select_option(value="A")
            time.sleep(delay_step)
            self.page.locator('select[name="dados_freteMinimo_tipoCarga"]').select_option(value="GER")
            time.sleep(delay_step)
        except Exception as e:
            self.log(f"[F4] [Item {nro}] Aviso ao definir tipo de carga/tabela: {e}", "DEBUG")

        # 6. Composição / Regra do Frete
        regra_id = strategy.get_regra_frete_id()
        self.log(f"[F4] [Item {nro}] Etapa 6: Aplicando Regra de Frete ({regra_id})...", "DEBUG")
        try:
            regra_sel = self.page.locator('select[name="dados_regraFrete_id"]')
            if regra_sel.is_visible(timeout=2000):
                regra_sel.select_option(value=regra_id)
                time.sleep(delay_step)
        except Exception as e:
            self.log(f"[F4] [Item {nro}] Aviso ao configurar Regra de Frete: {e}", "DEBUG")

        # 7. Zeramento de impostos e campos monetários
        self.log(f"[F4] [Item {nro}] Etapa 7: Ajustando campos de valores...", "DEBUG")
        self._zerar_valores(item, delay_step)

        # 8. Regras monetárias especiais (Lactalis Diária Parada)
        if regra_id == "146":
            self._preencher_frete_terceiros_lactalis(item, delay_step)

        # 9. Senha Ravex (se aplicável)
        if isinstance(strategy, LactalisSpecialBaseStrategy):
            self._preencher_senha_ravex(item, delay_step)

        # 10. Observação PV
        obs_pv = strategy.get_observacao_pv(item)
        if obs_pv:
            self.log(f"[F4] [Item {nro}] Etapa 8: Preenchendo Observação PV...", "DEBUG")
            try:
                obs_loc = self.page.locator('textarea[name="dados_observacaoPV"]')
                obs_loc.click()
                obs_loc.fill(obs_pv)
                obs_loc.dispatch_event('input')
                obs_loc.dispatch_event('change')
                time.sleep(delay_step)
            except Exception as e:
                self.log(f"[F4] [Item {nro}] Aviso ao preencher Observação PV: {e}", "AVISO")

        # 11. Checkbox Ciente Valor Zerado
        try:
            self.page.locator('input[name="dados_conf_CTeValorZerado[]"]').check()
            time.sleep(delay_step)
        except Exception:
            pass

        # 12. Avança para a Fase 5
        self.log(f"[F4] [Item {nro}] Etapa 9: Avançando para a Fase 5...", "DEBUG")
        try:
            self.page.locator('#botao_avancar, button:has-text("Avançar")').first.click()
        except Exception as e:
            raise FormFillError(f"Falha ao clicar no botão Avançar: {e}", field_name="botao_avancar", step="Fase 4")

        # 13. Aguarda transição para a Fase 5
        self._aguardar_transicao_fase5(item)
        self.log(f"[F4] [Item {nro}] Fase 4 concluída com sucesso.", "SUCESSO")

    def _sincronizar_remetente_destinatario(self, item: ItemContrato, strategy: BaseStrategy, delay_step: float) -> None:
        nro = item.nro_cotacao
        DialogGuard.dismiss_all_popups(self.page, self.log, f"Item {nro}")

        if isinstance(strategy, LactalisSpecialBaseStrategy):
            # Mantém preenchimento automático
            self.log(f"[F4] [Item {nro}] Lactalis Especial: Remetente e Destinatário mantidos da cotação.", "DEBUG")
            return

        if isinstance(strategy, DPAStrategy):
            # Remetente DPA
            self._selecionar_remetente_por_cnpj("05.300.331/0014-85", item, delay_step, pick_second=True)
            # Destinatário Logtudo
            self._selecionar_destinatario_por_cnpj("20511709000169", item, delay_step)
            return

        if isinstance(strategy, LactalisBaseStrategy):
            # Remetente Lactalis
            self._selecionar_remetente_por_cnpj("43.340.312/0006-61", item, delay_step)
            # Destinatário Logtudo
            self._selecionar_destinatario_por_cnpj("20.511.709/0001-69", item, delay_step)
            return

        # Latam / Padrão: Sincroniza Destinatário com base no CNPJ do Remetente
        try:
            rem_sel = self.page.locator('select[name="dados_enderecoRemetente_id"]')
            rem_sel.wait_for(state="attached", timeout=6000)
            rem_val = rem_sel.input_value()
            if not rem_val:
                raise FormFillError("Remetente não está selecionado na tela.", field_name="dados_enderecoRemetente_id", step="Fase 4")

            rem_text = self.page.locator(f'select[name="dados_enderecoRemetente_id"] option[value="{rem_val}"]').inner_text().strip()
            cnpj_match = re.search(r'(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})|(\d{14})', rem_text)
            cnpj = re.sub(r'\D', '', cnpj_match.group(0)) if cnpj_match else re.sub(r'\D', '', rem_text)[:14]

            if not cnpj or len(cnpj) < 8:
                self.log(f"[F4] [Item {nro}] Aviso: CNPJ não identificado do Remetente ('{rem_text}').", "AVISO")
                return

            self._selecionar_destinatario_por_cnpj(cnpj, item, delay_step, fallback_value=rem_val)
        except FormFillError:
            raise
        except Exception as e:
            self.log(f"[F4] [Item {nro}] Aviso na sincronização Remetente/Destinatário: {e}", "AVISO")

    def _selecionar_remetente_por_cnpj(self, cnpj: str, item: ItemContrato, delay_step: float, pick_second: bool = False) -> None:
        nro = item.nro_cotacao
        try:
            DialogGuard.dismiss_all_popups(self.page, self.log, f"Item {nro}")
            self.page.locator('input[name="pesquisa_enderecoRemetente_id"]').fill(cnpj)
            time.sleep(delay_step)
            self.page.locator('i[name="botaoPesquisa_enderecoRemetente_id"]').click()

            rem_sel = self.page.locator('select[name="dados_enderecoRemetente_id"]')
            rem_sel.wait_for(state="attached", timeout=8000)
            options = rem_sel.locator("option").all()
            valid_opts = [opt for opt in options if opt.get_attribute("value")]

            if not valid_opts:
                raise FormFillError(f"Remetente com CNPJ '{cnpj}' não encontrado.", field_name="dados_enderecoRemetente_id", step="Fase 4")

            chosen = valid_opts[1] if (pick_second and len(valid_opts) >= 2) else valid_opts[0]
            val = chosen.get_attribute("value")
            rem_sel.select_option(value=val)
            self.log(f"[F4] [Item {nro}] Remetente selecionado com sucesso.", "DEBUG")
            time.sleep(delay_step)
        except Exception as e:
            raise FormFillError(f"Erro ao selecionar Remetente ({cnpj}): {e}", field_name="pesquisa_enderecoRemetente_id", step="Fase 4")

    def _selecionar_destinatario_por_cnpj(self, cnpj: str, item: ItemContrato, delay_step: float, fallback_value: Optional[str] = None) -> None:
        nro = item.nro_cotacao
        try:
            DialogGuard.dismiss_all_popups(self.page, self.log, f"Item {nro}")
            self.page.locator('input[name="pesquisa_enderecoDestinatario_id"]').fill(cnpj)
            time.sleep(delay_step)
            self.page.locator('i[name="botaoPesquisa_enderecoDestinatario_id"]').click()

            dest_sel = self.page.locator('select[name="dados_enderecoDestinatario_id"]')
            dest_sel.wait_for(state="attached", timeout=8000)
            options = dest_sel.locator("option").all()
            valid_opts = [opt for opt in options if opt.get_attribute("value")]

            if not valid_opts:
                if fallback_value:
                    dest_sel.select_option(value=fallback_value)
                    return
                raise FormFillError(f"Destinatário com CNPJ '{cnpj}' não encontrado.", field_name="dados_enderecoDestinatario_id", step="Fase 4")

            dest_sel.select_option(value=valid_opts[0].get_attribute("value"))
            self.log(f"[F4] [Item {nro}] Destinatário selecionado com sucesso.", "DEBUG")
            time.sleep(delay_step)
        except Exception as e:
            raise FormFillError(f"Erro ao selecionar Destinatário ({cnpj}): {e}", field_name="pesquisa_enderecoDestinatario_id", step="Fase 4")

    def _configurar_cidade_origem(self, item: ItemContrato, strategy: BaseStrategy, delay_step: float) -> None:
        nro = item.nro_cotacao
        cidade_alvo = strategy.get_cidade_origem(item.cidade)

        # Habilita Início/Fim da Prestação
        try:
            chk_prestacao = self.page.locator('input[name="dados_definirInicioFimPrestacao[]"]')
            if chk_prestacao.is_visible(timeout=1500) and not chk_prestacao.is_checked():
                chk_prestacao.check()
                time.sleep(delay_step)
        except Exception:
            pass

        tentativas = [cidade_alvo]
        if cidade_alvo == "J. Pessoa":
            tentativas.extend(["João Pessoa", "Pessoa"])
        elif "simoes" in cidade_alvo.lower() or "simões" in cidade_alvo.lower():
            tentativas.append("Simoes Filho")

        # Busca tolerante: variações de capitalização e de acentuação para o
        # mesmo nome (ex.: 'Simões filho' -> 'Simões Filho' -> 'Simoes Filho').
        import unicodedata
        base = cidade_alvo.strip().title()
        sem_acento = "".join(c for c in unicodedata.normalize("NFD", base) if unicodedata.category(c) != "Mn")
        for v in (base, sem_acento):
            if v not in tentativas:
                tentativas.append(v)

        cidade_ok = False
        for cid in tentativas:
            try:
                DialogGuard.dismiss_all_popups(self.page, self.log, f"Item {nro}")
                self.page.locator('input[name="pesquisa_cMunIni"]').fill(cid)
                time.sleep(delay_step)
                self.page.locator('i[name="botaoPesquisa_cMunIni"]').click()

                cid_sel = self.page.locator('select[name="dados_cMunIni"]')
                cid_sel.wait_for(state="attached", timeout=6000)
                options = cid_sel.locator("option").all()

                if any("Nenhum registro encontrado!" in opt.inner_text() for opt in options):
                    continue

                valid_opts = [opt for opt in options if opt.get_attribute("value")]
                if valid_opts:
                    cid_sel.select_option(value=valid_opts[0].get_attribute("value"))
                    self.log(f"[F4] [Item {nro}] Município de Origem '{cid}' selecionado.", "DEBUG")
                    cidade_ok = True
                    break
            except Exception:
                continue

        if not cidade_ok:
            raise FormFillError(f"Não foi possível localizar o município de origem '{cidade_alvo}'.", field_name="pesquisa_cMunIni", step="Fase 4")

    def _configurar_natureza_operacao(self, item: ItemContrato, delay_step: float) -> None:
        try:
            self.page.locator('i[name="botaoPesquisa_cfops_id"]').click()
            time.sleep(delay_step)
            nat_sel = self.page.locator('select[name="dados_cfops_id"]')
            if not nat_sel.input_value():
                nat_sel.select_option(value="1")
                time.sleep(delay_step)
        except Exception:
            pass

    def _configurar_motorista(self, item: ItemContrato, delay_step: float) -> None:
        nro = item.nro_cotacao
        placa = item.placa
        if not placa or placa == "PLACA NÃO ENCONTRADA":
            raise FormFillError("Placa não informada ou inválida na planilha.", field_name="pesquisa_dados_motorista_id", step="Fase 4")

        try:
            DialogGuard.dismiss_all_popups(self.page, self.log, f"Item {nro}")
            self.page.locator('input[name="pesquisa_dados_motorista_id"]').fill(placa)
            time.sleep(delay_step)
            self.page.locator('i[name="botaoPesquisa_dados_motorista_id"]').click()

            mot_sel = self.page.locator('select[name="dados_motorista_id"]')
            mot_sel.wait_for(state="attached", timeout=12000)
            
            # Aguarda sair do estado de carregamento
            self.page.wait_for_selector('select[name="dados_motorista_id"] option:not(:text("Carregando dados ..."))', timeout=12000)

            options = mot_sel.locator("option").all()
            if any("Nenhum registro encontrado!" in opt.inner_text() for opt in options):
                raise FormFillError(f"Motorista não encontrado no sistema para a placa '{placa}'.", field_name="dados_motorista_id", step="Fase 4")

            valid_opts = [opt for opt in options if opt.get_attribute("value")]
            if not valid_opts:
                raise FormFillError(f"Nenhum motorista retornado para a placa '{placa}'.", field_name="dados_motorista_id", step="Fase 4")

            mot_sel.select_option(value=valid_opts[0].get_attribute("value"))
            self.log(f"[F4] [Item {nro}] Motorista vinculado à placa '{placa}'.", "DEBUG")
            time.sleep(delay_step)
        except FormFillError:
            raise
        except Exception as e:
            raise FormFillError(f"Erro ao vincular motorista pela placa '{placa}': {e}", field_name="dados_motorista_id", step="Fase 4")

    def _zerar_valores(self, item: ItemContrato, delay_step: float) -> None:
        campos = [
            'input[name="dados_valorFrete"]',
            'input[name="dados_baseCalculo"]',
            'input[name="dados_aliquota"]',
            'input[name="dados_valorICMS"]',
            'input[name="dados_valoresOutros"]',
            'input[name="dados_totalPrestacao"]',
        ]
        for sel in campos:
            try:
                loc = self.page.locator(sel)
                if loc.is_visible(timeout=500) and loc.is_editable():
                    loc.fill("0,00")
            except Exception:
                pass

    def _preencher_frete_terceiros_lactalis(self, item: ItemContrato, delay_step: float) -> None:
        def parse_float(v):
            if v is None: return 0.0
            if isinstance(v, (int, float)): return float(v)
            v_str = str(v).replace("R$", "").replace(".", "").replace(",", ".").strip()
            try: return float(v_str)
            except ValueError: return 0.0

        val_escolhido = parse_float(item.frete_negociado) or parse_float(item.frete_a_pagar)
        val_str = f"{val_escolhido:.2f}".replace(".", ",")
        try:
            loc = self.page.locator('input[name="dados_outrosValores[freteterceiros]"]')
            if loc.is_visible(timeout=1500) and loc.is_editable():
                loc.fill(val_str)
                time.sleep(delay_step)
        except Exception:
            pass

    def _preencher_senha_ravex(self, item: ItemContrato, delay_step: float) -> None:
        try:
            ravex_box = self.page.get_by_role("textbox", name="Senha Ravex")
            if ravex_box.is_visible(timeout=1500):
                ravex_box.fill(str(item.nro_cotacao))
            else:
                self.page.locator('input[name="dados_outrosValores[senha_ravex]"]').fill(str(item.nro_cotacao))
            time.sleep(delay_step)
        except Exception:
            pass

    def _aguardar_transicao_fase5(self, item: ItemContrato) -> None:
        nro = item.nro_cotacao
        primeiro_campo_fase5 = 'input[name="dados_dtFimViagem"]'
        timeout_limit = time.time() + 30

        while time.time() < timeout_limit:
            DialogGuard.dismiss_all_popups(self.page, self.log, f"Item {nro}")
            # Aborta cedo se o portal exibiu um erro de negócio
            # (ex.: data de emissão x data de pagamento, status da cotação)
            erro_negocio = DialogGuard.detectar_erro_negocio(self.page, self.log, f"[Item {nro}] ")
            if erro_negocio:
                raise NavigationError(f"Erro de negócio do portal na transição Fase 4->5: {erro_negocio}", url=self.page.url, step="Transição Fase 4->5")
            try:
                if self.page.locator(primeiro_campo_fase5).is_visible(timeout=300):
                    return
            except Exception:
                pass
            time.sleep(0.2)

        DialogGuard.dismiss_all_popups(self.page, self.log, f"Item {nro}")
        try:
            self.page.locator(primeiro_campo_fase5).wait_for(state="visible", timeout=5000)
        except PlaywrightTimeoutError:
            raise NavigationError("Timeout aguardando carregamento da Fase 5.", url=self.page.url, step="Transição Fase 4->5")
