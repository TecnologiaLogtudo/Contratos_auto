from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ItemStatus(str, Enum):
    PENDENTE = "Pendente"
    CONCLUIDO = "Concluído"
    ERRO = "Erro"
    FALHA_VALIDACAO = "Falha na Validação"


class ItemContrato(BaseModel):
    """Representação tipada e validada de uma linha da planilha de contratos."""
    nro_cotacao: str = Field(..., description="Número da cotação / Ravex")
    categoria_veiculo: str = Field(default="", description="Categoria do veículo")
    cidade: str = Field(default="", description="Cidade de destino ou origem")
    uf: str = Field(default="", description="UF de destino ou origem")
    nome: str = Field(default="", description="Nome higienizado do motorista")
    placa: str = Field(default="", description="Placa do veículo (Mercosul ou antiga)")
    data_pagamento: str = Field(default="", description="Data prevista de pagamento")
    viagem_extra: str = Field(default="Não", description="Indica se é viagem extra (Sim/Não)")
    remetente: str = Field(default="", description="Remetente da operação (ex: Lactalis, DPA, Latam)")
    validade: Optional[str] = Field(default=None, description="Data de validade do contrato")
    frete_a_pagar: Optional[str] = Field(default=None, description="Valor do frete a pagar")
    frete_negociado: Optional[str] = Field(default=None, description="Valor do frete negociado")
    status: ItemStatus = Field(default=ItemStatus.PENDENTE, description="Status do item")
    observacao_erro: Optional[str] = Field(default=None, description="Motivo do erro caso falhe")
    
    # Metadados internos extraídos durante a execução
    extracted_nro_pedido: Optional[str] = None
    extracted_obs_interna: Optional[str] = None
    extracted_nf: Optional[str] = None
    row_index: Optional[int] = None

    def to_row_processados(self) -> list[Any]:
        """Gera a linha para a aba 'Dados Processados'."""
        return [
            self.nro_cotacao,
            self.categoria_veiculo,
            self.cidade,
            self.uf,
            self.nome,
            self.placa,
            self.data_pagamento,
            self.viagem_extra,
            self.remetente,
            self.validade or "",
            self.frete_a_pagar or "",
            self.frete_negociado or "",
            self.status.value,
        ]

    def to_row_nao_realizado(self, motivo: str) -> list[Any]:
        """Gera a linha para a aba 'Contrato não realizado'."""
        return [
            self.nro_cotacao,
            self.categoria_veiculo,
            self.cidade,
            self.uf,
            self.nome,
            self.placa,
            self.data_pagamento,
            motivo or self.observacao_erro or "Erro não especificado",
            self.status.value,
        ]


@dataclass
class ItemResult:
    """Resultado da execução de um único contrato."""
    nro_cotacao: str
    status: ItemStatus = ItemStatus.CONCLUIDO
    sucesso: bool = True
    cte_number: Optional[str] = None
    motivo_erro: Optional[str] = None
    message: str = ""
    screenshot_path: Optional[str] = None
    execution_time_seconds: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


@dataclass
class ExecutionSummary:
    """Resumo consolidado do processamento do arquivo."""
    total: int = 0
    sucessos: int = 0
    erros: int = 0
    pendentes: int = 0
    duracao_segundos: float = 0.0

    @property
    def taxa_sucesso(self) -> float:
        processados = self.sucessos + self.erros
        if not processados:
            return 0.0
        return round((self.sucessos / processados) * 100, 2)
