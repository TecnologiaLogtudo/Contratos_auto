from unittest.mock import MagicMock, patch

from backend.app.domain.models import ItemContrato
from backend.app.engine.pages.frete_page import FretePage
from backend.app.engine.strategies.latam_strategy import LatamStrategy


def test_latam_destinatario_usa_logtudo_quando_remetente_sem_cnpj():
    page = MagicMock()
    rem_sel = MagicMock()
    rem_sel.input_value.return_value = "123"
    rem_opt = MagicMock()
    rem_opt.inner_text.return_value = "REMETENTE SEM DOCUMENTO"
    page.locator.side_effect = lambda sel: rem_sel if sel == 'select[name="dados_enderecoRemetente_id"]' else rem_opt

    item = ItemContrato(nro_cotacao="100", remetente="LATAM")
    frete_page = FretePage(page)

    with patch.object(frete_page, "_selecionar_destinatario_por_cnpj") as selecionar:
        frete_page._sincronizar_remetente_destinatario(item, LatamStrategy(), 0.05)

    selecionar.assert_called_once_with("20511709000169", item, 0.05)


def test_latam_nao_junta_numeros_soltos_como_cnpj():
    page = MagicMock()
    rem_sel = MagicMock()
    rem_sel.input_value.return_value = "123"
    rem_opt = MagicMock()
    rem_opt.inner_text.return_value = "7019 - TAM LINHAS AEREAS - filial 3000 - codigo 123456"
    page.locator.side_effect = lambda sel: rem_sel if sel == 'select[name="dados_enderecoRemetente_id"]' else rem_opt

    item = ItemContrato(nro_cotacao="100", remetente="LATAM")
    frete_page = FretePage(page)

    with patch.object(frete_page, "_selecionar_destinatario_por_cnpj") as selecionar:
        frete_page._sincronizar_remetente_destinatario(item, LatamStrategy(), 0.05)

    selecionar.assert_called_once_with("20511709000169", item, 0.05)
