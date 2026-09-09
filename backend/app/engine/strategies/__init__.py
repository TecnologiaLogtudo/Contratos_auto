from .base_strategy import BaseStrategy
from .lactalis_strategy import (
    LactalisBaseStrategy,
    LactalisDiariaParadaStrategy,
    LactalisPernoiteStrategy,
    LactalisDiariaGarantidaStrategy,
    extrair_numero_nf,
)
from .dpa_strategy import DPAStrategy
from .latam_strategy import LatamStrategy
from .strategy_factory import get_strategy

__all__ = [
    "BaseStrategy",
    "LactalisBaseStrategy",
    "LactalisDiariaParadaStrategy",
    "LactalisPernoiteStrategy",
    "LactalisDiariaGarantidaStrategy",
    "extrair_numero_nf",
    "DPAStrategy",
    "LatamStrategy",
    "get_strategy",
]
