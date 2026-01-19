"""Redis cache helpers."""

from __future__ import annotations

import json
from typing import Any

try:
    import redis
except ImportError as exc:  # pragma: no cover - optional dependency
    raise ImportError(
        "redis is required for CacheManager. Install with `pip install redis`."
    ) from exc


class CacheManager:
    """Gerenciador de cache com Redis."""

    def __init__(self, redis_url: str = "redis://localhost:6379") -> None:
        """Inicializa o cliente Redis.

        Args:
            redis_url: URL de conexao do Redis.
        """
        self._client = redis.from_url(redis_url)
        self._default_ttl = 3600

    def get(self, key: str) -> dict[str, Any] | None:
        """Obtém valor do cache.

        Args:
            key: Chave do cache.

        Returns:
            Payload salvo ou None quando inexistente.
        """
        data = self._client.get(key)
        if data:
            return json.loads(data)
        return None

    def set(self, key: str, value: dict[str, Any], ttl: int | None = None) -> None:
        """Define valor no cache.

        Args:
            key: Chave do cache.
            value: Payload a armazenar.
            ttl: Tempo de vida em segundos.
        """
        self._client.setex(key, ttl or self._default_ttl, json.dumps(value))

    def invalidate(self, pattern: str) -> int:
        """Invalida chaves que correspondem ao padrao.

        Args:
            pattern: Padrao a ser invalidado.

        Returns:
            Quantidade de chaves removidas.
        """
        keys = self._client.keys(pattern)
        if keys:
            return self._client.delete(*keys)
        return 0
