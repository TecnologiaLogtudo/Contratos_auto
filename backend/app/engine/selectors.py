"""Catálogo centralizado de seletores e cadeias de fallback do portal LogTudo (e-Login).

Isola 100% dos seletores de CSS, XPath e atributos da lógica de negócio.
Quando o ERP sofrer atualizações visuais ou mudanças de layout, basta alterar
as strings e cadeias de seletores deste arquivo.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class LoginSelectors:
    input_usuario: str = 'input[name="usuario"]'
    input_senha: str = 'input[name="senha"]'
    btn_submit: str = "#botaoSubmit, button:has-text('Entrar'), input[type='submit']"
    error_message: str = "p.error-message, .alert-danger"
    swal_container: str = ".swal2-html-container"
    token_2fa: str = 'input[name="token"]'


@dataclass(frozen=True)
class CotacoesSelectors:
    url_cotacoes: str = "https://logtudo.e-login.net/versoes/versao5.0/rotinas/c.php?id=transp_cotacoesFrete"
    url_conhecimentos: str = "https://logtudo.e-login.net/versoes/versao5.0/rotinas/c.php?id=trans_conhecimento"
    painel_busca_fechado: str = ".rg-busca-rapida.rg-busca-rapida-close"
    btn_expandir_busca: str = ".rg-busca-rapida__cabecalho, .fa.fa-chevron-up"
    input_busca_nro: str = 'input[name="busca_nro"]'
    btn_filtrar: str = 'input[value="Filtrar"], button:has-text("Filtrar")'
    status_error: str = 'div.error p:has-text("Status da cotação não permite editar a mesma")'
    checkbox_id: str = 'input[type="checkbox"][name="id"]'
    input_nro_pedido: str = 'input[name="dados_nroPedidoCliente"]'
    textareas_obs_interna: tuple = (
        'textarea[name="dados_observacaoInterna"]',
        'textarea[name="dados_obsInterna"]',
        'textarea[name="dados_observacoesInternas"]',
    )
    btn_adicionar_conhecimento: str = '[id="_boop"] > a, a:has-text("Adicionar"), .fa-plus'


@dataclass(frozen=True)
class ConhecimentoSelectors:
    url_formulario: str = "https://logtudo.e-login.net/versoes/versao5.0/rotinas/formulario.php?rotina=trans_conhecimento&OP=O1&_qsf=1"
    select_agencia: str = 'select[name="dados_agencias_id"]'
    select_talao: str = 'select[name="dados_tiposTaloes_id"]'
    chk_emitir_recibo: str = 'input[name="dados_emitirReciboFrete[]"]'
    input_pesquisa_pedido: str = 'input[name="pesquisa_pedidos_id"]'
    btn_pesquisa_pedido: str = 'i[name="botaoPesquisa_pedidos_id"]'
    select_pedido: str = 'select[name="dados_pedidos_id"]'
    input_nf_auxiliar: str = '#pswobj3'
    btn_pesquisa_nf: str = '.swrepp > td > em > .fa-solid, #pswobj3 + em i'
    input_complemento_pedido: str = 'input[name="dados_complementoPedido"]'
    btn_avancar: str = '#botao_avancar, button:has-text("Avançar")'
    indicador_fase4: str = 'input[name="pesquisa_enderecoDestinatario_id"], select[name="dados_enderecoDestinatario_id"]'


@dataclass(frozen=True)
class FreteSelectors:
    select_remetente: str = 'select[name="dados_enderecoRemetente_id"]'
    input_pesquisa_remetente: str = 'input[name="pesquisa_enderecoRemetente_id"]'
    btn_pesquisa_remetente: str = 'i[name="botaoPesquisa_enderecoRemetente_id"]'

    select_destinatario: str = 'select[name="dados_enderecoDestinatario_id"]'
    input_pesquisa_destinatario: str = 'input[name="pesquisa_enderecoDestinatario_id"]'
    btn_pesquisa_destinatario: str = 'i[name="botaoPesquisa_enderecoDestinatario_id"]'

    chk_definir_inicio_fim: str = 'input[name="dados_definirInicioFimPrestacao[]"]'
    input_pesquisa_municipio_ini: str = 'input[name="pesquisa_cMunIni"]'
    btn_pesquisa_municipio_ini: str = 'i[name="botaoPesquisa_cMunIni"]'
    select_municipio_ini: str = 'select[name="dados_cMunIni"]'

    btn_pesquisa_cfop: str = 'i[name="botaoPesquisa_cfops_id"]'
    select_cfop: str = 'select[name="dados_cfops_id"]'

    input_pesquisa_motorista: str = 'input[name="pesquisa_dados_motorista_id"]'
    btn_pesquisa_motorista: str = 'i[name="botaoPesquisa_dados_motorista_id"]'
    select_motorista: str = 'select[name="dados_motorista_id"]'

    select_tabela_transporte: str = 'select[name="dados_freteMinimo_tabela"]'
    select_tipo_carga: str = 'select[name="dados_freteMinimo_tipoCarga"]'
    select_regra_frete: str = 'select[name="dados_regraFrete_id"]'

    campos_valores_zerar: tuple = (
        'input[name="dados_valorFrete"]',
        'input[name="dados_baseCalculo"]',
        'input[name="dados_aliquota"]',
        'input[name="dados_valorICMS"]',
        'input[name="dados_valoresOutros"]',
        'input[name="dados_totalPrestacao"]',
    )
    input_frete_terceiros: str = 'input[name="dados_outrosValores[freteterceiros]"]'
    input_senha_ravex_role: str = "Senha Ravex"
    input_senha_ravex_fallback: str = 'input[name="dados_outrosValores[senha_ravex]"]'

    textarea_obs_pv: str = 'textarea[name="dados_observacaoPV"]'
    chk_cte_valor_zerado: str = 'input[name="dados_conf_CTeValorZerado[]"]'
    btn_avancar: str = '#botao_avancar, button:has-text("Avançar")'
    indicador_fase5: str = 'input[name="dados_dtFimViagem"]'


@dataclass(frozen=True)
class ContratoSelectors:
    input_dt_fim_viagem: str = 'input[name="dados_dtFimViagem"]'
    input_dt_emissao_rf: str = 'input[name="dados_dtEmissaoRF"]'

    input_pesquisa_perfil: str = 'input[name="pesquisa_dados_perfisApropriacao_id"]'
    btn_pesquisa_perfil: str = 'i[name="botaoPesquisa_dados_perfisApropriacao_id"]'
    select_perfil: str = 'select[name="dados_perfisApropriacao_id"]'

    input_kms: str = 'input[name="dados_kms"]'
    input_pesquisa_ncm: str = 'input[name="pesquisa_dados_ncm"]'
    btn_pesquisa_ncm: str = 'i[name="botaoPesquisa_dados_ncm"]'
    select_ncm: str = 'select[name="dados_ncm"]'

    select_composicao_veicular: str = 'select[name="dados_composicao_veicular"]'
    select_regras_carreto: str = 'select[name="dados_regrasCarreto_id"]'
    textarea_obs_contrato: str = 'textarea[name="dados_obs"]'

    select_operadora_credito: str = 'select[name="dados_operadoraCredito_id"]'
    input_cartao_operadora: str = 'input[name="dados_nroCartaoOperadoraCredito"]'
    select_operacao_repom: str = 'select[name="dados_operacaoRepom"]'
    select_tipo_saldo_repom: str = 'select[name="dados_tipoSaldoRepom"]'

    input_pesquisa_remetente_contrato: str = 'input[name="pesquisa_dados_enderecoRemetenteContrato_id"]'
    btn_pesquisa_remetente_contrato: str = 'i[name="botaoPesquisa_dados_enderecoRemetenteContrato_id"]'
    input_pesquisa_destinatario_contrato: str = 'input[name="pesquisa_dados_enderecoDestinatarioContrato_id"]'
    btn_pesquisa_destinatario_contrato: str = 'i[name="botaoPesquisa_dados_enderecoDestinatarioContrato_id"]'
    select_destinatario_contrato: str = 'select[name="dados_enderecoDestinatarioContrato_id"]'

    input_data_saldo_repom: str = 'input[name="dados_dataSaldoRepom"]'
    chk_frete_minimo_antt: str = '#confirmacaoFreteMinimo_concorda'
    chk_confirmacao_ncm: str = 'input[name="dados_confirmacaoNCMGeral_concorda"]'

    btn_cadastrar: str = '#botao_cadastrar, button:has-text("Salvar")'
    err_frete_minimo: str = 'input[name="dados_freteMinimo_valor"].swstatus-input-error'
    err_campos_obrigatorios: str = 'div.rotina-generica.alert-message.error:has-text("Os seguintes campos são obrigatórios")'

    # Alerta genérico de erro de negócio do portal: o motivo específico aparece
    # em <p class="regular-small-text"> (ex.: "A data de emissão não pode ser ser
    # maior que a data programada do saldo.", "Status da cotação não permite
    # editar a mesma."). Ver element_erros.txt.
    err_alerta_generico: str = 'div.rotina-generica.alert-message.error p.regular-small-text'
    err_data_emissao: str = 'div.rotina-generica.alert-message.error:has-text("A data de emissão não pode ser")'

    cfop_modal_container: str = '#COM_RF_confirmacaoPrimeiroUsoCFOP'
    radio_cfop_permissao_sim: str = 'input[name="dados_conf_primeiroUsoCFOP_comPermissao"][value="S"]'


class SelectorsCatalog:
    login = LoginSelectors()
    cotacoes = CotacoesSelectors()
    conhecimento = ConhecimentoSelectors()
    frete = FreteSelectors()
    contrato = ContratoSelectors()


SELECTORS = SelectorsCatalog()
