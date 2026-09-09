from __future__ import annotations

import pytest
from backend.app.domain.models import ItemContrato
from backend.app.engine.strategies.strategy_factory import get_strategy
from backend.app.engine.strategies.lactalis_strategy import (
    LactalisDiariaParadaStrategy,
    LactalisPernoiteStrategy,
    LactalisDiariaGarantidaStrategy,
    extrair_numero_nf,
)
from backend.app.engine.strategies.dpa_strategy import DPAStrategy
from backend.app.engine.strategies.latam_strategy import LatamStrategy


def test_strategy_factory_matching():
    # Lactalis Diária Parada
    st1 = get_strategy("LACTALIS DO BRASIL")
    assert isinstance(st1, LactalisDiariaParadaStrategy)

    # Lactalis Pernoite
    st2 = get_strategy("LACTALIS PERNOITE")
    assert isinstance(st2, LactalisPernoiteStrategy)

    # Lactalis Diária Garantida
    st3 = get_strategy("LACTALIS DIARIA GARANTIDA")
    assert isinstance(st3, LactalisDiariaGarantidaStrategy)

    # DPA
    st4 = get_strategy("DPA DAIRY PARTNERS 05.300.331/0014-85")
    assert isinstance(st4, DPAStrategy)

    # Latam
    st5 = get_strategy("TAM LINHAS AEREAS")
    assert isinstance(st5, LatamStrategy)

    # Fallback
    st6 = get_strategy("EMPRESA DESCONHECIDA QUALQUER")
    assert isinstance(st6, LatamStrategy)


def test_calculo_data_programada_lactalis():
    st = LactalisDiariaParadaStrategy()

    # Validade dia <= 15 -> dia 05 do mês seguinte
    item1 = ItemContrato(nro_cotacao="1", validade="10/08/2026")
    assert st.get_data_programada(item1) == "05/09/2026"

    item2 = ItemContrato(nro_cotacao="2", validade="15/08/2026")
    assert st.get_data_programada(item2) == "05/09/2026"

    # Validade dia > 15 -> dia 20 do mês seguinte
    item3 = ItemContrato(nro_cotacao="3", validade="16/08/2026")
    assert st.get_data_programada(item3) == "20/09/2026"

    # Rollover de ano (Dezembro -> Janeiro do ano seguinte)
    item4 = ItemContrato(nro_cotacao="4", validade="28/12/2026")
    assert st.get_data_programada(item4) == "20/01/2027"

    item5 = ItemContrato(nro_cotacao="5", validade="05/12/2026")
    assert st.get_data_programada(item5) == "05/01/2027"


def test_extrair_numero_nf():
    assert extrair_numero_nf("pernoite 53640535 nf-115452") == "115452"
    assert extrair_numero_nf("Diaria Garantida NF: 987654") == "987654"
    assert extrair_numero_nf("CARGA EXTRA DANFE 445566") == "445566"
    assert extrair_numero_nf("Ref NFe-123456 cliente") == "123456"
    assert extrair_numero_nf("Texto sem numero nenhum") is None


def test_observacao_contrato_lactalis():
    st_pernoite = LactalisPernoiteStrategy()
    item = ItemContrato(
        nro_cotacao="100",
        validade="15/08/2026",
        extracted_obs_interna="pernoite 53640535 nf-115452 06/08/2026",
    )
    obs = st_pernoite.get_observacao_contrato(item)
    # A data antiga 06/08/2026 deve ser substituída pela validade 15/08/2026
    assert "15/08/2026" in obs
    assert "06/08/2026" not in obs
