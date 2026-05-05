import threading
import time
from playwright.sync_api import Page, Error
from typing import Callable, Dict

def preencher_frete(
    page: Page, 
    dados_linha: Dict[str, str], 
    log_callback: Callable[[str, str], None],
    pause_event: threading.Event,
    output_filepath: str, # Adicionado para consistência, mesmo que não usado aqui.
    atraso_etapas: float
) -> bool:
    """
    Executa os passos de preenchimento da Fase 4 (Dados do Frete).
    """
    try:
        nro_cotacao = dados_linha.get("Nro cotação", "N/A")
        cidade = dados_linha.get("Cidade", "N/A")
        placa = dados_linha.get("Placa", "N/A")
        nome_motorista = dados_linha.get("Nome", "NOME NÃO ENCONTRADO")
        log_callback(f"[F4] [Item {nro_cotacao}] --- INÍCIO: DADOS DO FRETE ---", "FASE")

        # ETAPA 1: Destinatário "Diversos"
        pause_event.wait()
        log_callback(f"[F4] [Item {nro_cotacao}] Etapa 1: Preenchendo Destinatário 'Diversos'...", "DEBUG")
        page.fill('input[name="pesquisa_enderecoDestinatario_id"]', "Diversos")
        time.sleep(atraso_etapas)
        page.click('i[name="botaoPesquisa_enderecoDestinatario_id"]')
        page.wait_for_timeout(500)
        time.sleep(atraso_etapas)

        # ETAPA 2: Cidade (da planilha)
        pause_event.wait()
        log_callback(f"[F4] [Item {nro_cotacao}] Etapa 2: Preenchendo Cidade '{cidade}'...", "DEBUG")

        def _perform_city_search_and_selection(city_name: str) -> bool:
            try:
                page.fill('input[name="pesquisa_cMunIni"]', city_name)
                time.sleep(atraso_etapas)
                page.click('i[name="botaoPesquisa_cMunIni"]')
                
                cidade_selector = 'select[name="dados_cMunIni"]';
                page.wait_for_selector(f'{cidade_selector} option[value]:not([value=""])', state='attached', timeout=10000)
                
                options = page.locator(cidade_selector).locator("option").all()
                
                all_option_texts = [opt.inner_text().strip() for opt in options if opt.inner_text().strip()]
                log_callback(f"[F4] [Item {nro_cotacao}] Opções de cidade encontradas para '{city_name}': {all_option_texts}", "DEBUG")

                if any("Nenhum registro encontrado!" in opt.inner_text() for opt in options):
                    return False # City not found

                cidade_selecionada = False
                selected_value = None
                selected_option_text = ""

                for opt in options:
                    option_text = opt.inner_text().strip()
                    if option_text == city_name:
                        selected_value = opt.get_attribute("value")
                        selected_option_text = option_text
                        break
                
                if not selected_value:
                    for opt in options:
                        option_text = opt.inner_text().strip()
                        if option_text.startswith(city_name):
                            selected_value = opt.get_attribute("value")
                            selected_option_text = option_text
                            break

                if selected_value:
                    page.select_option(cidade_selector, value=selected_value)
                    log_callback(f"[F4] [Item {nro_cotacao}] Cidade '{selected_option_text}' selecionada com sucesso (valor: {selected_value}).", "INFO")
                    cidade_selecionada = True
                
                return cidade_selecionada

            except Exception as e:
                log_callback(f"[F4] [Item {nro_cotacao}] ERRO durante a busca/seleção da cidade '{city_name}': {e}", "ERRO")
                return False

        cidade_encontrada = False
        
        if _perform_city_search_and_selection(cidade):
            cidade_encontrada = True
        elif cidade == "J. Pessoa":
            log_callback(f"[F4] [Item {nro_cotacao}] AVISO: Cidade 'J. Pessoa' não encontrada. Tentando 'João Pessoa'...", "AVISO")
            if _perform_city_search_and_selection("João Pessoa"):
                cidade_encontrada = True
            else:
                log_callback(f"[F4] [Item {nro_cotacao}] AVISO: Cidade 'João Pessoa' não encontrada. Tentando 'Pessoa'...", "AVISO")
                if _perform_city_search_and_selection("Pessoa"):
                    cidade_encontrada = True
        
        if not cidade_encontrada:
            log_callback(f"[F4] [Item {nro_cotacao}] ERRO: Não foi possível encontrar a cidade '{cidade}', 'João Pessoa' ou 'Pessoa' após as tentativas.", "ERRO")
            return False
        
        # ETAPA 3: Natureza da Operação (clicar em pesquisar)
        pause_event.wait()
        log_callback(f"[F4] [Item {nro_cotacao}] Etapa 3: Clicando em Pesquisar Natureza...", "DEBUG")
        page.click('i[name="botaoPesquisa_cfops_id"]')
        page.wait_for_timeout(500)
        time.sleep(atraso_etapas)

        natureza_selector = 'select[name="dados_cfops_id"]'
        if not page.input_value(natureza_selector):
            log_callback(f"[F4] [Item {nro_cotacao}] Natureza da operação não preenchida. Selecionando valor padrão '5352'...", "AVISO")
            page.select_option(natureza_selector, value="1")
            time.sleep(atraso_etapas)

        # ETAPA 4: Motorista (Placa da planilha)
        pause_event.wait()
        if not placa or placa == "PLACA NÃO ENCONTRADA":
            log_callback(f"[F4] [Item {nro_cotacao}] ERRO: Placa não fornecida ou inválida na planilha ('{placa}').", "ERRO")
            return False
        
        try:
            log_callback(f"[F4] [Item {nro_cotacao}] Etapa 4: Preenchendo Placa '{placa}'...", "DEBUG")
            page.fill('input[name="pesquisa_dados_motorista_id"]', placa)
            time.sleep(atraso_etapas)
            page.click('i[name="botaoPesquisa_dados_motorista_id"]')
            
            motorista_selector = 'select[name="dados_motorista_id"]'
            
            # Espera até que a opção "Carregando dados ..." desapareça,
            # ou que uma opção com valor não vazio apareça.
            # Isso garante que os dados foram carregados ou que a mensagem de "não encontrado" apareceu.
            try:
                page.wait_for_selector(
                    f'{motorista_selector} option:not(:text("Carregando dados ..."))',
                    state='attached',
                    timeout=15000 # Aumentar o timeout para dar mais tempo para carregar
                )
            except Error: # Changed from PlaywrightError to Error
                # Se o timeout ocorrer aqui, significa que a opção "Carregando dados..." nunca desapareceu
                # ou nenhuma outra opção apareceu. Isso é um erro.
                log_callback(f"[F4] [Item {nro_cotacao}] ERRO: Timeout ao esperar o carregamento das opções de motorista para a placa '{placa}'.", "ERRO")
                return False
            
            options = page.locator(motorista_selector).locator("option").all()
            
            # Itera sobre as opções para verificar o texto
            option_texts = [opt.inner_text() for opt in options]
            log_callback(f"[F4] [Item {nro_cotacao}] Opções de motorista encontradas: {option_texts}", "DEBUG")

            # Verifica se a mensagem "Nenhum registro encontrado!" está presente
            if any("Nenhum registro encontrado!" in text for text in option_texts):
                log_callback(f"[F4] [Item {nro_cotacao}] ERRO: Placa '{placa}' não encontrada no sistema (Nenhum registro encontrado!).", "ERRO")
                return False

            # Verifica se alguma opção válida foi retornada e selecionada
            selected_value = page.input_value(motorista_selector)
            if not selected_value:
                # Se nada estiver pré-selecionado, pode ser um problema.
                # Vamos tentar selecionar a primeira opção válida, se houver.
                valid_options = [opt for opt in options if opt.get_attribute("value")]
                if valid_options:
                    first_valid_value = valid_options[0].get_attribute("value")
                    page.select_option(motorista_selector, value=first_valid_value)
                    log_callback(f"[F4] [Item {nro_cotacao}] Motorista selecionado para a placa '{placa}'.", "INFO")
                else:
                    log_callback(f"[F4] [Item {nro_cotacao}] ERRO: Placa '{placa}' não retornou motoristas válidos.", "ERRO")
                    return False
            else:
                log_callback(f"[F4] [Item {nro_cotacao}] Motorista encontrado e pré-selecionado para a placa '{placa}'.", "INFO")

        except Exception as e:
            log_callback(f"[F4] [Item {nro_cotacao}] ERRO ao buscar ou validar motorista pela placa '{placa}': {e}", "ERRO")
            return False

        # ETAPA 5: Selecionar "A - Transporte rodoviário de carga"
        pause_event.wait()
        log_callback(f"[F4] [Item {nro_cotacao}] Etapa 5: Selecionando Tipo de Transporte...", "DEBUG")
        page.select_option('select[name="dados_freteMinimo_tabela"]', value="A")
        time.sleep(atraso_etapas)

        # ETAPA 6: Selecionar "5 - Carga Geral"
        pause_event.wait()
        log_callback(f"[F4] [Item {nro_cotacao}] Etapa 6: Selecionando Tipo de Carga...", "DEBUG")
        page.select_option('select[name="dados_freteMinimo_tipoCarga"]', value="GER")
        time.sleep(atraso_etapas)

        # ETAPA 7: Selecionar "Não realiza cálculos"
        pause_event.wait()
        log_callback(f"[F4] [Item {nro_cotacao}] Etapa 7: Selecionando Composição do Frete...", "DEBUG")
        page.select_option('select[name="dados_regraFrete_id"]', value="40")
        time.sleep(atraso_etapas)

        # ETAPA 8: Apagar valores
        pause_event.wait()
        log_callback(f"[F4] [Item {nro_cotacao}] Etapa 8: Zerando valores de frete...", "DEBUG")
        page.fill('input[name="dados_valorFrete"]', "0,00")
        time.sleep(atraso_etapas)
        page.fill('input[name="dados_baseCalculo"]', "0,00")
        time.sleep(atraso_etapas)
        page.fill('input[name="dados_aliquota"]', "0,00")
        time.sleep(atraso_etapas)
        page.fill('input[name="dados_valorICMS"]', "0,00")
        time.sleep(atraso_etapas)                
        page.fill('input[name="dados_valoresOutros"]', "0,00")
        time.sleep(atraso_etapas)
        page.fill('input[name="dados_totalPrestacao"]', "0,00")
        time.sleep(atraso_etapas)

        # ETAPA 9: Preencher campo de observação
        pause_event.wait()
        log_callback(f"[F4] [Item {nro_cotacao}] Etapa 9: Preenchendo Observação...", "DEBUG")
        
        partes_obs = []
        if nome_motorista != "NOME NÃO ENCONTRADO":
            partes_obs.append(nome_motorista)
        if placa != "PLACA NÃO ENCONTRADA":
            partes_obs.append(placa)

        if partes_obs:
            observacao = " - ".join(partes_obs)
            log_callback(f"[F4] [Item {nro_cotacao}] Preenchendo observação com: '{observacao}'", "DEBUG")
            page.fill('textarea[name="dados_observacaoPV"]', observacao)
        else:
            log_callback(f"[F4] [Item {nro_cotacao}] Nome e placa não encontrados. Pulando observação.", "AVISO")
        time.sleep(atraso_etapas)

        # ETAPA 10: Marcar caixa "Ciente... valor zerado"
        pause_event.wait()
        log_callback(f"[F4] [Item {nro_cotacao}] Etapa 10: Marcando Checkbox 'Ciente Valor Zerado'...", "DEBUG")
        page.check('input[name="dados_conf_CTeValorZerado[]"]')
        time.sleep(atraso_etapas)

        # ETAPA 11: Clicar em "Avançar" para ir para a Fase 5
        pause_event.wait()
        log_callback(f"[F4] [Item {nro_cotacao}] Etapa 11: Clicando em 'Avançar' para a Fase 5...", "DEBUG")
        botao_avancar_selector = '#botao_avancar'
        primeiro_campo_fase5_selector = 'input[name="dados_dtFimViagem"]'
        page.click(botao_avancar_selector)
        log_callback(f"[F4] [Item {nro_cotacao}] Aguardando transição para a Fase 5...", "DEBUG")
        page.wait_for_selector(primeiro_campo_fase5_selector, state="visible", timeout=30000)

        log_callback(f"[F4] [Item {nro_cotacao}] Fase concluída com sucesso.", "SUCESSO")
        return True

    except Error as e:
        nro_cotacao = dados_linha.get("Nro cotação", "N/A")
        log_callback(f"[F4] Erro de Playwright na Fase 4 (Item {nro_cotacao}): {e}", "ERRO")
        return False
    except Exception as e:
        nro_cotacao = dados_linha.get("Nro cotação", "N/A")
        log_callback(f"[F4] Erro inesperado na Fase 4 (Item {nro_cotacao}): {e}", "ERRO")
        import traceback
        log_callback(f"[F4] Traceback Fase 4: {traceback.format_exc()}", "DEBUG")
        return False
