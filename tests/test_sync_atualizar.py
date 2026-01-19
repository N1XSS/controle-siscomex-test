"""Tests for sync_atualizar helpers."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from src.core.constants import DIAS_AVERBACAO_RECENTE, SITUACOES_AVERBADAS
from src.sync import update_dues


def test_verificar_se_due_mudou_sem_mudanca(monkeypatch: pytest.MonkeyPatch) -> None:
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"dataDeRegistro": "2026-01-01T00:00:00.000-0300"}

    session = MagicMock()
    session.get.return_value = response
    monkeypatch.setattr(update_dues.token_manager, "session", session)
    monkeypatch.setattr(update_dues.token_manager, "obter_headers", lambda: {})

    data_bd = datetime(2026, 1, 2)
    mudou, dados, erro = update_dues.verificar_se_due_mudou("24BR0001", data_bd)

    assert mudou is False
    assert dados is None
    assert erro is None


def test_carregar_dues_para_verificar_classifica(monkeypatch: pytest.MonkeyPatch) -> None:
    agora = datetime.utcnow()
    rows = [
        ("DUE1", next(iter(SITUACOES_AVERBADAS)), agora, agora),
        ("DUE2", next(iter(SITUACOES_AVERBADAS)), agora, agora - timedelta(days=DIAS_AVERBACAO_RECENTE + 1)),
        ("DUE3", "EM_CARGA", agora, None),
    ]

    cursor = MagicMock()
    cursor.fetchall.return_value = rows

    conn = MagicMock()
    conn.cursor.return_value = cursor
    monkeypatch.setattr(update_dues.db_manager, "conn", conn)

    resultado = update_dues.carregar_dues_para_verificar(forcar_todas=True, limite=10)

    assert resultado is not None
    assert len(resultado["averbadas_recentes"]) == 1
    assert len(resultado["averbadas_antigas"]) == 1
    assert len(resultado["pendentes"]) == 1
