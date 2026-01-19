"""Tests for due_processor normalization helpers."""

from __future__ import annotations

from typing import Any

from src.processors.due import processar_dados_due


def test_processar_dados_due_minimal(sample_due: dict[str, Any]) -> None:
    """Ensure minimal payload produces normalized structures."""
    resultado = processar_dados_due(
        sample_due,
        atos_concessorios=[],
        atos_isencao=[],
        exigencias_fiscais=[],
        debug_mode=False,
    )

    assert resultado is not None
    assert "due_principal" in resultado
    assert "due_itens" in resultado
    assert resultado["due_principal"]


def test_processar_dados_due_sem_itens(sample_due: dict[str, Any]) -> None:
    """Ensure payload without items returns empty item list."""
    resultado = processar_dados_due(
        sample_due,
        atos_concessorios=[],
        atos_isencao=[],
        exigencias_fiscais=[],
        debug_mode=False,
    )

    assert resultado is not None
    assert resultado["due_itens"] == []
