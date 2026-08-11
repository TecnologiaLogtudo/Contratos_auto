from .base_company import BaseCompany
from .lactalis import (
    LactalisDiariaParadaCompany,
    LactalisPernoiteCompany,
    LactalisDiariaGarantidaCompany
)
from .dpa import DPACompany
from .latam import LatamCompany

# Order is important: more specific rules check first,
# and LatamCompany acts as the default fallback.
COMPANIES = [
    DPACompany(),
    LactalisPernoiteCompany(),
    LactalisDiariaGarantidaCompany(),
    LactalisDiariaParadaCompany(),
    LatamCompany()
]

import unicodedata

def _remover_acentos(texto: str) -> str:
    nfkd_form = unicodedata.normalize('NFKD', texto)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

def get_company(remetente: str) -> BaseCompany:
    remetente_clean = _remover_acentos(str(remetente or "").strip().lower())
    for company in COMPANIES:
        if company.match(remetente_clean):
            return company
    # fallback to Latam/Default
    return COMPANIES[-1]
