from __future__ import annotations

import unicodedata
from .base_strategy import BaseStrategy
from .lactalis_strategy import (
    LactalisBaseStrategy,
    LactalisDiariaParadaStrategy,
    LactalisPernoiteStrategy,
    LactalisDiariaGarantidaStrategy,
)
from .dpa_strategy import DPAStrategy
from .latam_strategy import LatamStrategy

# Ordem de prioridade na avaliação das estratégias
STRATEGIES: list[BaseStrategy] = [
    DPAStrategy(),
    LactalisPernoiteStrategy(),
    LactalisDiariaGarantidaStrategy(),
    LactalisDiariaParadaStrategy(),
    LatamStrategy(),
]


def _normalize(texto: str) -> str:
    nfkd = unicodedata.normalize('NFKD', str(texto or ""))
    return "".join(c for c in nfkd if not unicodedata.combining(c)).strip().lower()


def get_strategy(remetente: str) -> BaseStrategy:
    """Retorna a estratégia adequada para o remetente informado, com fallback seguro para Latam/Padrão."""
    clean_rem = _normalize(remetente)
    for strategy in STRATEGIES:
        if strategy.match(clean_rem):
            return strategy
    # Fallback padrão
    return STRATEGIES[-1]
