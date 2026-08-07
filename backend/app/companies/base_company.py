import abc
import time
from typing import Callable, Dict
from playwright.sync_api import Page

class BaseCompany(abc.ABC):
    @abc.abstractmethod
    def match(self, remetente: str) -> bool:
        """Retorna True se o remetente bater com este cliente."""
        pass

    # Fase 1 - Validação
    def require_data_pagamento(self) -> bool:
        """Se o campo data_pagamento é obrigatório na planilha."""
        return True

    def require_validade(self) -> bool:
        """Se o campo validade é obrigatório na planilha."""
        return False

    # Fase 3 - Preenchimento da Cotação
    def match_cotacao_opcao(self, option_text: str, nro_cotacao: str) -> bool:
        """Retorna se o texto de uma opção de cotação corresponde à regra do cliente."""
        return option_text.strip().startswith(f"{nro_cotacao} /")

    def format_cotacao_erro_msg(self, target_option_prefix: str) -> str:
        """Mensagem de formato esperado para erro de cotação."""
        return f"'{target_option_prefix}'"

    def get_complemento_pedido(self, nro_cotacao_item: str) -> str | None:
        """Valor a preencher no campo dados_complementoPedido. Se retornar None, não preenche."""
        return str(nro_cotacao_item)

    def executar_pesquisa_cotacao(
        self,
        page: Page,
        dados_linha: Dict[str, str],
        nro_cotacao: str,
        log_callback: Callable,
        atraso_etapas: float,
        output_filepath: str
    ) -> bool:
        """Realiza a pesquisa e seleção da cotação na Fase 3."""
        from ..phases.fase3_preenchimento import registrar_erro_em_planilha
        try:
            select_locator = page.locator('select[name="dados_pedidos_id"]')
            
            # Preenche cotação
            page.fill('input[name="pesquisa_pedidos_id"]', str(nro_cotacao))
            time.sleep(atraso_etapas)
            
            # Clica em pesquisar
            page.click('i[name="botaoPesquisa_pedidos_id"]')
            page.wait_for_timeout(500)
            time.sleep(atraso_etapas)
            
            # Verifica e seleciona
            select_locator.wait_for(timeout=5000)
            options = select_locator.locator("option").all()
            
            # Caso 1: Nenhum registro encontrado
            if any("Nenhum registro encontrado!" in opt.inner_text() for opt in options):
                motivo_erro = "Nenhum registro de cotação encontrado no sistema."
                log_callback(f"[F3] [Item {nro_cotacao}] {motivo_erro}", "ERRO")
                registrar_erro_em_planilha(dados_linha, motivo_erro, log_callback, output_filepath)
                return False

            # Caso 2: Match prefix e seleciona
            target_option_prefix = f"{nro_cotacao} /"
            correct_option_value = None
            
            for opt in options:
                option_text = opt.inner_text()
                if self.match_cotacao_opcao(option_text, nro_cotacao):
                    correct_option_value = opt.get_attribute("value")
                    log_callback(f"[F3] [Item {nro_cotacao}] Opção correspondente encontrada: '{option_text.strip()}'", "DEBUG")
                    break
            
            if correct_option_value is not None:
                select_locator.select_option(value=correct_option_value)
                log_callback(f"[F3] [Item {nro_cotacao}] Cotação selecionada com sucesso.", "INFO")
                return True
            else:
                available_options = [opt.inner_text().strip() for opt in options]
                formato_esperado = self.format_cotacao_erro_msg(target_option_prefix)
                log_callback(f"[F3] [Item {nro_cotacao}] ERRO: Nenhuma opção de cotação correspondente ao formato {formato_esperado} foi encontrada.", "ERRO")
                log_callback(f"[F3] [Item {nro_cotacao}] Opções disponíveis: {available_options}", "DEBUG")
                registrar_erro_em_planilha(dados_linha, f"Cotação não encontrada no formato esperado ({formato_esperado}).", log_callback, output_filepath)
                return False
                
        except Exception as e:
            motivo_erro = f"O campo de seleção de cotação não foi encontrado ou erro após a pesquisa: {e}"
            log_callback(f"[F3] [Item {nro_cotacao}] ERRO: {motivo_erro}", "ERRO")
            registrar_erro_em_planilha(dados_linha, motivo_erro, log_callback, output_filepath)
            return False

    # Fase 4 - Dados do Frete
    @abc.abstractmethod
    def sincronizar_remetente_destinatario(
        self, page: Page, nro_cotacao: str, log_callback: Callable, atraso_etapas: float
    ) -> bool:
        """Executa a sincronização de remetente e destinatário no Playwright."""
        pass

    def get_regra_frete_id(self) -> str:
        """Retorna o valor da Regra de Frete (select dados_regraFrete_id)."""
        return "40"  # Padrão: Não realiza cálculos

    def preencher_frete_terceiros(
        self, page: Page, dados_linha: Dict[str, str], log_callback: Callable, nro_cotacao: str, atraso_etapas: float
    ) -> None:
        """Passo opcional 8.5 na Fase 4 para preencher frete terceiros."""
        pass

    def get_observacao_pv(self, dados_linha: Dict[str, str], nro_cotacao: str) -> str:
        """Retorna o valor para o campo dados_observacaoPV na Fase 4. Por padrão usa Motorista e Placa."""
        nome_motorista = dados_linha.get("Nome", "NOME NÃO ENCONTRADO")
        placa = dados_linha.get("Placa", "PLACA NÃO ENCONTRADA")
        partes_obs = []
        if nome_motorista != "NOME NÃO ENCONTRADO":
            partes_obs.append(nome_motorista)
        if placa != "PLACA NÃO ENCONTRADA":
            partes_obs.append(placa)
        return " - ".join(partes_obs) if partes_obs else ""

    def preencher_campos_especificos_fase4(
        self, page: Page, dados_linha: Dict[str, str], nro_cotacao: str, log_callback: Callable, atraso_etapas: float
    ) -> None:
        """Permite preencher campos adicionais/específicos na Fase 4."""
        pass

    # Fase 5 - Contrato de Frete
    def get_fim_viagem(self, page: Page, dados_linha: Dict[str, str], data_pagamento: str, log_callback: Callable) -> str | None:
        """Retorna o valor a preencher na Data Fim de Viagem."""
        return f"{data_pagamento} 12:00" if data_pagamento else None

    def get_termo_busca_perfil(self, cidade_planilha: str) -> str:
        """Retorna o termo para buscar no Perfil de Apropriação."""
        return cidade_planilha

    def get_valor_km(self, dados_km: str) -> str:
        """Retorna a quilometragem a preencher."""
        return dados_km

    def get_ncm_pesquisa(self) -> str:
        """Termo para pesquisar o NCM."""
        return "vinho"

    def get_ncm_valor(self) -> str:
        """Valor do NCM a selecionar."""
        return "2204."

    def get_observacao(self, dados_linha: Dict[str, str]) -> str:
        """Retorna a observação do contrato."""
        return "Contrato Diária"

    def get_data_programada(self, dados_linha: Dict[str, str], data_pagamento: str, log_callback: Callable) -> str | None:
        """Retorna a data programada para o saldo do contrato."""
        return data_pagamento

    # Utility helper
    def _preencher_campo_se_editavel(
        self,
        page: Page,
        selector: str,
        valor: str,
        log_callback: Callable,
        nro_cotacao: str,
        atraso_etapas: float
    ) -> None:
        try:
            locator = page.locator(selector)
            locator.wait_for(state="visible", timeout=3000)
            if locator.is_editable():
                locator.fill(valor)
            else:
                log_callback(f"[F4] [Item {nro_cotacao}] Campo '{selector}' bloqueado para edição (readonly/disabled). Ignorando.", "AVISO")
        except Exception:
            log_callback(f"[F4] [Item {nro_cotacao}] Não foi possível interagir com o campo '{selector}' (campo bloqueado para edição). Ignorando.", "AVISO")
        time.sleep(atraso_etapas)
