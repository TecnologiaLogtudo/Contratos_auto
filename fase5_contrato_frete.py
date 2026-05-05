import threading
from playwright.sync_api import Page, Error, TimeoutError
from typing import Callable, Dict
from datetime import datetime

import time
from fase3_preenchimento import registrar_erro_em_planilha, registrar_sucesso_em_planilha

def preencher_contrato_frete(
    page: Page,
    dados_linha: Dict[str, str],
    log_callback: Callable[[str, str], None],
    pause_event: threading.Event,
    atraso_etapas: float,
    output_filepath: str,
    atraso_fases: float,
    dados_km: str,
) -> bool:
    """
    Executa os passos de preenchimento da Fase 5 (Contrato Frete).
    Retorna True em caso de sucesso, False em caso de falha.
    """
    try:
        nro_cotacao = dados_linha.get("Nro cotação", "N/A")
        log_callback(f"[F5] [Item {nro_cotacao}] --- INÍCIO: CONTRATO DE FRETE ---", "FASE")

        # ETAPA 1: Preencher Data Final de Viagem
        pause_event.wait()
        log_callback(f"[F5] [Item {nro_cotacao}] Etapa 1: Preenchendo Data Final da Viagem...", "DEBUG")
        data_fim_viagem_selector = 'input[name="dados_dtFimViagem"]'
        data_pagamento_raw = dados_linha.get("Data pagamento", "DATA NÃO ENCONTRADA")

        if data_pagamento_raw and data_pagamento_raw != "DATA NÃO ENCONTRADA":
            # Garante que a data esteja no formato string dd/mm/aaaa
            if isinstance(data_pagamento_raw, datetime):
                data_pagamento = data_pagamento_raw.strftime('%d/%m/%Y')
            else:
                # Se já for string, assume que está no formato correto (vindo da fase 1)
                data_pagamento = str(data_pagamento_raw)

            log_callback(f"[F5] [Item {nro_cotacao}] Preenchendo 'Fim viagem' com 'Data pagamento': '{data_pagamento}'.", "DEBUG")
            data_pagamento_com_hora = f"{data_pagamento} 12:00"

            page.click(data_fim_viagem_selector)
            page.fill(data_fim_viagem_selector, data_pagamento_com_hora)
            log_callback(f"[F5] [Item {nro_cotacao}] Campo 'Fim viagem' preenchido com '{data_pagamento_com_hora}'.", "DEBUG")
        else:
            motivo_erro = "Data de pagamento não encontrada na planilha para preencher 'Data Final da Viagem'."
            log_callback(f"[F5] [Item {nro_cotacao}] ERRO: {motivo_erro} Cancelando item.", "ERRO")
            registrar_erro_em_planilha(dados_linha, motivo_erro, log_callback, output_filepath)
            return False # Sinaliza falha para pular para o próximo item

        time.sleep(atraso_etapas)

        # ETAPA 2: Preencher Perfil Apropriação com a Cidade da planilha
        pause_event.wait()
        cidade_planilha = dados_linha.get("Cidade", "N/A")
        log_callback(f"[F5] [Item {nro_cotacao}] Etapa 2: Preenchendo Perfil Apropriação com a cidade da planilha: '{cidade_planilha}'...", "DEBUG")

        perfil_apropriacao_select_selector = 'select[name="dados_perfisApropriacao_id"]'

        try:
            if cidade_planilha in ["N/A", "CIDADE NÃO ENCONTRADA"]:
                motivo_erro = "Cidade não disponível na planilha para preenchimento do Perfil Apropriação."
                log_callback(f"[F5] [Item {nro_cotacao}] ERRO: {motivo_erro}", "ERRO")
                registrar_erro_em_planilha(dados_linha, motivo_erro, log_callback, output_filepath)
                return False

            # Preenche o campo de pesquisa e clica no botão
            page.fill('input[name="pesquisa_dados_perfisApropriacao_id"]', cidade_planilha)
            time.sleep(atraso_etapas)
            page.click('i[name="botaoPesquisa_dados_perfisApropriacao_id"]')
            page.wait_for_timeout(500) # Aguarda a população do select

            # Verifica as opções do select
            perfil_apropriacao_locator = page.locator(perfil_apropriacao_select_selector)
            perfil_apropriacao_locator.wait_for(timeout=5000)

            options = perfil_apropriacao_locator.locator("option").all()
            
            # Caso 1: "Nenhum registro encontrado!"
            if any("Nenhum registro encontrado!" in opt.inner_text() for opt in options):
                motivo_erro = f"Nenhum registro de Perfil de Apropriação encontrado para '{cidade_planilha}'."
                log_callback(f"[F5] [Item {nro_cotacao}] ERRO: {motivo_erro}", "ERRO")
                registrar_erro_em_planilha(dados_linha, motivo_erro, log_callback, output_filepath)
                return False
            
            # Caso 2: Selecionar a primeira opção válida
            for opt in options:
                value = opt.get_attribute("value")
                if value: # Se o valor não for vazio
                    perfil_apropriacao_locator.select_option(value=value)
                    log_callback(f"[F5] [Item {nro_cotacao}] Perfil de Apropriação selecionado: '{opt.inner_text().strip()}'", "DEBUG")
                    break
            
            # Se nenhuma opção válida foi selecionada (ex: apenas a opção vazia ou "Nenhum registro encontrado!" estava presente)
            if not perfil_apropriacao_locator.input_value(): # Verifica se o select ainda está vazio
                motivo_erro = f"Nenhum Perfil de Apropriação válido foi selecionado para '{cidade_planilha}' após a pesquisa."
                log_callback(f"[F5] [Item {nro_cotacao}] ERRO: {motivo_erro}", "ERRO")
                registrar_erro_em_planilha(dados_linha, motivo_erro, log_callback, output_filepath)
                return False

        except Error as e:
            motivo_erro = f"Erro ao interagir com o campo 'Perfil de Apropriação'. Detalhe: {e}"
            log_callback(f"[F5] [Item {nro_cotacao}] ERRO: {motivo_erro}", "ERRO")
            registrar_erro_em_planilha(dados_linha, motivo_erro, log_callback, output_filepath)
            return False
            
        time.sleep(atraso_etapas)

        # ETAPA 3: Preencher Km
        pause_event.wait()
        log_callback(f"[F5] [Item {nro_cotacao}] Etapa 3: Preenchendo Km com '{dados_km}'...", "DEBUG")
        page.fill('input[name="dados_kms"]', dados_km)

        time.sleep(atraso_etapas)

        # ETAPA 4: Pesquisar e Selecionar NCM
        pause_event.wait()
        log_callback(f"[F5] [Item {nro_cotacao}] Etapa 4: Pesquisando e selecionando NCM 'vinho'...", "DEBUG")
        
        # Preenche o campo de pesquisa com 'vinho'
        page.fill('input[name="pesquisa_dados_ncm"]', "vinho")
        
        # Clica no botão de pesquisa
        page.click('i[name="botaoPesquisa_dados_ncm"]')
        
        # Aguarda os resultados da pesquisa aparecerem no select
        ncm_selector = 'select[name="dados_ncm"]'
        option_to_wait_for = f'{ncm_selector} option[value="2204."]'
        log_callback(f"[F5] [Item {nro_cotacao}] Aguardando resultados da pesquisa de NCM...", "DEBUG")
        # Alteração: Esperar o elemento estar 'attached' (presente no DOM), não 'visible'
        page.wait_for_selector(option_to_wait_for, state="attached", timeout=10000)
        
        # Seleciona a opção desejada que começa com 2204
        log_callback(f"[F5] [Item {nro_cotacao}] Selecionando NCM '2204.'...", "DEBUG")
        page.select_option(ncm_selector, value="2204.")

        time.sleep(atraso_etapas)

        # ETAPA 5: Selecionar Regra
        pause_event.wait()
        log_callback(f"[F5] [Item {nro_cotacao}] Etapa 5: Selecionando Regra de Carreto...", "DEBUG")
        
        regra_selector = 'select[name="dados_regrasCarreto_id"]'
        selected_value = None
        selected_text = ""

        try:
            # Espera o elemento select estar visível
            page.wait_for_selector(regra_selector, state="visible", timeout=10000)
            options = page.locator(regra_selector).locator("option").all()

            # 1. Tenta encontrar "Base Tabela"
            search_term_1 = "Base Tabela"
            for opt in options:
                if search_term_1.lower() in opt.inner_text().lower():
                    selected_value = opt.get_attribute("value")
                    selected_text = opt.inner_text().strip()
                    break
            
            # 2. Se não encontrou, tenta "Baseado Tabela"
            if not selected_value:
                search_term_2 = "Baseado Tabela"
                for opt in options:
                    if search_term_2.lower() in opt.inner_text().lower():
                        selected_value = opt.get_attribute("value")
                        selected_text = opt.inner_text().strip()
                        break
            
            # 3. Se ainda não encontrou, verifica se há apenas uma opção válida
            if not selected_value:
                valid_options = [opt for opt in options if opt.get_attribute("value")]
                if len(valid_options) == 1:
                    selected_value = valid_options[0].get_attribute("value")
                    selected_text = valid_options[0].inner_text().strip()
                    log_callback(f"[F5] [Item {nro_cotacao}] Nenhuma regra padrão encontrada. Selecionando a única opção disponível: '{selected_text}'", "AVISO")

            if selected_value:
                page.select_option(regra_selector, value=selected_value)
                log_callback(f"[F5] [Item {nro_cotacao}] Regra '{selected_text}' selecionada com sucesso.", "INFO")
            else:
                available_options_text = [opt.inner_text().strip() for opt in options if opt.get_attribute("value")]
                motivo_erro = f"Não foi possível determinar a Regra de Carreto. Opções disponíveis: {available_options_text}"
                log_callback(f"[F5] [Item {nro_cotacao}] ERRO: {motivo_erro}", "ERRO")
                registrar_erro_em_planilha(dados_linha, motivo_erro, log_callback, output_filepath)
                return False

        except Error as e:
            motivo_erro = f"Erro de Playwright ao tentar selecionar a Regra de Carreto: {e}. Verifique se o elemento está visível e as opções carregadas."
            log_callback(f"[F5] [Item {nro_cotacao}] ERRO: {motivo_erro}", "ERRO")
            registrar_erro_em_planilha(dados_linha, motivo_erro, log_callback, output_filepath)
            return False
        time.sleep(atraso_etapas)

        # ETAPA 6: Preencher Observação
        pause_event.wait()
        log_callback(f"[F5] [Item {nro_cotacao}] Etapa 6: Preenchendo Observação 'Contrato Diária'...", "DEBUG")
        page.fill('textarea[name="dados_obs"]', "Contrato Diária")

        time.sleep(atraso_etapas)

        # ETAPA 7: Selecionar Operadora de Crédito
        pause_event.wait()
        log_callback(f"[F5] [Item {nro_cotacao}] Etapa 7: Selecionando Operadora 'REPOM - POS PAGO'...", "DEBUG")
        page.select_option('select[name="dados_operadoraCredito_id"]', value="7")

        time.sleep(atraso_etapas)

        # ETAPA 8: Preencher Número do Cartão
        pause_event.wait()
        log_callback(f"[F5] [Item {nro_cotacao}] Etapa 8: Verificando e preenchendo Número do Cartão...", "DEBUG")
        cartao_selector = 'input[name="dados_nroCartaoOperadoraCredito"]'
        if not page.input_value(cartao_selector):
            log_callback(f"[F5] [Item {nro_cotacao}] Número do Cartão vazio. Preenchendo com '0'.", "DEBUG")
            page.fill(cartao_selector, "0")

        time.sleep(atraso_etapas)

        # ETAPA 9: Preencher Operação
        pause_event.wait()
        log_callback(f"[F5] [Item {nro_cotacao}] Etapa 9: Preenchendo Operação 'PADRAO'...", "DEBUG")
        # CORREÇÃO: O campo é um <select> com name="dados_operacaoRepom" e o valor para "PADRAO" é "1".
        operacao_selector = 'select[name="dados_operacaoRepom"]'
        option_padrao_selector = f'{operacao_selector} option[value="1"]'
        log_callback(f"[F5] [Item {nro_cotacao}] Aguardando opção 'PADRAO' para Operação...", "DEBUG")
        page.wait_for_selector(option_padrao_selector, state="attached", timeout=10000)
        page.select_option(operacao_selector, value="1")

        time.sleep(atraso_etapas)

        # ETAPA 10: Selecionar Tipo de Saldo
        pause_event.wait()
        log_callback(f"[F5] [Item {nro_cotacao}] Etapa 10: Selecionando Tipo de Saldo...", "DEBUG")
        tipo_saldo_selector = 'select[name="dados_tipoSaldoRepom"]'
        option_p_selector = f'{tipo_saldo_selector} option[value="P"]'
        log_callback(f"[F5] [Item {nro_cotacao}] Aguardando opção 'P' para Tipo de Saldo...", "DEBUG")
        page.wait_for_selector(option_p_selector, state="attached", timeout=10000)
        page.select_option(tipo_saldo_selector, value="P")
        time.sleep(atraso_etapas)

        # ETAPA 10.5: Preencher Remetente se for Viagem Extra
        pause_event.wait()
        viagem_extra = dados_linha.get("Viagem extra", "Não")
        
        if viagem_extra == "Sim":
            log_callback(f"[F5] [Item {nro_cotacao}] Etapa 10.5: Viagem extra detectada. Preenchendo Remetente...", "INFO")
            remetente = dados_linha.get("Remetente", "N/A")

            if remetente in ["N/A", ""]:
                motivo_erro = "Viagem extra é 'Sim', mas o valor de 'Remetente' não foi encontrado na planilha."
                log_callback(f"[F5] [Item {nro_cotacao}] ERRO: {motivo_erro}", "ERRO")
                registrar_erro_em_planilha(dados_linha, motivo_erro, log_callback, output_filepath)
                return False

            try:
                input_selector = 'input[name="pesquisa_dados_enderecoRemetenteContrato_id"]'
                button_selector = 'i[name="botaoPesquisa_dados_enderecoRemetenteContrato_id"]'

                log_callback(f"[F5] [Item {nro_cotacao}] Preenchendo campo Remetente com '{remetente}'...", "DEBUG")
                page.fill(input_selector, remetente)
                time.sleep(atraso_etapas)

                log_callback(f"[F5] [Item {nro_cotacao}] Clicando no botão de pesquisa do Remetente...", "DEBUG")
                page.click(button_selector)
                page.wait_for_timeout(500) # Aguarda a pesquisa

            except Error as e:
                motivo_erro = f"Erro ao interagir com o campo 'Remetente'. Detalhe: {e}"
                log_callback(f"[F5] [Item {nro_cotacao}] ERRO: {motivo_erro}", "ERRO")
                registrar_erro_em_planilha(dados_linha, motivo_erro, log_callback, output_filepath)
                return False
        
        time.sleep(atraso_etapas)

        # ETAPA 11: Preencher e Selecionar Destinatário
        pause_event.wait()
        log_callback(f"[F5] [Item {nro_cotacao}] Etapa 11: Preenchendo Destinatário 'logtudo'...", "DEBUG")
        try:
            page.fill('input[name="pesquisa_dados_enderecoDestinatarioContrato_id"]', "logtudo")
            page.click('i[name="botaoPesquisa_dados_enderecoDestinatarioContrato_id"]')
        except TimeoutError:
            motivo_erro = (
                "Timeout: O clique no botão de pesquisa de Destinatário foi bloqueado por um "
                "componente sobreposto (como uma tela de carregamento) e excedeu o tempo limite de espera."
            )
            log_callback(f"[F5] [Item {nro_cotacao}] ERRO: {motivo_erro}", "ERRO")
            registrar_erro_em_planilha(dados_linha, motivo_erro, log_callback, output_filepath)
            return False

        destinatario_selector = 'select[name="dados_enderecoDestinatarioContrato_id"]'
        log_callback(f"[F5] [Item {nro_cotacao}] Aguardando resultados da pesquisa de destinatário...", "DEBUG")
        page.wait_for_selector(f'{destinatario_selector} option[value="1"]', state="attached", timeout=10000)
        log_callback(f"[F5] [Item {nro_cotacao}] Selecionando primeiro destinatário encontrado...", "DEBUG")
        page.select_option(destinatario_selector, value="1")

        time.sleep(atraso_etapas)

        # ETAPA 12: Preencher Data Programada
        pause_event.wait()
        data_pagamento_raw = dados_linha.get("Data pagamento", "DATA NÃO ENCONTRADA")
        log_callback(f"[F5] [Item {nro_cotacao}] Etapa 12: Verificando e preenchendo Data Programada...", "DEBUG")

        if data_pagamento_raw and data_pagamento_raw != "DATA NÃO ENCONTRADA":
            # Garante que a data esteja no formato string dd/mm/aaaa
            if isinstance(data_pagamento_raw, datetime):
                data_pagamento = data_pagamento_raw.strftime('%d/%m/%Y')
            else:
                data_pagamento = str(data_pagamento_raw)

            log_callback(f"[F5] [Item {nro_cotacao}] Preenchendo Data Programada com '{data_pagamento}'.", "DEBUG")

            page.fill('input[name="dados_dataSaldoRepom"]', data_pagamento)
        else:
            motivo_erro = "Data de pagamento não encontrada na planilha."
            log_callback(f"[F5] [Item {nro_cotacao}] ERRO: {motivo_erro} Cancelando item.", "ERRO")
            registrar_erro_em_planilha(dados_linha, motivo_erro, log_callback, output_filepath)
            return False # Sinaliza falha para pular para o próximo item

        time.sleep(atraso_etapas)

        # ETAPA 13: Verificar e confirmar frete mínimo ANTT
        pause_event.wait()
        log_callback(f"[F5] [Item {nro_cotacao}] Etapa 13: Verificando aviso de frete mínimo ANTT...", "DEBUG")

        # Localiza o checkbox específico para a confirmação do frete mínimo ANTT.
        checkbox_locator = page.locator('#confirmacaoFreteMinimo_concorda')

        # Verifica se o checkbox está visível na página, indicando que o aviso foi exibido.
        # Um timeout curto é suficiente, pois a verificação é rápida.
        if checkbox_locator.is_visible(timeout=3000):
            log_callback(f"[F5] [Item {nro_cotacao}] AVISO: Valor do frete menor que o mínimo da ANTT detectado.", "AVISO")
            
            log_callback(f"[F5] [Item {nro_cotacao}] Marcando o checkbox de aceite do frete mínimo.", "DEBUG")
            try:
                # Tenta marcar o checkbox.
                checkbox_locator.check()
                log_callback(f"[F5] [Item {nro_cotacao}] Checkbox de frete mínimo ANTT marcado com sucesso.", "DEBUG")
            except Exception as e:
                # Se falhar, registra o erro e encerra o processamento deste item.
                motivo_erro = f"Não foi possível marcar a confirmação de frete mínimo ANTT: {e}"
                log_callback(f"[F5] [Item {nro_cotacao}] ERRO: {motivo_erro}", "ERRO")
                registrar_erro_em_planilha(dados_linha, motivo_erro, log_callback, output_filepath)
                return False
        else:
            log_callback(f"[F5] [Item {nro_cotacao}] Não foi exibido o aviso de frete mínimo da ANTT.", "DEBUG")

        # ETAPA 14: Marcar Checkbox de confirmação
        pause_event.wait()
        log_callback(f"[F5] [Item {nro_cotacao}] Etapa 14: Marcando checkbox de confirmação NCM...", "DEBUG")
        page.check('input[name="dados_confirmacaoNCMGeral_concorda"]')
        
        time.sleep(atraso_etapas)

        # ETAPA 15: Clicar em "Salvar" para finalizar o contrato
        pause_event.wait()
        log_callback(f"[F5] [Item {nro_cotacao}] Etapa 15: Clicando em 'Salvar' para finalizar o contrato...", "DEBUG")
        
        success_url_prefix = "https://logtudo.e-login.net/versoes/versao5.0/rotinas/c.php?id=trans_conhecimento"
            
        # --- TENTATIVA 1: Salvar Principal ---
        log_callback(f"[F5] [Item {nro_cotacao}] Etapa 15.1: Tentativa inicial de salvar...", "DEBUG")
        page.click('#botao_cadastrar')

        # Give a short moment for client-side errors to appear without navigation
        time.sleep(1) # Small delay to allow DOM to update with error messages

        # --- Verificação de erros específicos após a primeira tentativa de salvar ---
        frete_minimo_error_locator = page.locator('input[name="dados_freteMinimo_valor"].swstatus-input-error')
        motorista_dados_faltantes_error_locator = page.locator('div.rotina-generica.alert-message.error:has-text("Os seguintes campos são obrigatórios")')
        
        specific_error_found = False
        if frete_minimo_error_locator.is_visible():
            motivo_erro = "Erro (Tentativa 1): Campo 'Frete Mínimo' vazio."
            log_callback(f"[F5] [Item {nro_cotacao}] ERRO: {motivo_erro}", "ERRO")
            registrar_erro_em_planilha(dados_linha, motivo_erro, log_callback, output_filepath)
            specific_error_found = True
        
        if motorista_dados_faltantes_error_locator.is_visible():
            error_text = motorista_dados_faltantes_error_locator.inner_text()
            motivo_erro = f"Erro (Tentativa 1): Falta de dados do motorista. Detalhes: {error_text}"
            log_callback(f"[F5] [Item {nro_cotacao}] ERRO: {motivo_erro}", "ERRO")
            registrar_erro_em_planilha(dados_linha, motivo_erro, log_callback, output_filepath)
            specific_error_found = True

        if specific_error_found:
            return False # Já registrou o erro específico
        
        # If no specific error, then wait for navigation
        # Otimização: Em vez de esperar 'networkidle', que pode ser lento,
        # esperamos pela URL de sucesso ou por um elemento que confirme o sucesso.
        try:
            page.wait_for_url(lambda url: "/rotinas/" in url and "/rotinas/formulario" not in url, timeout=60000)
        except Error as e:
            # If navigation times out, it means the save likely failed for another reason
            motivo_erro = f"Erro de Playwright (Tentativa 1): Timeout {e.timeout}ms excedido ao aguardar a URL de sucesso após salvar."
            log_callback(f"[F5] [Item {nro_cotacao}] ERRO: {motivo_erro}", "ERRO")
            registrar_erro_em_planilha(dados_linha, motivo_erro, log_callback, output_filepath)
            return False

        if "/rotinas/" in page.url and "/rotinas/formulario" not in page.url:
            registrar_sucesso_em_planilha(dados_linha, log_callback, output_filepath)
            return True
        # If it reaches here, it means navigation happened but not to the success URL,
        # so it will proceed to CFOP handling.

        # TENTATIVA 2 - CÓDIGO REFATORADO ETAPA CFOP
        cfop_container = page.locator('#COM_RF_confirmacaoPrimeiroUsoCFOP')

        if cfop_container.is_visible(timeout=3000):
            log_callback(f"[F5] [Item {nro_cotacao}] Etapa 15.2: Aviso de CFOP detectado.", "INFO")
            
            try:
                time.sleep(atraso_etapas)
                
                # ABORDAGEM HÍBRIDA (mais robusta)
                radio_locator = page.locator('input[name="dados_conf_primeiroUsoCFOP_comPermissao"][value="S"]')
                
                # Tenta click + dispatch primeiro
                radio_locator.click(force=True, timeout=5000)
                radio_locator.dispatch_event('change')
                
                # Validação: verifica se realmente marcou
                time.sleep(0.5)
                if not radio_locator.is_checked():
                    log_callback(f"[F5] [Item {nro_cotacao}] Click falhou, usando JavaScript...", "DEBUG")
                    page.evaluate('''
                        const radio = document.querySelector('input[name="dados_conf_primeiroUsoCFOP_comPermissao"][value="S"]');
                        radio.checked = true;
                        radio.dispatchEvent(new Event('change', { bubbles: true }));
                    ''')
                
                log_callback(f"[F5] [Item {nro_cotacao}] Radio button CFOP marcado com sucesso.", "DEBUG")
                time.sleep(atraso_etapas)

                log_callback(f"[F5] [Item {nro_cotacao}] Clicando em 'Avançar' após marcar CFOP.", "DEBUG")
                page.click('#botao_avancar')
                time.sleep(atraso_etapas)

                # Re-marcar checkboxes após o pop-up do CFOP
                log_callback(f"[F5] [Item {nro_cotacao}] Re-marcando checkboxes de Frete Mínimo e NCM...", "DEBUG")
                
                # Re-marcar Frete Mínimo (se visível)
                frete_minimo_checkbox = page.locator('#confirmacaoFreteMinimo_concorda')
                if frete_minimo_checkbox.is_visible(timeout=1000):
                    frete_minimo_checkbox.check()
                    log_callback(f"[F5] [Item {nro_cotacao}] Checkbox de Frete Mínimo re-marcado.", "DEBUG")

                # Re-marcar Confirmação NCM
                ncm_checkbox = page.locator('input[name="dados_confirmacaoNCMGeral_concorda"]')
                ncm_checkbox.check()
                log_callback(f"[F5] [Item {nro_cotacao}] Checkbox de Confirmação NCM re-marcado.", "DEBUG")
                
                time.sleep(atraso_etapas)
            
                page.click('#botao_cadastrar') # Click without waiting for navigation yet

                # Give a short moment for client-side errors to appear without navigation
                time.sleep(1) # Small delay to allow DOM to update with error messages

                # --- Verificação de erros específicos após a segunda tentativa de salvar ---
                frete_minimo_error_locator_2 = page.locator('input[name="dados_freteMinimo_valor"].swstatus-input-error')
                motorista_dados_faltantes_error_locator_2 = page.locator('div.rotina-generica.alert-message.error:has-text("Os seguintes campos são obrigatórios")')
                
                specific_error_found = False
                if frete_minimo_error_locator_2.is_visible():
                    motivo_erro = "Erro (Tentativa 2): Campo 'Frete Mínimo' vazio."
                    log_callback(f"[F5] [Item {nro_cotacao}] ERRO: {motivo_erro}", "ERRO")
                    registrar_erro_em_planilha(dados_linha, motivo_erro, log_callback, output_filepath)
                    specific_error_found = True
                
                if motorista_dados_faltantes_error_locator_2.is_visible():
                    error_text = motorista_dados_faltantes_error_locator_2.inner_text()
                    motivo_erro = f"Erro (Tentativa 2): Falta de dados do motorista. Detalhes: {error_text}"
                    log_callback(f"[F5] [Item {nro_cotacao}] ERRO: {motivo_erro}", "ERRO")
                    registrar_erro_em_planilha(dados_linha, motivo_erro, log_callback, output_filepath)
                    specific_error_found = True

                if specific_error_found:
                    return False # Já registrou o erro específico

                # If no specific error, then wait for navigation
                try:
                    page.wait_for_url(lambda url: "/rotinas/" in url and "/rotinas/formulario" not in url, timeout=60000)
                except Error as e:
                    motivo_erro = f"Erro de Playwright (Tentativa 2): Timeout {e.timeout}ms excedido ao aguardar a URL de sucesso após salvar."
                    log_callback(f"[F5] [Item {nro_cotacao}] ERRO: {motivo_erro}", "ERRO")
                    registrar_erro_em_planilha(dados_linha, motivo_erro, log_callback, output_filepath)
                    return False

                if "/rotinas/" in page.url and "/rotinas/formulario" not in page.url:
                    registrar_sucesso_em_planilha(dados_linha, log_callback, output_filepath)
                    return True
                else:
                    # If navigation happened but not to the success URL, and no specific error was found
                    motivo_erro = "Falha ao salvar contrato após tentativa com CFOP e sem erros específicos detectados."
                    log_callback(f"[F5] [Item {nro_cotacao}] ERRO: {motivo_erro}", "ERRO")
                    registrar_erro_em_planilha(dados_linha, motivo_erro, log_callback, output_filepath)
                    return False                    
            except Exception as e:
                motivo_erro = f"Erro ao processar CFOP: {e}"
                log_callback(f"[F5] [Item {nro_cotacao}] ERRO: {motivo_erro}", "ERRO")
                registrar_erro_em_planilha(dados_linha, motivo_erro, log_callback, output_filepath)
                return False

    except Error as e:
        nro_cotacao = dados_linha.get("Nro cotação", "N/A")
        log_callback(f"[F5] Erro de Playwright na Fase 5 (Item {nro_cotacao}): {e}", "ERRO")
        registrar_erro_em_planilha(dados_linha, f"Erro de Playwright: {e}", log_callback, output_filepath)
        return False
    except Exception as e:
        nro_cotacao = dados_linha.get("Nro cotação", "N/A")
        log_callback(f"[F5] Erro inesperado na Fase 5 (Item {nro_cotacao}): {e}", "ERRO")
        import traceback
        log_callback(f"[F5] Traceback Fase 5: {traceback.format_exc()}", "DEBUG")
        registrar_erro_em_planilha(dados_linha, f"Erro inesperado: {e}", log_callback, output_filepath)
        return False
