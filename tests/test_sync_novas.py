"""Tests for sync_novas helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from src.sync import new_dues


def test_carregar_nfs_sap_usa_postgres(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(new_dues.db_manager, "conn", object())
    monkeypatch.setattr(new_dues.db_manager, "obter_nfs_sap", lambda: ["1" * 44])

    resultado = new_dues.carregar_nfs_sap()

    assert resultado == ["1" * 44]


def test_carregar_nfs_sap_csv_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    csv_path = tmp_path / "nfe-sap.csv"
    csv_path.write_text("Chave NF;\n" + ("2" * 44) + ";\n", encoding="utf-8")

    monkeypatch.setattr(new_dues, "CAMINHO_NFE_SAP", str(csv_path))
    monkeypatch.setattr(new_dues.db_manager, "conn", None)
    monkeypatch.setattr(new_dues.db_manager, "conectar", lambda: False)

    resultado = new_dues.carregar_nfs_sap()

    assert resultado == ["2" * 44]
