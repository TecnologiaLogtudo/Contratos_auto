import re
import time
from datetime import datetime
from typing import Callable, Dict
from playwright.sync_api import Page
from .base_company import BaseCompany

class LactalisBaseCompany(BaseCompany):
    def match(self, remetente: str) -> bool:
        rem = remetente.lower()
        return "lactalis" in rem or "43.340.312" in rem or "43340312" in rem

    def require_data_pagamento(self) -> bool:
        return False

    def require_validade(self) -> bool:
        return True

    def get_termo_busca_perfil(self, cidade_planilha: str) -> str:
        return "lactalis BA"

    def get_valor_km(self, dados_km: str) -> str:
        return "1"

    def get_ncm_pesquisa(self) -> str:
        return "0403"

    def get_ncm_valor(self) -> str:
        return "0403."

class LactalisDiariaParadaCompany(LactalisBaseCompany):
    def match(self, remetente: str) -> bool:
        rem = remetente.lower()
        return super().match(remetente) and not any(kw in rem for kw in ["pernoite", "diaria em rota", "diaria no cliente", "diaria garantida"])

    def match_cotacao_opcao(self, option_text: str, nro_cotacao: str) -> bool:
        return option_text.strip().startswith(f"{nro_cotacao} /") and "lactalis" in option_text.lower()

    def format_cotacao_erro_msg(self, target_option_prefix: str) -> str:
        return f"'{target_option_prefix}' contendo 'Lactalis'"

    def get_complemento_pedido(self, nro_cotacao_item: str) -> str:
        return "DIARIA PARADO"

    def sincronizar_remetente_destinatario(
        self, page: Page, nro_cotacao: str, log_callback: Callable, atraso_etapas: float
    ) -> bool:
        try:
            log_callback(f"[F4] [Item {nro_cotacao}] Aplicando regra de destinatário LACTALIS...", "DEBUG")
            
            # 1. Remetente: Pesquisar '43.340.312/0006-61'
            page.fill('input[name="pesquisa_enderecoRemetente_id"]', '43.340.312/0006-61')
            time.sleep(atraso_etapas)
            page.click('i[name="botaoPesquisa_enderecoRemetente_id"]')
            
            remetente_selector = 'select[name="dados_enderecoRemetente_id"]'
            page.wait_for_selector(f'{remetente_selector} option[value]:not([value=""])', state='attached', timeout=10000)
            time.sleep(atraso_etapas)
            
            options_remetente = page.locator(remetente_selector).locator("option").all()
            remetente_value = None
            for opt in options_remetente:
                val = opt.get_attribute("value")
                if val and val != "":
                    remetente_value = val
                    break
            
            if remetente_value:
                page.select_option(remetente_selector, value=remetente_value)
                log_callback(f"[F4] [Item {nro_cotacao}] Remetente LACTALIS selecionado com sucesso.", "INFO")
            else:
                log_callback(f"[F4] [Item {nro_cotacao}] ERRO: Remetente LACTALIS não encontrado nas opções.", "ERRO")
                return False
                
            time.sleep(atraso_etapas)

            # 2. Destinatário: Pesquisar '20.511.709/0001-69'
            page.fill('input[name="pesquisa_enderecoDestinatario_id"]', '20.511.709/0001-69')
            time.sleep(atraso_etapas)
            page.click('i[name="botaoPesquisa_enderecoDestinatario_id"]')
            
            destinatario_selector = 'select[name="dados_enderecoDestinatario_id"]'
            page.wait_for_selector(f'{destinatario_selector} option[value]:not([value=""])', state='attached', timeout=10000)
            time.sleep(atraso_etapas)
            
            options_destinatario = page.locator(destinatario_selector).locator("option").all()
            destinatario_value = None
            for opt in options_destinatario:
                val = opt.get_attribute("value")
                if val and val != "":
                    destinatario_value = val
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

    def get_regra_frete_id(self) -> str:
        return "120"  # Cotação Varejo (120)

    def _formatar_moeda_lactalis(self, frete_negociado, frete_pagar) -> str:
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

    def preencher_frete_terceiros(
        self, page: Page, dados_linha: Dict[str, str], log_callback: Callable, nro_cotacao: str, atraso_etapas: float
    ) -> None:
        frete_negociado = dados_linha.get("Frete negociado")
        frete_pagar = dados_linha.get("Frete a pagar")
        
        valor_moeda = self._formatar_moeda_lactalis(frete_negociado, frete_pagar)
        log_callback(f"[F4] [Item {nro_cotacao}] Valor selecionado para frete terceiros: R$ {valor_moeda}", "DEBUG")
        self._preencher_campo_se_editavel(page, 'input[name="dados_outrosValores[freteterceiros]"]', valor_moeda, log_callback, nro_cotacao, atraso_etapas)

    # Fase 5
    def get_fim_viagem(self, page: Page, dados_linha: Dict[str, str], data_pagamento: str, log_callback: Callable) -> str | None:
        try:
            data_emissao = page.input_value('input[name="dados_dtEmissaoRF"]')
            nro_cotacao = dados_linha.get("Nro cotação", "N/A")
            log_callback(f"[F5] [Item {nro_cotacao}] Regra Lactalis: Usando Data de Emissão '{data_emissao}' para 'Fim viagem'.", "DEBUG")
            return data_emissao
        except Exception as e:
            nro_cotacao = dados_linha.get("Nro cotação", "N/A")
            log_callback(f"[F5] [Item {nro_cotacao}] ERRO ao obter data de emissão: {e}", "ERRO")
            return None

    def get_observacao(self, dados_linha: Dict[str, str]) -> str:
        data_validade_raw = dados_linha.get("Validade", "")
        if isinstance(data_validade_raw, datetime):
            data_str = data_validade_raw.strftime('%d/%m/%Y')
        else:
            data_str = str(data_validade_raw)
        return f"DIARIA PARADA {data_str}"

    def get_data_programada(self, dados_linha: Dict[str, str], data_pagamento: str, log_callback: Callable) -> str | None:
        validade_raw = dados_linha.get("Validade")
        nro_cotacao = dados_linha.get("Nro cotação", "N/A")
        return self._calcular_data_programada_lactalis(validade_raw, nro_cotacao, log_callback)

    def _calcular_data_programada_lactalis(self, validade_raw: str, nro_cotacao: str, log_callback: Callable) -> str | None:
        if validade_raw and str(validade_raw).strip():
            try:
                if isinstance(validade_raw, datetime):
                    val_date = validade_raw
                else:
                    match = re.search(r'(\d{2})[-/](\d{2})[-/](\d{4})', str(validade_raw))
                    if match:
                        val_date = datetime(int(match.group(3)), int(match.group(2)), int(match.group(1)))
                    else:
                        raise ValueError("Formato desconhecido")
                        
                novo_mes = val_date.month + 1
                novo_ano = val_date.year
                if novo_mes > 12:
                    novo_mes = 1
                    novo_ano += 1
                    
                novo_dia = 5 if val_date.day <= 15 else 20
                data_final = f"{novo_dia:02d}/{novo_mes:02d}/{novo_ano}"
                log_callback(f"[F5] [Item {nro_cotacao}] Regra Lactalis aplicada: Validade {val_date.strftime('%d/%m/%Y')} -> Programada {data_final}.", "DEBUG")
                return data_final
            except Exception as e:
                log_callback(f"[F5] [Item {nro_cotacao}] AVISO: Falha ao calcular Lactalis pela Validade '{validade_raw}'. Erro: {e}", "AVISO")
                return None
        return None

class LactalisSpecialBaseCompany(LactalisBaseCompany):
    def preparar_dados_cotacao(self, page: Page, dados_linha: Dict[str, str], log_callback: Callable, atraso_etapas: float) -> bool:
        try:
            nro_cotacao = dados_linha.get("Nro cotação", "N/A")
            log_callback(f"[Prep] [Item {nro_cotacao}] Acessando listagem de cotações para extrair metadados...", "DEBUG")
            
            # Acessa a página de Cotações
            page.goto("https://logtudo.e-login.net/versoes/versao5.0/rotinas/c.php?id=transp_cotacoesFrete")
            time.sleep(atraso_etapas)
            
            # Tenta abrir filtros se fechados
            try:
                page.locator(".fa.fa-chevron-up").click(timeout=2000)
            except Exception:
                pass

            # Filtra pelo número da cotação (que é o Ravex na planilha)
            page.fill('input[name="busca_nro"]', str(nro_cotacao))
            time.sleep(atraso_etapas)
            page.click('button:has-text("Filtrar")')
            time.sleep(atraso_etapas)
            
            checkbox_selector = 'input[type="checkbox"][name="dados_selecionados[]"]'
            page.wait_for_selector(checkbox_selector, timeout=10000)
            
            id_val = page.locator(checkbox_selector).first.get_attribute("value")
            if not id_val:
                log_callback(f"[Prep] [Item {nro_cotacao}] ERRO: Não foi possível obter o ID da cotação.", "ERRO")
                return False
                
            log_callback(f"[Prep] [Item {nro_cotacao}] Cotação encontrada com ID interno {id_val}. Abrindo detalhes...", "DEBUG")
            
            # Acessa o formulário de detalhes da Cotação
            detail_url = f"https://logtudo.e-login.net/versoes/versao5.0/rotinas/formulario.php?pop=&detail=&rotina=transp_cotacoesFrete&chave=&OP=O3&id={id_val}"
            page.goto(detail_url)
            time.sleep(atraso_etapas)
            
            # 1. Extrai o número do pedido real do cliente (dados_nroPedidoCliente)
            nro_pedido = page.input_value('input[name="dados_nroPedidoCliente"]')
            if not nro_pedido:
                log_callback(f"[Prep] [Item {nro_cotacao}] ERRO: Nº Pedido Cliente não encontrado nos detalhes da cotação.", "ERRO")
                return False
                
            log_callback(f"[Prep] [Item {nro_cotacao}] Nº Pedido Cliente extraído: '{nro_pedido}'", "DEBUG")
            dados_linha["extracted_nro_pedido"] = nro_pedido
            
            # 2. Extrai o texto da Observação Interna
            obs_interna = ""
            for selector in ['textarea[name="dados_observacaoInterna"]', 'textarea[name="dados_obsInterna"]', 'textarea[name="dados_observacoesInternas"]']:
                try:
                    if page.locator(selector).is_visible():
                        obs_interna = page.locator(selector).input_value()
                        if obs_interna:
                            break
                except Exception:
                    continue
                    
            if not obs_interna:
                try:
                    textareas = page.locator('textarea').all()
                    for ta in textareas:
                        val = ta.input_value()
                        if "nf-" in val.lower():
                            obs_interna = val
                            break
                except Exception:
                    pass
                    
            if not obs_interna:
                log_callback(f"[Prep] [Item {nro_cotacao}] ERRO: Campo Observação Interna não encontrado ou vazio na cotação.", "ERRO")
                return False
                
            log_callback(f"[Prep] [Item {nro_cotacao}] Observação Interna extraída com sucesso.", "DEBUG")
            dados_linha["extracted_obs_interna"] = obs_interna
            
            # Garimpa o número da Nota Fiscal (NF) do texto
            nf_match = re.search(r'nf-(\d+)', obs_interna, re.IGNORECASE)
            if not nf_match:
                log_callback(f"[Prep] [Item {nro_cotacao}] ERRO: Número de NF (nf-XXXX) não encontrado na Observação Interna: '{obs_interna}'", "ERRO")
                return False
            nf_val = nf_match.group(1)
            log_callback(f"[Prep] [Item {nro_cotacao}] NF extraída: '{nf_val}'", "DEBUG")
            dados_linha["extracted_nf"] = nf_val
            
            # 3. Clica na aba Conhecimentos
            page.get_by_role("link", name="Conhecimentos").click()
            time.sleep(atraso_etapas)
            
            # 4. Clica em adicionar Conhecimento
            page.locator('[id="_boop"] > a').first.click()
            time.sleep(atraso_etapas)
            
            # 5. Seleciona "Preenchimento Manual"
            try:
                page.locator('div').filter(has_text="Preenchimento Manual").nth(5).click(timeout=5000)
            except Exception:
                log_callback("[Prep] Aviso: clique por index na listagem falhou. Tentando por texto direto...", "DEBUG")
                page.get_by_text("Preenchimento Manual").first.click()
            time.sleep(atraso_etapas)
            
            log_callback(f"[Prep] [Item {nro_cotacao}] Transição com sucesso para o formulário de Conhecimento.", "DEBUG")
            return True
            
        except Exception as e:
            log_callback(f"[Prep] [Item {nro_cotacao}] Falha na preparação dos dados da cotação: {e}", "ERRO")
            import traceback
            log_callback(f"[Prep] Traceback: {traceback.format_exc()}", "DEBUG")
            return False

    def match_cotacao_opcao(self, option_text: str, nro_cotacao: str) -> bool:
        return option_text.strip().startswith(f"{nro_cotacao} /")

    def format_cotacao_erro_msg(self, target_option_prefix: str) -> str:
        return f"'{target_option_prefix}'"

    def get_complemento_pedido(self, nro_cotacao_item: str) -> str | None:
        # De acordo com o codegen da Lactalis Pernoite/Diária Garantida, o complemento não é preenchido
        return None

    def executar_pesquisa_cotacao(
        self,
        page: Page,
        dados_linha: Dict[str, str],
        nro_cotacao: str,
        log_callback: Callable,
        atraso_etapas: float,
        output_filepath: str
    ) -> bool:
        from ..phases.fase3_preenchimento import registrar_erro_em_planilha
        try:
            nro_pedido = dados_linha.get("extracted_nro_pedido")
            if not nro_pedido:
                log_callback("[F3] ERRO: Nº Pedido Cliente não extraído na preparação.", "ERRO")
                return False
                
            log_callback(f"[F3] Pesquisando Pedido Cliente '{nro_pedido}'...", "DEBUG")
            
            # Pesquisa o número do pedido real extraído
            page.fill('input[name="pesquisa_pedidos_id"]', str(nro_pedido))
            time.sleep(atraso_etapas)
            page.click('i[name="botaoPesquisa_pedidos_id"]')
            page.wait_for_timeout(500)
            time.sleep(atraso_etapas)
            
            select_locator = page.locator('select[name="dados_pedidos_id"]')
            try:
                select_locator.wait_for(timeout=5000)
                options = select_locator.locator("option").all()
                if any("Nenhum registro encontrado!" in opt.inner_text() for opt in options):
                    motivo_erro = f"Nenhum registro de cotação encontrado no select para o pedido '{nro_pedido}'."
                    log_callback(f"[F3] {motivo_erro}", "ERRO")
                    registrar_erro_em_planilha(dados_linha, motivo_erro, log_callback, output_filepath)
                    return False
                    
                correct_option_value = None
                target_prefix = f"{nro_pedido} /"
                for opt in options:
                    opt_text = opt.inner_text()
                    if opt_text.strip().startswith(target_prefix):
                        correct_option_value = opt.get_attribute("value")
                        break
                        
                if correct_option_value:
                    select_locator.select_option(value=correct_option_value)
                    log_callback(f"[F3] Opção de cotação '{nro_pedido}' selecionada com sucesso.", "INFO")
                else:
                    log_callback(f"[F3] Aviso: Opção com prefixo '{target_prefix}' não encontrada. Deixando seleção padrão.", "AVISO")
            except Exception as e_sel:
                log_callback(f"[F3] Aviso ao verificar select: {e_sel}. Continuando...", "DEBUG")
                
            # Pesquisa a Nota Fiscal (NF) extraída
            nf_val = dados_linha.get("extracted_nf")
            if nf_val:
                log_callback(f"[F3] Pesquisando Nota Fiscal '{nf_val}'...", "DEBUG")
                page.fill('#pswobj3', str(nf_val))
                time.sleep(atraso_etapas)
                page.click('.swrepp > td > em > .fa-solid')
                time.sleep(atraso_etapas)
            else:
                log_callback("[F3] ERRO: Número de NF não extraído na preparação.", "ERRO")
                return False
                
            return True
        except Exception as e:
            motivo_erro = f"Falha na pesquisa de cotação/NF da Lactalis Especial: {e}"
            log_callback(f"[F3] ERRO: {motivo_erro}", "ERRO")
            registrar_erro_em_planilha(dados_linha, motivo_erro, log_callback, output_filepath)
            return False

    def sincronizar_remetente_destinatario(
        self, page: Page, nro_cotacao: str, log_callback: Callable, atraso_etapas: float
    ) -> bool:
        # Ao abrir o conhecimento a partir da cotação nos detalhes,
        # o sistema já preenche automaticamente o remetente e destinatário
        log_callback(f"[F4] [Item {nro_cotacao}] Conhecimento aberto via cotação detalhe. Remetente e Destinatário já preenchidos.", "INFO")
        return True

    def get_regra_frete_id(self) -> str:
        # Conforme o codegen, a regra do frete não é alterada (mantém padrão ou Não realiza cálculo)
        return "40"

    def get_observacao_pv(self, dados_linha: Dict[str, str], nro_cotacao: str) -> str:
        # A observação PV deve ser preenchida com o número da cotação (Ravex)
        return str(nro_cotacao)

    def preencher_campos_especificos_fase4(
        self, page: Page, dados_linha: Dict[str, str], nro_cotacao: str, log_callback: Callable, atraso_etapas: float
    ) -> None:
        try:
            log_callback(f"[F4] [Item {nro_cotacao}] Preenchendo Senha Ravex...", "DEBUG")
            ravex_textbox = page.get_by_role("textbox", name="Senha Ravex")
            if ravex_textbox.is_visible(timeout=2000):
                ravex_textbox.fill(str(nro_cotacao))
                time.sleep(atraso_etapas)
            else:
                # Seletor alternativo genérico
                page.fill('input[name="dados_outrosValores[senha_ravex]"]', str(nro_cotacao))
                time.sleep(atraso_etapas)
        except Exception as e:
            log_callback(f"[F4] [Item {nro_cotacao}] Aviso ao preencher Senha Ravex: {e}", "DEBUG")

    def transicionar_para_fase5(self, page: Page, nro_cotacao: str, log_callback: Callable, atraso_etapas: float) -> bool:
        try:
            # 1. Clica em Salvar no formulário de conhecimento
            log_callback(f"[F4] [Item {nro_cotacao}] Clicando em Salvar Conhecimento...", "DEBUG")
            page.get_by_role("button", name="Salvar").click()
            
            # 2. Aguarda ir para a listagem
            log_callback(f"[F4] [Item {nro_cotacao}] Aguardando retorno para a listagem...", "DEBUG")
            page.wait_for_selector('input[name="busca_nDoc"]', timeout=30000)
            
            # Tenta abrir filtros se fechados
            try:
                page.locator(".fa.fa-chevron-up").click(timeout=2000)
            except Exception:
                pass
                
            # 3. Filtra pelo número da cotação (Ravex)
            page.fill('input[name="busca_nDoc"]', str(nro_cotacao))
            time.sleep(atraso_etapas)
            page.click('button:has-text("Filtrar")')
            time.sleep(atraso_etapas)
            
            # 4. Seleciona a caixa de "Emitir contrato de frete"
            checkbox_selector = 'input[type="checkbox"][name="dados_selecionados[]"]'
            page.wait_for_selector(checkbox_selector, timeout=10000)
            page.locator(checkbox_selector).first.check()
            time.sleep(atraso_etapas)
            
            # 5. Clica em Avançar para abrir formulário de contrato
            page.click('#botao_avancar')
            time.sleep(atraso_etapas)
            
            # 6. Aguarda o formulário carregar
            page.wait_for_selector('input[name="dados_dtFimViagem"]', state="visible", timeout=30000)
            return True
            
        except Exception as e:
            log_callback(f"[F4] [Item {nro_cotacao}] ERRO na transição para o Contrato de Frete: {e}", "ERRO")
            import traceback
            log_callback(f"[F4] Traceback: {traceback.format_exc()}", "DEBUG")
            return False

    # Fase 5
    def get_fim_viagem(self, page: Page, dados_linha: Dict[str, str], data_pagamento: str, log_callback: Callable) -> str | None:
        try:
            data_emissao = page.input_value('input[name="dados_dtEmissaoRF"]')
            nro_cotacao = dados_linha.get("Nro cotação", "N/A")
            log_callback(f"[F5] [Item {nro_cotacao}] Regra Lactalis: Usando Data de Emissão '{data_emissao}' para 'Fim viagem'.", "DEBUG")
            return data_emissao
        except Exception as e:
            nro_cotacao = dados_linha.get("Nro cotação", "N/A")
            log_callback(f"[F5] [Item {nro_cotacao}] ERRO ao obter data de emissão: {e}", "ERRO")
            return None

    def get_observacao(self, dados_linha: Dict[str, str]) -> str:
        obs_text = dados_linha.get("extracted_obs_interna", "")
        validade_raw = dados_linha.get("Validade")
        
        # Formata data de validade para dd/mm/yyyy
        if isinstance(validade_raw, datetime):
            validade_str = validade_raw.strftime('%d/%m/%Y')
        elif validade_raw:
            match = re.search(r'(\d{2})[-/](\d{2})[-/](\d{4})', str(validade_raw))
            if match:
                validade_str = f"{match.group(1)}/{match.group(2)}/{match.group(3)}"
            else:
                validade_str = str(validade_raw).strip()
        else:
            validade_str = ""

        # Substitui qualquer data na string de observação pela validade correta
        cleaned_obs = re.sub(r'\d{2}/\d{2}/\d{4}', validade_str, obs_text)
        cleaned_obs = re.sub(r'\d{2}/\d{2}/\d{2}(?!\d)', validade_str, cleaned_obs)
        
        # Limpa espaços duplos ou quebras de linha
        cleaned_obs = " ".join(cleaned_obs.split())
        return cleaned_obs

    def get_data_programada(self, dados_linha: Dict[str, str], data_pagamento: str, log_callback: Callable) -> str | None:
        validade_raw = dados_linha.get("Validade")
        if isinstance(validade_raw, datetime):
            return validade_raw.strftime('%d/%m/%Y')
        elif validade_raw:
            match = re.search(r'(\d{2})[-/](\d{2})[-/](\d{4})', str(validade_raw))
            if match:
                return f"{match.group(1)}/{match.group(2)}/{match.group(3)}"
            else:
                return str(validade_raw).strip()
        return None

class LactalisPernoiteCompany(LactalisSpecialBaseCompany):
    def match(self, remetente: str) -> bool:
        rem = remetente.lower()
        return super().match(remetente) and any(kw in rem for kw in ["pernoite", "diaria em rota", "diaria no cliente"])

class LactalisDiariaGarantidaCompany(LactalisSpecialBaseCompany):
    def match(self, remetente: str) -> bool:
        rem = remetente.lower()
        return super().match(remetente) and "diaria garantida" in rem
