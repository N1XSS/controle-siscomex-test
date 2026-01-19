"""Shared pytest fixtures."""

from __future__ import annotations

from typing import Any

import pytest


@pytest.fixture()
def sample_due() -> dict[str, Any]:
    """Return a minimal DUE payload for normalization tests."""
    return {
        "numero": "24BR0001",
        "situacao": "EM_CARGA",
        "dataDeRegistro": "2024-01-01T00:00:00",
        "itens": [],
        "eventosDoHistorico": [],
        "situacoesDaCarga": [],
        "solicitacoes": [],
    }
