import sys
import os
from pathlib import Path

# Adiciona o diretório raiz ao sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from playwright.sync_api import sync_playwright
from backend.app.phases.dialog_helper import fechar_popups_alerta, esperar_e_fechar_popups


def test_fechar_popup_lactalis_nf_duplicada():
    print("Iniciando teste do dialog_helper...")
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Teste Popup</title>
        <style>
            .ui-dialog { display: block; position: absolute; z-index: 1000; }
            .ui-widget-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: #aaa; opacity: 0.3; z-index: 999; }
        </style>
    </head>
    <body>
        <input name="pesquisa_enderecoRemetente_id" value="" />
        <i name="botaoPesquisa_enderecoRemetente_id">Pesquisar</i>

        <!-- Modal idêntico ao do sistema do usuário -->
        <div class="ui-widget-overlay ui-front"></div>
        <div class="ui-dialog ui-widget ui-widget-content ui-corner-all ui-front ui-dialog-buttons" tabindex="-1" role="dialog" aria-describedby="ui-id-1" style="height: auto; width: 300px; top: 280px; left: 592px; display: block;" aria-labelledby="ui-id-2">
            <div class="ui-dialog-titlebar ui-widget-header ui-corner-all ui-helper-clearfix">
                <span id="ui-id-2" class="ui-dialog-title">Mensagem</span>
                <button type="button" class="ui-button ui-widget ui-state-default ui-corner-all ui-button-icon-only ui-dialog-titlebar-close" role="button" aria-disabled="false" title="Fechar">
                    <span class="ui-button-icon-primary ui-icon ui-icon-closethick"></span>
                    <span class="ui-button-text">Fechar</span>
                </button>
            </div>
            <div class="swconfirm ui-dialog-content ui-widget-content" id="ui-id-1" style="width: auto; min-height: 0px; max-height: none; height: auto;">
                As seguintes NFs já foram utilizadas em outros conhecimentos:<br><br>
                <table><tbody><tr><td width="125"><b>NF</b>: 122603/1</td><td><b>CT</b>: 122779</td></tr></tbody></table>
            </div>
            <div class="ui-dialog-buttonpane ui-widget-content ui-helper-clearfix">
                <div class="ui-dialog-buttonset">
                    <button type="button" id="btn-ok-teste" class="ui-button ui-widget ui-state-default ui-corner-all ui-button-text-only" role="button" aria-disabled="false" onclick="document.querySelector('.ui-dialog').style.display='none'; document.querySelector('.ui-widget-overlay').remove();">
                        <span class="ui-button-text">OK</span>
                    </button>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

    logs_capturados = []
    def log_cb(msg, level):
        logs_capturados.append((msg, level))
        print(f"[{level}] {msg}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(html_content)

        # 1. Verifica se o diálogo está visível antes
        assert page.locator('.ui-dialog:visible').count() == 1, "O diálogo deveria estar visível no início do teste"

        # 2. Executa fechar_popups_alerta
        fechou = fechar_popups_alerta(page, log_cb, nro_cotacao="1870015")
        assert fechou is True, "fechar_popups_alerta deveria ter retornado True"

        # 3. Verifica se o diálogo e o overlay foram fechados/removidos
        assert page.locator('.ui-dialog:visible').count() == 0, "O diálogo deveria ter sido fechado"
        assert page.locator('.ui-widget-overlay:visible').count() == 0, "O overlay deveria ter sido removido"

        # 4. Verifica se o log capturou a mensagem
        mensagens = [m[0] for m in logs_capturados]
        assert any("As seguintes NFs já foram utilizadas em outros conhecimentos" in m for m in mensagens), f"Mensagem esperada não encontrada nos logs: {mensagens}"
        assert any("1870015" in m for m in mensagens), "Número da cotação deveria constar no log"

        # 5. Executa novamente quando não há popups
        fechou_segunda_vez = fechar_popups_alerta(page, log_cb, nro_cotacao="1870015")
        assert fechou_segunda_vez is False, "Não deveria fechar nada quando não há popup"

        # 6. Testa esperar_e_fechar_popups
        fechou_espera = esperar_e_fechar_popups(page, log_cb, nro_cotacao="1870015", duracao_segundos=0.5, intervalo_segundos=0.1)
        assert fechou_espera is False, "esperar_e_fechar_popups não deveria encontrar popups em tela limpa"

        browser.close()
        print("TESTE DO DIALOG_HELPER PASSOU COM SUCESSO!")


def test_lactalis_sincronizacao_com_popup():
    print("Iniciando teste de sincronização Lactalis com popup bloqueador...")
    from backend.app.companies.lactalis import LactalisDiariaParadaCompany

    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Teste Lactalis</title>
        <style>
            .ui-dialog { display: block; position: absolute; z-index: 1000; }
            .ui-widget-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: #aaa; opacity: 0.3; z-index: 999; }
        </style>
    </head>
    <body>
        <input name="pesquisa_enderecoRemetente_id" value="" />
        <i name="botaoPesquisa_enderecoRemetente_id" onclick="document.querySelector('select[name=dados_enderecoRemetente_id]').innerHTML = '<option value=123>43.340.312/0006-61 - LACTALIS</option>';">Pesquisar Remetente</i>
        <select name="dados_enderecoRemetente_id"></select>

        <input name="pesquisa_enderecoDestinatario_id" value="" />
        <i name="botaoPesquisa_enderecoDestinatario_id" onclick="document.querySelector('select[name=dados_enderecoDestinatario_id]').innerHTML = '<option value=456>20.511.709/0001-69 - LOGTUDO</option>';">Pesquisar Destinatario</i>
        <select name="dados_enderecoDestinatario_id"></select>

        <!-- Modal bloqueador de tela -->
        <div class="ui-widget-overlay ui-front"></div>
        <div class="ui-dialog ui-widget ui-widget-content ui-corner-all ui-front ui-dialog-buttons" tabindex="-1" role="dialog" aria-describedby="ui-id-1" style="height: auto; width: 300px; top: 280px; left: 592px; display: block;" aria-labelledby="ui-id-2">
            <div class="ui-dialog-titlebar ui-widget-header ui-corner-all ui-helper-clearfix">
                <span id="ui-id-2" class="ui-dialog-title">Mensagem</span>
                <button type="button" class="ui-button ui-widget ui-state-default ui-corner-all ui-button-icon-only ui-dialog-titlebar-close" role="button" aria-disabled="false" title="Fechar">
                    <span class="ui-button-text">Fechar</span>
                </button>
            </div>
            <div class="swconfirm ui-dialog-content ui-widget-content" id="ui-id-1">
                As seguintes NFs já foram utilizadas em outros conhecimentos:<br><br>
                <table><tbody><tr><td width="125"><b>NF</b>: 122603/1</td><td><b>CT</b>: 122779</td></tr></tbody></table>
            </div>
            <div class="ui-dialog-buttonpane ui-widget-content ui-helper-clearfix">
                <div class="ui-dialog-buttonset">
                    <button type="button" class="ui-button ui-widget ui-state-default ui-corner-all ui-button-text-only" role="button" aria-disabled="false" onclick="document.querySelector('.ui-dialog').style.display='none'; document.querySelector('.ui-widget-overlay').remove();">
                        <span class="ui-button-text">OK</span>
                    </button>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

    logs = []
    def log_cb(msg, level):
        logs.append((msg, level))
        print(f"[{level}] {msg}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(html_content)

        company = LactalisDiariaParadaCompany()
        sucesso = company.sincronizar_remetente_destinatario(page, "1870015", log_cb, 0.05)

        assert sucesso is True, "A sincronização Lactalis deveria ter sucesso mesmo com o popup inicial"
        assert page.input_value('select[name="dados_enderecoRemetente_id"]') == "123"
        assert page.input_value('select[name="dados_enderecoDestinatario_id"]') == "456"

        browser.close()
        print("TESTE DE SINCRONIZAÇÃO LACTALIS PASSOU COM SUCESSO!")


if __name__ == "__main__":
    test_fechar_popup_lactalis_nf_duplicada()
    test_lactalis_sincronizacao_com_popup()
