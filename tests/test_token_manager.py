"""Tests for token manager behavior."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.api.siscomex.token import SharedTokenManager


def test_token_valido_retorna_false_sem_tokens() -> None:
    """Token is invalid when missing credentials."""
    manager = SharedTokenManager()
    manager.set_token = None
    manager.csrf_token = None
    manager.expiracao = None

    assert manager.token_valido() is False


def test_obter_headers_retorna_chaves_basicas() -> None:
    """Headers include auth and csrf tokens when set."""
    manager = SharedTokenManager()
    manager.set_token = "token"
    manager.csrf_token = "csrf"
    manager.expiracao = datetime.now(timezone.utc) + timedelta(minutes=10)

    headers = manager.obter_headers()
    assert headers["Authorization"] == "token"
    assert headers["X-CSRF-Token"] == "csrf"
