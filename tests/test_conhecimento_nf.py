"""Teste unitário da vinculação e sincronização do campo de Nota Fiscal (NF) na Fase 3."""

from __future__ import annotations

from unittest.mock import MagicMock
import pytest

from backend.app.domain.models import ItemContrato
from backend.app.engine.pages.conhecimento_page import ConhecimentoPage


def test_vincular_cotacao_com_nf():
    """Testa se ConhecimentoPage preenche, busca e seleciona a Nota Fiscal quando extracted_nf existe."""
    mock_page = MagicMock()
    mock_log = MagicMock()

    # Configura locators simulados
    mock_input_pedidos = MagicMock()
    mock_btn_pedidos = MagicMock()
    mock_select_pedidos = MagicMock()

    mock_input_nf = MagicMock()
    mock_btn_nf = MagicMock()
    mock_select_nf = MagicMock()

    mock_opt_pedidos = MagicMock()
    mock_opt_pedidos.get_attribute.return_value = "1001"
    mock_opt_pedidos.inner_text.return_value = "12345 / Teste"
    mock_select_pedidos.locator.return_value.all.return_value = [mock_opt_pedidos]
    mock_select_pedidos.get_attribute.return_value = ""

    mock_input_nf.first = mock_input_nf
    mock_btn_nf.first = mock_btn_nf
    mock_select_nf.first = mock_select_nf
    mock_opt_nf = MagicMock()
    mock_opt_nf.get_attribute.return_value = "435618"
    mock_opt_nf.inner_text.return_value = "Cód:435618 NF:127100/1 - LACTALIS"
    mock_select_nf.locator.return_value.all.return_value = [mock_opt_nf]

    def locator_side_effect(selector):
        if 'botaoPesquisa_pedidos_id' in selector:
            return mock_btn_pedidos
        if 'pesquisa_pedidos_id' in selector:
            return mock_input_pedidos
        if 'dados_pedidos_id' in selector:
            return mock_select_pedidos
        if 'botaoPesquisa_dados_notas_carregamento_id' in selector or '.swrepp' in selector:
            mock_btn_nf.count.return_value = 1
            return mock_btn_nf
        if 'pesquisa_dados_notas_carregamento_id' in selector or '#pswobj3' in selector:
            mock_input_nf.count.return_value = 1
            return mock_input_nf
        if 'dados_notas_carregamento_id' in selector or '#cswobj2_rep_2' in selector:
            mock_select_nf.count.return_value = 1
            return mock_select_nf
        return MagicMock()

    mock_page.locator.side_effect = locator_side_effect
    mock_page.wait_for_selector.return_value = None

    conhecimento_page = ConhecimentoPage(mock_page, mock_log)

    item = ItemContrato(
        linha_origem=2,
        empresa="Lactalis",
        tipo_solicitacao="Pernoite",
        nro_cotacao="12345",
        extracted_nro_pedido="12345",
        extracted_nf="127100",
    )

    mock_strategy = MagicMock()
    conhecimento_page._vincular_cotacao(item, mock_strategy, delay_step=0.01)

    # Verifica se input_nf foi preenchido com '127100'
    mock_input_nf.fill.assert_called_with("127100")
    # Verifica se o evento de alteração foi disparado
    mock_input_nf.dispatch_event.assert_called_with("change")
    # Verifica se a busca da NF foi clicada
    mock_btn_nf.click.assert_called_once()
    # Verifica se select_nf teve a opção selecionada
    mock_select_nf.select_option.assert_called_with(value="435618")
