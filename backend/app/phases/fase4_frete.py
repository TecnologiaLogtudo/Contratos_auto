import threading
import time
from playwright.sync_api import Page, Error
from typing import Callable, Dict
import re
import unicodedata


def _normalizar_texto(texto: str) -> str:
    texto = unicodedata.normalize("NFD", str(texto or ""))
    texto = "".join(char for char in texto if unicodedata.category(char) != "Mn")
    return " ".join(texto.upper().split())


def _opcao_destinatario_tam_para_cidade(option_text: str, cidade: str) -> bool:
    texto_normalizado = _normalizar_texto(option_text)
    cidade_normalizada = _normalizar_texto(cidade)
    padrao_cnpj_tam = r"^\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\s+-\s+TAM LINHAS AEREAS\s+-\s+"

    return (
        re.search(padrao_cnpj_tam, texto_normalizado) is not None
        and f"TAM LINHAS AEREAS - {cidade_normalizada} -" in texto_normalizado
    )


def _alternativas_busca_cidade(cidade: str) -> list[str]:
    alternativas = [cidade]
    if cidade == "J. Pessoa":
        alternativas.extend(["João Pessoa", "Pessoa"])
    return alternativas


def _sincronizar_destinatario_latam(page: Page, nro_cotacao: str, log_callback: Callable, atraso_etapas: float) -> bool:
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

def _formatar_moeda_lactalis(frete_negociado, frete_pagar) -> str:
    def parse_float(v):
        if v is None: return 0.0
        if isinstance(v, (int, float)): return float(v)
        v_str = str(v).replace("R$", "").replace(".", "").replace(",", ".").strip()
        try:
            return float(v_str)
        except ValueError:
            return 0.0
            
    fn_val = parse_float(frete_negociado)
    fp_val = parse_float(frete_pagar)
    
    val_escolhido = fn_val if fn_val > 0 else fp_val
    return f"{val_escolhido:.2f}".replace(".", ",")


def _preencher_campo_se_editavel(
    page: Page,
    selector: str,
    valor: str,
    log_callback: Callable,
    nro_cotacao: str,
    atraso_etapas: float
) -> None:
    """
    Tenta preencher um campo de texto. Se estiver bloqueado para edição (readonly/disabled),
    registra um log de aviso e continua sem lançar erro.
    """
    try:
        locator = page.locator(selector)
        # Espera curta (até 3 segundos) para o campo estar disponível e visível
        locator.wait_for(state="visible", timeout=3000)
        if locator.is_editable():
            locator.fill(valor)
        else:
            log_callback(f"[F4] [Item {nro_cotacao}] Campo '{selector}' bloqueado para edição (readonly/disabled). Ignorando.", "AVISO")
    except Exception as e:
        log_callback(f"[F4] [Item {nro_cotacao}] Não foi possível interagir com o campo '{selector}' (campo bloqueado para edição). Ignorando.", "AVISO")
    time.sleep(atraso_etapas)


def _sincronizar_remetente_destinatario_lactalis(page: Page, nro_cotacao: str, log_callback: Callable, atraso_etapas: float) -> bool:
    try:
        log_callback(f"[F4] [Item {nro_cotacao}] Aplicando regra de destinatário LACTALIS...", "DEBUG")
        
        # 1. Remetente: Pesquisar 'Lactalis'
        page.fill('input[name="pesquisa_enderecoRemetente_id"]', 'Lactalis')
        time.sleep(atraso_etapas)
        page.click('i[name="botaoPesquisa_enderecoRemetente_id"]')
        
        remetente_selector = 'select[name="dados_enderecoRemetente_id"]'
        page.wait_for_selector(f'{remetente_selector} option[value]:not([value=""])', state='attached', timeout=10000)
        time.sleep(atraso_etapas)
        
        # Selecionar '43.340.312/0006-61...'
        options_remetente = page.locator(remetente_selector).locator("option").all()
        remetente_value = None
        for opt in options_remetente:
            text = opt.inner_text().strip()
            if "43.340.312/0006-61" in text:
                remetente_value = opt.get_attribute("value")
                break
        
        if remetente_value:
            page.select_option(remetente_selector, value=remetente_value)
            log_callback(f"[F4] [Item {nro_cotacao}] Remetente LACTALIS selecionado com sucesso.", "INFO")
        else:
            log_callback(f"[F4] [Item {nro_cotacao}] ERRO: Remetente LACTALIS não encontrado nas opções.", "ERRO")
            return False
            
        time.sleep(atraso_etapas)

        # 2. Destinatário: Pesquisar 'Logtudo'
        page.fill('input[name="pesquisa_enderecoDestinatario_id"]', 'Logtudo')
        time.sleep(atraso_etapas)
        page.click('i[name="botaoPesquisa_enderecoDestinatario_id"]')
        
        destinatario_selector = 'select[name="dados_enderecoDestinatario_id"]'
        page.wait_for_selector(f'{destinatario_selector} option[value]:not([value=""])', state='attached', timeout=10000)
        time.sleep(atraso_etapas)
        
        options_destinatario = page.locator(destinatario_selector).locator("option").all()
        destinatario_value = None
        for opt in options_destinatario:
            text = opt.inner_text().strip()
            if "20.511.709/0001-69" in text:
                destinatario_value = opt.get_attribute("value")
                break
                
        if destinatario_value:
            page.select_option(destinatario_selector, value=destinatario_value)
            log_callback(f"[F4] [Item {nro_cotacao}] Destinatário LOGTUDO selecionado com sucesso.", "INFO")
        else:
            log_callback(f"[F4] [Item {nro_cotacao}] ERRO: Destinatário LOGTUDO não encontrado nas opções.", "ERRO")
            return False

        return True
    except Exception as e:
        log_callback(f"[F4] [Item {nro_cotacao}] ERRO na Etapa 1 (Remetente/Destinatário LACTALIS): {e}", "ERRO")
        return False


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

        # ETAPA 1: Destinatário (buscar pelo CNPJ do Remetente e sincronizar)
        pause_event.wait()
        
        remetente_planilha = dados_linha.get("Remetente", "").upper()

        if "LACTALIS" in remetente_planilha:
            sucesso_etapa1 = _sincronizar_remetente_destinatario_lactalis(page, nro_cotacao, log_callback, atraso_etapas)
        else:
            # Fallback default (TAM)
            sucesso_etapa1 = _sincronizar_destinatario_latam(page, nro_cotacao, log_callback, atraso_etapas)

        if not sucesso_etapa1:
            return False

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

        # ETAPA 7: Selecionar Composição do Frete
        pause_event.wait()
        log_callback(f"[F4] [Item {nro_cotacao}] Etapa 7: Selecionando Composição do Frete...", "DEBUG")
        if "LACTALIS" in remetente_planilha:
            log_callback(f"[F4] [Item {nro_cotacao}] Remetente Lactalis detectado. Selecionando Cotação Varejo (120)...", "DEBUG")
            page.select_option('select[name="dados_regraFrete_id"]', value="120")
        else:
            log_callback(f"[F4] [Item {nro_cotacao}] Selecionando Não realiza cálculos (40)...", "DEBUG")
            page.select_option('select[name="dados_regraFrete_id"]', value="40")
        time.sleep(atraso_etapas)

        # ETAPA 8: Apagar valores
        pause_event.wait()
        log_callback(f"[F4] [Item {nro_cotacao}] Etapa 8: Zerando valores de frete...", "DEBUG")
        _preencher_campo_se_editavel(page, 'input[name="dados_valorFrete"]', "0,00", log_callback, nro_cotacao, atraso_etapas)
        _preencher_campo_se_editavel(page, 'input[name="dados_baseCalculo"]', "0,00", log_callback, nro_cotacao, atraso_etapas)
        _preencher_campo_se_editavel(page, 'input[name="dados_aliquota"]', "0,00", log_callback, nro_cotacao, atraso_etapas)
        _preencher_campo_se_editavel(page, 'input[name="dados_valorICMS"]', "0,00", log_callback, nro_cotacao, atraso_etapas)
        _preencher_campo_se_editavel(page, 'input[name="dados_valoresOutros"]', "0,00", log_callback, nro_cotacao, atraso_etapas)
        _preencher_campo_se_editavel(page, 'input[name="dados_totalPrestacao"]', "0,00", log_callback, nro_cotacao, atraso_etapas)

        # ETAPA 8.5: Regra Lactalis - Preencher Frete Terceiros
        if "LACTALIS" in remetente_planilha:
            pause_event.wait()
            log_callback(f"[F4] [Item {nro_cotacao}] Etapa 8.5: Preenchendo Frete Terceiros para Lactalis...", "DEBUG")
            frete_negociado = dados_linha.get("Frete negociado")
            frete_pagar = dados_linha.get("Frete a pagar")
            
            valor_moeda = _formatar_moeda_lactalis(frete_negociado, frete_pagar)
            log_callback(f"[F4] [Item {nro_cotacao}] Valor selecionado para frete terceiros: R$ {valor_moeda}", "DEBUG")
            _preencher_campo_se_editavel(page, 'input[name="dados_outrosValores[freteterceiros]"]', valor_moeda, log_callback, nro_cotacao, atraso_etapas)

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
            
            obs_selector = 'textarea[name="dados_observacaoPV"]'
            try:
                # Clica para dar foco e disparar o onfocus="montaObsPV();"
                page.click(obs_selector)
                page.wait_for_timeout(500) # Aguarda um pouco para o script da página rodar
                
                # Preenche o valor
                page.fill(obs_selector, observacao)
                
                # Dispara eventos manualmente para garantir que a página reconheça a mudança
                page.locator(obs_selector).dispatch_event('input')
                page.locator(obs_selector).dispatch_event('change')
                
                log_callback(f"[F4] [Item {nro_cotacao}] Observação preenchida e eventos disparados.", "DEBUG")
            except Error as e:
                log_callback(f"[F4] [Item {nro_cotacao}] AVISO: Erro ao preencher observação: {e}", "AVISO")
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
