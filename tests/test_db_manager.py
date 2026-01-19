"""Tests for DatabaseManager helpers."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.database.manager import DatabaseManager


def _make_conn(raise_on_execute: bool = False) -> tuple[MagicMock, MagicMock]:
    conn = MagicMock()
    cursor = MagicMock()
    if raise_on_execute:
        cursor.execute.side_effect = RuntimeError("boom")

    conn.cursor.return_value.__enter__.return_value = cursor
    return conn, cursor


def test_executar_query_commits() -> None:
    manager = DatabaseManager()
    conn, cursor = _make_conn()
    manager.conn = conn

    ok = manager.executar_query("SELECT 1")

    assert ok is True
    cursor.execute.assert_called_once()
    conn.commit.assert_called_once()


def test_executar_query_rollback_on_error() -> None:
    manager = DatabaseManager()
    conn, cursor = _make_conn(raise_on_execute=True)
    manager.conn = conn

    ok = manager.executar_query("SELECT 1")

    assert ok is False
    cursor.execute.assert_called_once()
    conn.rollback.assert_called_once()
