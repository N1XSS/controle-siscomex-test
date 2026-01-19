"""Async client for Siscomex DUE API."""

from __future__ import annotations

import asyncio
from typing import Any, AsyncGenerator

try:
    import aiohttp
except ImportError as exc:  # pragma: no cover - optional dependency
    raise ImportError(
        "aiohttp is required for AsyncSiscomexClient. Install with `pip install aiohttp`."
    ) from exc

from src.api.siscomex.token import SharedTokenManager
from src.core.logger import logger


class AsyncSiscomexClient:
    """Cliente assincrono para consultas de DUE."""

    def __init__(self, token_manager: SharedTokenManager) -> None:
        """Inicializa o cliente com token manager compartilhado."""
        self.token_manager = token_manager
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Garante uma sessao HTTP ativa com headers atualizados."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(headers=self.token_manager.obter_headers())
        return self._session

    async def consultar_due(self, numero_due: str) -> dict[str, Any]:
        """Consulta uma DUE de forma assincrona.

        Args:
            numero_due: Numero da DUE.

        Returns:
            Payload da DUE.
        """
        session = await self._get_session()
        url = f"https://portalunico.siscomex.gov.br/due/api/ext/due/{numero_due}"

        async with session.get(url) as response:
            response.raise_for_status()
            return await response.json()

    async def consultar_dues_batch(
        self,
        numeros_due: list[str],
        max_concurrent: int = 5,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Consulta multiplas DUEs com concorrencia limitada.

        Args:
            numeros_due: Lista de DUEs.
            max_concurrent: Limite de concorrencia.

        Yields:
            Payloads individuais das DUEs.
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def fetch_with_semaphore(numero: str) -> dict[str, Any]:
            async with semaphore:
                return await self.consultar_due(numero)

        tasks = [fetch_with_semaphore(numero) for numero in numeros_due]
        for coro in asyncio.as_completed(tasks):
            yield await coro

    async def close(self) -> None:
        """Fecha a sessao HTTP."""
        if self._session and not self._session.closed:
            await self._session.close()
            logger.info("Async Siscomex session closed")
