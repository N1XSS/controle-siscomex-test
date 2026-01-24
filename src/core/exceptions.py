"""Custom exceptions for Controle Siscomex."""

from __future__ import annotations


class ControleSiscomexError(Exception):
    """Base exception for system errors."""


class DatabaseError(ControleSiscomexError):
    """Database operation error."""


class ConnectionError(DatabaseError):
    """Database connection error."""


class QueryError(DatabaseError):
    """Database query error."""


class SiscomexAPIError(ControleSiscomexError):
    """Siscomex API error."""


class AuthenticationError(SiscomexAPIError):
    """Authentication error with Siscomex API."""


class RateLimitError(SiscomexAPIError):
    """Rate limit exceeded."""

    def __init__(self, message: str, retry_after: int = 3600) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class TokenExpiredError(SiscomexAPIError):
    """Authentication token expired."""


class DUEProcessingError(ControleSiscomexError):
    """DUE processing error."""


class ValidationError(ControleSiscomexError):
    """Data validation error."""


class ConfigurationError(ControleSiscomexError):
    """Configuration error."""
