from __future__ import annotations

from typing import Optional


class AutomationError(Exception):
    """Exceção base para todas as falhas na automação de contratos."""

    def __init__(self, message: str, step: Optional[str] = None, details: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.step = step or "Geral"
        self.details = details or ""

    def __str__(self) -> str:
        if self.details:
            return f"[{self.step}] {self.message} | Detalhes: {self.details}"
        return f"[{self.step}] {self.message}"


class SpreadsheetValidationError(AutomationError):
    """Erro de validação ou leitura na planilha de entrada (dados faltantes ou corrompidos)."""

    def __init__(self, message: str, missing_fields: Optional[list[str]] = None, row_index: Optional[int] = None):
        step = f"Validação Planilha (Linha {row_index})" if row_index else "Validação Planilha"
        details = f"Campos: {', '.join(missing_fields)}" if missing_fields else None
        super().__init__(message, step=step, details=details)
        self.missing_fields = missing_fields or []
        self.row_index = row_index


class AuthenticationError(AutomationError):
    """Falha de login, credenciais inválidas ou timeout no 2FA."""

    def __init__(self, message: str, reason: str = "Credenciais Inválidas"):
        super().__init__(message, step="Fase 2 - Login", details=reason)
        self.reason = reason


class QuoteExtractionError(AutomationError):
    """Falha na extração de dados da cotação no portal (Pedido, NF ou Status não editável)."""

    def __init__(self, message: str, quote_number: str, details: Optional[str] = None):
        super().__init__(message, step=f"Cotação {quote_number}", details=details)
        self.quote_number = quote_number


class NavigationError(AutomationError):
    """Falha de navegação, timeout de URL ou bloqueio de rota."""

    def __init__(self, message: str, url: str, step: str = "Navegação"):
        super().__init__(message, step=step, details=f"URL: {url}")
        self.url = url


class FormFillError(AutomationError):
    """Falha ao preencher campos, selecionar dropdowns ou avançar etapas do formulário."""

    def __init__(self, message: str, field_name: str, step: str = "Formulário"):
        super().__init__(message, step=step, details=f"Campo/Ação: {field_name}")
        self.field_name = field_name


class SubmissionError(AutomationError):
    """Falha ao salvar o contrato de frete ou na aprovação de contingência de CFOP."""

    def __init__(self, message: str, reason: str = "Timeout ou Erro de Validação"):
        super().__init__(message, step="Fase 5 - Salvamento", details=reason)
        self.reason = reason
