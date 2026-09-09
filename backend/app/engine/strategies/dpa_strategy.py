from __future__ import annotations

from typing import Optional
from ...domain.models import ItemContrato
from .lactalis_strategy import LactalisBaseStrategy


class DPAStrategy(LactalisBaseStrategy):
    """Estratégia dedicada para DPA (Dairy Partners)."""

    def match(self, remetente: str) -> bool:
        rem = (remetente or "").lower()
        return "dpa" in rem or "dairy partners" in rem or "05.300.331" in rem or "05300331" in rem

    def get_termo_busca_perfil(self, cidade_planilha: str) -> str:
        return "dpa BA"
