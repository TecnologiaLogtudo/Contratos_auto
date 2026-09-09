from __future__ import annotations

import time
from typing import Callable, Optional
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from ...domain.models import ItemContrato
from ...domain.errors import FormFillError, SubmissionError
from ..dialog_guard import DialogGuard
from ..strategies.base_strategy import BaseStrategy


class ContratoPage:
    """Page Object para a Fase 5 - Emissão e Finalização do Contrato de Frete."""

    def __init__(self, page: Page, log_callback: Optional[Callable[[str, str], None]] = None):
        self.page = page
        self.log = log_callback or (lambda m, l="INFO": None)

    def preencher_e_salvar_fase5(
        self,
        item: ItemContrato,
        strategy: BaseStrategy,
        delay_step: float = 0.05,
        dados_km: str = "20",
        aceitar_frete_minimo_antt: bool = True,
    ) -> None:
        nro = item.nro_cotacao
        self.log(f"[F5] [Item {nro}] --- INÍCIO: EMISSÃO DO CONTRATO DE FRETE ---", "FASE")

        DialogGuard.dismiss_all_popups(self.page, self.log, f"Item {nro}")

        # 1. Data Final de Viagem
        self.log(f"[F5] [Item {nro}] Etapa 1: Preenchendo Data Fim de Viagem...", "DEBUG")
        dt_fim = strategy.get_fim_viagem(self.page, item)
        if not dt_fim:
            raise FormFillError("Data de pagamento ou emissão indisponível para Fim de Viagem.", field_name="dados_dtFimViagem", step="Fase 5")

        try:
            self.page.locator('input[name="dados_dtFimViagem"]').fill(dt_fim)
            time.sleep(delay_step)
        except Exception as e:
            raise FormFillError(f"Falha ao preencher Fim de Viagem: {e}", field_name="dados_dtFimViagem", step="Fase 5")

        # 2. Perfil de Apropriação
        self.log(f"[F5] [Item {nro}] Etapa 2: Selecionando Perfil de Apropriação...", "DEBUG")
        self._configurar_perfil_apropriacao(item, strategy, delay_step)

        # 3. Km
        km_val = strategy.get_valor_km(dados_km)
        self.log(f"[F5] [Item {nro}] Etapa 3: Preenchendo Km ({km_val})...", "DEBUG")
        try:
            self.page.locator('input[name="dados_kms"]').fill(km_val)
            time.sleep(delay_step)
        except Exception as e:
            self.log(f"[F5] [Item {nro}] Aviso ao preencher Km: {e}", "DEBUG")

        # 4. NCM
        self.log(f"[F5] [Item {nro}] Etapa 4: Selecionando NCM...", "DEBUG")
        self._configurar_ncm(item, strategy, delay_step)

        # 5. Composição Veicular (Sim -> value "S")
        try:
            comp_loc = self.page.locator('select[name="dados_composicao_veicular"]')
            if comp_loc.is_visible(timeout=1500):
                comp_loc.select_option(value="S")
                time.sleep(delay_step)
        except Exception:
            pass

        # 6. Regra de Carreto
        self.log(f"[F5] [Item {nro}] Etapa 5: Selecionando Regra de Carreto...", "DEBUG")
        self._configurar_regra_carreto(item, delay_step)

        # 7. Observação do Contrato
        obs_contrato = strategy.get_observacao_contrato(item)
        self.log(f"[F5] [Item {nro}] Etapa 6: Preenchendo Observação do Contrato...", "DEBUG")
        try:
            self.page.locator('textarea[name="dados_obs"]').fill(obs_contrato)
            time.sleep(delay_step)
        except Exception as e:
            self.log(f"[F5] [Item {nro}] Aviso ao preencher Observação do Contrato: {e}", "AVISO")

        # 8. Operadora REPOM PÓS PAGO (value 10) e Cartão
        self.log(f"[F5] [Item {nro}] Etapa 7: Configurando REPOM...", "DEBUG")
        try:
            self.page.locator('select[name="dados_operadoraCredito_id"]').select_option(value="10")
            time.sleep(delay_step)
            cartao_loc = self.page.locator('input[name="dados_nroCartaoOperadoraCredito"]')
            if not cartao_loc.input_value():
                cartao_loc.fill("0")
                time.sleep(delay_step)
            self.page.locator('select[name="dados_operacaoRepom"]').select_option(value="5")  # SEM CIOT
            time.sleep(delay_step)
            self.page.locator('select[name="dados_tipoSaldoRepom"]').select_option(value="P")
            time.sleep(delay_step)
        except Exception as e:
            self.log(f"[F5] [Item {nro}] Aviso ao configurar operadora/cartão: {e}", "AVISO")

        # 9. Remetente do Contrato se for Viagem Extra
        if item.viagem_extra == "Sim":
            self.log(f"[F5] [Item {nro}] Etapa 8: Viagem Extra detectada. Vinculando Remetente...", "DEBUG")
            self._configurar_remetente_viagem_extra(item, delay_step)

        # 10. Destinatário do Contrato ('logtudo')
        self.log(f"[F5] [Item {nro}] Etapa 9: Vinculando Destinatário Contrato (Logtudo)...", "DEBUG")
        self._configurar_destinatario_contrato(item, delay_step)

        # 11. Data Programada do Saldo
        dt_prog = strategy.get_data_programada(item)
        if not dt_prog:
            raise FormFillError("Data Programada não pode ser calculada (Validade ou Data Pagamento ausente).", field_name="dados_dataSaldoRepom", step="Fase 5")

        self.log(f"[F5] [Item {nro}] Etapa 10: Preenchendo Data Programada ({dt_prog})...", "DEBUG")
        try:
            self.page.locator('input[name="dados_dataSaldoRepom"]').fill(dt_prog)
            time.sleep(delay_step)
        except Exception as e:
            raise FormFillError(f"Falha ao preencher Data Programada: {e}", field_name="dados_dataSaldoRepom", step="Fase 5")

        # 12. Confirmação Frete Mínimo ANTT
        if aceitar_frete_minimo_antt:
            chk_antt = self.page.locator('#confirmacaoFreteMinimo_concorda')
            if chk_antt.is_visible(timeout=1500):
                self.log(f"[F5] [Item {nro}] Aceitando aviso de Frete Mínimo ANTT...", "DEBUG")
                chk_antt.check()
                time.sleep(delay_step)

        # 13. Confirmação NCM
        try:
            self.page.locator('input[name="dados_confirmacaoNCMGeral_concorda"]').check()
            time.sleep(delay_step)
        except Exception:
            pass

        # 14. Salvamento & Contingência CFOP
        self.log(f"[F5] [Item {nro}] Etapa 11: Submetendo e salvando contrato...", "INFO")
        self._salvar_e_validar_conclusao(item, delay_step)
        self.log(f"[F5] [Item {nro}] Contrato emitido e salvo com sucesso!", "SUCESSO")

    def _configurar_perfil_apropriacao(self, item: ItemContrato, strategy: BaseStrategy, delay_step: float) -> None:
        nro = item.nro_cotacao
        termo = strategy.get_termo_busca_perfil(item.cidade)
        try:
            DialogGuard.dismiss_all_popups(self.page, self.log, f"Item {nro}")
            self.page.locator('input[name="pesquisa_dados_perfisApropriacao_id"]').fill(termo)
            time.sleep(delay_step)
            self.page.locator('i[name="botaoPesquisa_dados_perfisApropriacao_id"]').click()

            sel = self.page.locator('select[name="dados_perfisApropriacao_id"]')
            sel.wait_for(state="attached", timeout=6000)
            options = sel.locator("option").all()

            if any("Nenhum registro encontrado!" in opt.inner_text() for opt in options):
                raise FormFillError(f"Perfil de Apropriação não encontrado para '{termo}'.", field_name="dados_perfisApropriacao_id", step="Fase 5")

            valid_opts = [opt for opt in options if opt.get_attribute("value")]
            if not valid_opts:
                raise FormFillError(f"Nenhum Perfil de Apropriação válido retornado para '{termo}'.", field_name="dados_perfisApropriacao_id", step="Fase 5")

            sel.select_option(value=valid_opts[0].get_attribute("value"))
            time.sleep(delay_step)
        except FormFillError:
            raise
        except Exception as e:
            raise FormFillError(f"Erro ao selecionar Perfil de Apropriação: {e}", field_name="dados_perfisApropriacao_id", step="Fase 5")

    def _configurar_ncm(self, item: ItemContrato, strategy: BaseStrategy, delay_step: float) -> None:
        nro = item.nro_cotacao
        termo = strategy.get_ncm_pesquisa()
        val = strategy.get_ncm_valor()
        try:
            DialogGuard.dismiss_all_popups(self.page, self.log, f"Item {nro}")
            self.page.locator('input[name="pesquisa_dados_ncm"]').fill(termo)
            time.sleep(delay_step)
            self.page.locator('i[name="botaoPesquisa_dados_ncm"]').click()

            ncm_sel = self.page.locator('select[name="dados_ncm"]')
            ncm_sel.wait_for(state="attached", timeout=8000)
            ncm_sel.select_option(value=val)
            time.sleep(delay_step)
        except Exception as e:
            raise FormFillError(f"Erro ao selecionar NCM '{val}': {e}", field_name="dados_ncm", step="Fase 5")

    def _configurar_regra_carreto(self, item: ItemContrato, delay_step: float) -> None:
        nro = item.nro_cotacao
        try:
            sel = self.page.locator('select[name="dados_regrasCarreto_id"]')
            sel.wait_for(state="visible", timeout=8000)
            options = sel.locator("option").all()

            chosen_val = None
            for opt in options:
                txt = opt.inner_text().lower()
                if "base tabela" in txt or "baseado tabela" in txt:
                    chosen_val = opt.get_attribute("value")
                    break

            if not chosen_val:
                valid_opts = [opt for opt in options if opt.get_attribute("value")]
                if valid_opts:
                    chosen_val = valid_opts[0].get_attribute("value")

            if chosen_val:
                sel.select_option(value=chosen_val)
                time.sleep(delay_step)
            else:
                raise FormFillError("Nenhuma Regra de Carreto disponível para seleção.", field_name="dados_regrasCarreto_id", step="Fase 5")
        except FormFillError:
            raise
        except Exception as e:
            raise FormFillError(f"Erro ao selecionar Regra de Carreto: {e}", field_name="dados_regrasCarreto_id", step="Fase 5")

    def _configurar_remetente_viagem_extra(self, item: ItemContrato, delay_step: float) -> None:
        rem_busca = item.remetente.split(" - ")[0].strip() if " - " in item.remetente else item.remetente
        try:
            self.page.locator('input[name="pesquisa_dados_enderecoRemetenteContrato_id"]').fill(rem_busca)
            time.sleep(delay_step)
            self.page.locator('i[name="botaoPesquisa_dados_enderecoRemetenteContrato_id"]').click()
            time.sleep(delay_step)
        except Exception:
            pass

    def _configurar_destinatario_contrato(self, item: ItemContrato, delay_step: float) -> None:
        nro = item.nro_cotacao
        try:
            self.page.locator('input[name="pesquisa_dados_enderecoDestinatarioContrato_id"]').fill("logtudo")
            time.sleep(delay_step)
            self.page.locator('i[name="botaoPesquisa_dados_enderecoDestinatarioContrato_id"]').click()

            dest_sel = self.page.locator('select[name="dados_enderecoDestinatarioContrato_id"]')
            dest_sel.wait_for(state="attached", timeout=8000)
            dest_sel.select_option(value="1")
            time.sleep(delay_step)
        except Exception as e:
            self.log(f"[F5] [Item {nro}] Aviso ao vincular Destinatário Contrato: {e}", "DEBUG")

    def _salvar_e_validar_conclusao(self, item: ItemContrato, delay_step: float) -> None:
        nro = item.nro_cotacao
        btn_save = self.page.locator('#botao_cadastrar, button:has-text("Salvar")').first

        try:
            btn_save.click()
            time.sleep(1.0)
        except Exception as e:
            raise SubmissionError(f"Falha ao clicar no botão Salvar: {e}")

        # 1. Verifica erros de validação imediata na tela
        if self.page.locator('input[name="dados_freteMinimo_valor"].swstatus-input-error').is_visible():
            raise SubmissionError("Campo 'Frete Mínimo' inválido ou vazio.")

        mot_err = self.page.locator('div.rotina-generica.alert-message.error:has-text("Os seguintes campos são obrigatórios")')
        if mot_err.is_visible():
            raise SubmissionError(f"Campos obrigatórios pendentes: {mot_err.inner_text().strip()}")

        # Alerta genérico de erro de negócio (ex.: "A data de emissão não pode ser
        # ser maior que a data programada do saldo.", "Status da cotação não permite
        # editar a mesma."). Detecta e registra o motivo específico imediatamente,
        # evitando esperar o timeout completo da submissão.
        erro_negocio = DialogGuard.detectar_erro_negocio(self.page, self.log, f"[Item {nro}] ")
        if erro_negocio:
            raise SubmissionError(f"Erro de negócio do portal: {erro_negocio}")

        # 2. Verifica modal de aprovação de CFOP (Primeiro Uso de CFOP)
        cfop_container = self.page.locator('#COM_RF_confirmacaoPrimeiroUsoCFOP')
        if cfop_container.is_visible(timeout=2500):
            self.log(f"[F5] [Item {nro}] Aviso de primeiro uso de CFOP detectado. Aplicando autorização...", "INFO")
            try:
                radio_s = self.page.locator('input[name="dados_conf_primeiroUsoCFOP_comPermissao"][value="S"]')
                radio_s.click(force=True)
                radio_s.dispatch_event('change')
                time.sleep(delay_step)

                self.page.locator('#botao_avancar').first.click()
                time.sleep(delay_step)

                # Re-confirma checkboxes
                chk_antt = self.page.locator('#confirmacaoFreteMinimo_concorda')
                if chk_antt.is_visible(timeout=1000):
                    chk_antt.check()

                self.page.locator('input[name="dados_confirmacaoNCMGeral_concorda"]').check()
                time.sleep(delay_step)

                btn_save.click()
                time.sleep(1.0)
            except Exception as e_cfop:
                raise SubmissionError(f"Falha ao processar autorização de CFOP: {e_cfop}")

        # 3. Aguarda URL de sucesso após submissão
        try:
            self.page.wait_for_url(lambda u: "/rotinas/" in u and "/rotinas/formulario" not in u, timeout=45000)
        except PlaywrightTimeoutError:
            # Se timeout, verifica se há erro persistente visível
            DialogGuard.dismiss_all_popups(self.page, self.log, f"Item {nro}")
            # Tenta extrair o motivo específico do alerta de erro do portal
            # (evita registrar erro genérico "Timeout aguardando confirmação...")
            erro_negocio = DialogGuard.detectar_erro_negocio(self.page, self.log, f"[Item {nro}] ")
            if erro_negocio:
                raise SubmissionError(f"Erro de negócio do portal: {erro_negocio}")
            if "/rotinas/formulario" in self.page.url:
                raise SubmissionError("Timeout aguardando confirmação de salvamento do contrato.")
