"""REST wrapper for Siscomex API calls."""

from __future__ import annotations

from typing import Any

import requests

from src.api.siscomex.token import SharedTokenManager
from src.core.constants import DEFAULT_HTTP_TIMEOUT_SEC


class SiscomexRestClient:
    """Wrapper simples para chamadas REST autenticadas."""

    def __init__(self, token_manager: SharedTokenManager) -> None:
        """Inicializa o cliente com token manager compartilhado."""
        self.token_manager = token_manager
        self.session = requests.Session()

    def get(self, url: str, timeout: int = DEFAULT_HTTP_TIMEOUT_SEC) -> dict[str, Any]:
        """Executa GET autenticado.

        Args:
            url: Endpoint completo.
            timeout: Timeout em segundos.

        Returns:
            JSON retornado pela API.
        """
        response = self.session.get(url, headers=self.token_manager.obter_headers(), timeout=timeout)
        response.raise_for_status()
        return response.json()

    def post(self, url: str, payload: dict[str, Any], timeout: int = DEFAULT_HTTP_TIMEOUT_SEC) -> dict[str, Any]:
        """Executa POST autenticado.

        Args:
            url: Endpoint completo.
            payload: Payload JSON.
            timeout: Timeout em segundos.

        Returns:
            JSON retornado pela API.
        """
        response = self.session.post(
            url,
            json=payload,
            headers=self.token_manager.obter_headers(),
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()
