from __future__ import annotations

from typing import Optional
from ...domain.models import ItemContrato
from .base_strategy import BaseStrategy


class LatamStrategy(BaseStrategy):
    """Estratégia para Latam e contingência padrão para operações gerais."""

    def match(self, remetente: str) -> bool:
        rem = (remetente or "").lower()
        return "latam" in rem or "tam" in rem or "02.012.862" in rem or "02012862" in rem

    def get_termo_busca_perfil(self, cidade_planilha: str) -> str:
        cid = (cidade_planilha or "").lower()
        if "vitoria da conquista" in cid or "vitória da conquista" in cid:
            return "vitoria"
        return cidade_planilha
