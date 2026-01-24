from __future__ import annotations

import json
import os
import pickle
import re
import sys
import threading
import time
from datetime import datetime, timedelta, timezone

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dotenv import load_dotenv

from src.core.constants import (
    DEFAULT_HTTP_TIMEOUT_SEC,
    ENV_CONFIG_FILE,
    HTTP_MAX_RETRIES,
    HTTP_RETRY_BACKOFF_FACTOR,
    SISCOMEX_AUTH_INTERVAL_SEC,
    SISCOMEX_RATE_LIMIT_BURST,
    SISCOMEX_RATE_LIMIT_HOUR,
    SISCOMEX_SAFE_REQUEST_LIMIT,
    SISCOMEX_TOKEN_SAFETY_MARGIN_MIN,
)
from src.core.logger import logger
from src.core.rate_limiter import TokenBucket

load_dotenv(ENV_CONFIG_FILE)

# Configurar encoding para Windows
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except (AttributeError, OSError):
        # Se não conseguir reconfigurar, continua normalmente
        pass

# Configuracoes da API
URL_AUTH = "https://portalunico.siscomex.gov.br/portal/api/autenticar/chave-acesso"
TOKEN_CACHE_FILE = "token_cache.pkl"

class SharedTokenManager:
    """Gerencia tokens Siscomex com cache e sessao compartilhada.

    Otimizacoes principais:
        - Singleton para compartilhamento entre threads.
        - Cache persistente de token com margem de seguranca.
        - Reuso de sessao HTTP com pool e retries.
        - Controle de intervalo minimo entre autenticacoes.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls: type["SharedTokenManager"]) -> "SharedTokenManager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self) -> None:
        if self._initialized:
            return
            
        self.set_token = None
        self.csrf_token = None
        self.expiracao = None
        self.session = None
        self.client_id = None
        self.client_secret = None
        self.ultima_autenticacao = None  # Controle de intervalo mínimo de 60s
        self._request_lock = threading.Lock()
        self._request_window_start = self._current_window_start()
        self._requests_in_window = 0
        self._safe_request_limit = self._load_safe_request_limit()
        self._blocked_until: datetime | None = None  # Horário de desbloqueio PUCX-ER1001
        
        self._setup_session()
        self._limiter = self._build_rate_limiter()
        self._carregar_token_cache()  # Carregar token do cache se existe
        self._initialized = True
    
    def _setup_session(self) -> None:
        """Configura a sessao HTTP com retries e pool."""
        self.session = requests.Session()
        
        # Configurar retry strategy
        retry_strategy = Retry(
            total=HTTP_MAX_RETRIES,
            backoff_factor=HTTP_RETRY_BACKOFF_FACTOR,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        
        # Configurar adapter com pool de conexoes
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=20,
            pool_maxsize=20
        )
        
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def _build_rate_limiter(self) -> TokenBucket | None:
        """Cria um rate limiter baseado em configuracao."""
        try:
            limit_hour = int(os.getenv("SISCOMEX_RATE_LIMIT_HOUR", SISCOMEX_RATE_LIMIT_HOUR))
            burst = int(os.getenv("SISCOMEX_RATE_LIMIT_BURST", SISCOMEX_RATE_LIMIT_BURST))
        except ValueError:
            limit_hour = SISCOMEX_RATE_LIMIT_HOUR
            burst = SISCOMEX_RATE_LIMIT_BURST

        if limit_hour <= 0:
            return None

        rate_per_sec = limit_hour / 3600.0
        return TokenBucket(rate_per_sec=rate_per_sec, capacity=burst)

    def _load_safe_request_limit(self) -> int:
        """Carrega limite preventivo de requisicoes por hora."""
        try:
            return int(os.getenv("SISCOMEX_SAFE_REQUEST_LIMIT", SISCOMEX_SAFE_REQUEST_LIMIT))
        except ValueError:
            return SISCOMEX_SAFE_REQUEST_LIMIT

    def _current_window_start(self) -> datetime:
        """Retorna o inicio da janela da hora atual."""
        now = datetime.now()
        return now.replace(minute=0, second=0, microsecond=0)

    def _seconds_until_next_hour(self) -> float:
        """Calcula segundos restantes para a proxima hora cheia."""
        now = datetime.now()
        next_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        return max(0.0, (next_hour - now).total_seconds())

    def _wait_for_safe_limit(self) -> None:
        """Pausa automaticamente quando atingir limite preventivo ou bloqueio ativo.

        Verifica primeiro se há bloqueio PUCX-ER1001 ativo (para coordenar threads),
        depois verifica o limite preventivo de requisições por hora.
        """
        # Verificar se está em período de bloqueio PUCX-ER1001
        # Isso coordena todas as threads para aguardarem juntas
        if self._blocked_until is not None:
            wait = (self._blocked_until - datetime.now()).total_seconds()
            if wait > 0:
                logger.warning(
                    "⏸️  Bloqueio SISCOMEX ativo. Aguardando %.1f minutos até %s...",
                    wait / 60.0,
                    self._blocked_until.strftime("%H:%M:%S"),
                )
                time.sleep(wait + 1)

        if self._safe_request_limit <= 0:
            return

        while True:
            with self._request_lock:
                now = datetime.now()
                if now >= self._request_window_start + timedelta(hours=1):
                    self._request_window_start = self._current_window_start()
                    self._requests_in_window = 0

                if self._requests_in_window < self._safe_request_limit:
                    self._requests_in_window += 1
                    return

                wait_seconds = self._seconds_until_next_hour()
                logger.warning(
                    "⏸️  Limite preventivo SISCOMEX atingido (%s req/h). Aguardando %.1f minutos...",
                    self._safe_request_limit,
                    wait_seconds / 60.0,
                )

            time.sleep(wait_seconds + 1)

    def _parse_block_until(self, message: str) -> datetime | None:
        """Extrai horário de desbloqueio da mensagem PUCX-ER1001."""
        match = re.search(r"após as (\d{1,2}):(\d{2})(?::(\d{2}))?", message)
        if not match:
            return None

        hour = int(match.group(1))
        minute = int(match.group(2))
        second = int(match.group(3) or 0)
        now = datetime.now()
        desbloqueio = now.replace(hour=hour, minute=minute, second=second, microsecond=0)
        if desbloqueio <= now:
            desbloqueio += timedelta(days=1)
        return desbloqueio

    def _extract_rate_limit_wait(self, response: requests.Response) -> float | None:
        """Detecta bloqueio PUCX-ER1001 e retorna segundos de espera."""
        try:
            data = response.json()
        except Exception:
            return None

        if isinstance(data, dict) and data.get("code") == "PUCX-ER1001":
            message = data.get("message", "")
            desbloqueio = self._parse_block_until(message)
            if desbloqueio:
                wait_seconds = max(0.0, (desbloqueio - datetime.now()).total_seconds())
            else:
                wait_seconds = self._seconds_until_next_hour()

            logger.warning("⏸️  Bloqueio SISCOMEX detectado (PUCX-ER1001).")
            if message:
                logger.warning("📋 Mensagem: %s", message)
            logger.warning(
                "⏰ Aguardando até %s (%.1f minutos)...",
                desbloqueio.strftime("%H:%M:%S") if desbloqueio else "próxima hora",
                wait_seconds / 60.0,
            )
            return wait_seconds

        return None

    def request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Executa requisicao respeitando rate limit configurado.

        IMPORTANTE: Quando detecta bloqueio PUCX-ER1001, aguarda o tempo indicado
        mas NAO faz retry automatico. Conforme documentacao oficial do Siscomex,
        cada tentativa durante bloqueio AUMENTA a penalidade:
        - 1a violacao: bloqueio ate fim da hora atual
        - 2a violacao: +1 hora de penalidade
        - 3a+ violacao: +2 horas de penalidade

        A resposta de bloqueio é retornada para que o caller decida se quer
        tentar novamente após o desbloqueio.
        """
        self._wait_for_safe_limit()
        if self._limiter:
            self._limiter.acquire()

        resposta = self.session.request(method, url, **kwargs)

        # Detectar bloqueio PUCX-ER1001
        wait_seconds = self._extract_rate_limit_wait(resposta)
        if wait_seconds is not None:
            # Registrar horário de desbloqueio para coordenar outras threads
            self._blocked_until = datetime.now() + timedelta(seconds=wait_seconds)
            logger.info(
                "⏳ Iniciando pausa de %.1f minutos. Proximas requisicoes aguardarao automaticamente.",
                wait_seconds / 60.0,
            )
            time.sleep(wait_seconds + 1)
            self._blocked_until = None
            logger.info("✅ Periodo de bloqueio encerrado. Retomando operacoes.")

        return resposta
    
    def configurar_credenciais(self, client_id: str, client_secret: str) -> None:
        """Configura as credenciais para autenticacao.

        Args:
            client_id: Client ID do Siscomex.
            client_secret: Client Secret do Siscomex.
        """
        self.client_id = client_id
        self.client_secret = client_secret
    
    def token_valido(self) -> bool:
        """Verifica se o token ainda e valido.

        Returns:
            True quando o token atual ainda pode ser usado.
        """
        if not (self.set_token and self.csrf_token and self.expiracao):
            return False
        
        # Verificar se o token ainda não expirou (sem margem excessiva)
        # Usar apenas 2 minutos de margem para maximizar uso do token
        agora = datetime.utcnow()
        margem_seguranca = timedelta(minutes=SISCOMEX_TOKEN_SAFETY_MARGIN_MIN)
        
        return agora < (self.expiracao - margem_seguranca)
    
    def obter_headers(self) -> dict[str, str]:
        """Retorna os headers padrao para requisicoes autenticadas."""
        if not self.set_token or not self.csrf_token:
            raise RuntimeError("Token nao inicializado")
        return {
            'Authorization': self.set_token,
            'X-CSRF-Token': self.csrf_token,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    def autenticar(self, forcar_nova_auth: bool = False) -> bool:
        """Autentica e obtem novos tokens.

        Args:
            forcar_nova_auth: Quando True, ignora token em cache.

        Returns:
            True quando a autenticacao foi concluida com sucesso.
        """
        with self._lock:
            if not forcar_nova_auth and self.token_valido():
                tempo_restante = (self.expiracao - datetime.utcnow()).total_seconds() / 60
                logger.info(
                    "Reutilizando token existente (%.1f min restantes)",
                    tempo_restante,
                )
                return True

            if not self.client_id or not self.client_secret:
                logger.info("Credenciais nao configuradas")
                return False

            agora = datetime.utcnow()
            if self.ultima_autenticacao:
                tempo_desde_ultima = (agora - self.ultima_autenticacao).total_seconds()
                if tempo_desde_ultima < SISCOMEX_AUTH_INTERVAL_SEC:
                    tempo_restante = SISCOMEX_AUTH_INTERVAL_SEC - tempo_desde_ultima
                    logger.info("Aguardando %.1fs para respeitar intervalo minimo", tempo_restante)
                    time.sleep(tempo_restante)

            logger.info("Autenticando com Siscomex API...")
            try:
                headers_auth = {
                    "Client-Id": self.client_id,
                    "Client-Secret": self.client_secret,
                    "Role-Type": "IMPEXP",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                }
                response_auth = self.request(
                    "POST",
                    URL_AUTH,
                    json={},
                    headers=headers_auth,
                    timeout=DEFAULT_HTTP_TIMEOUT_SEC,
                )

                if response_auth.status_code == 422:
                    logger.info("Rate limiting detectado (422) - aguardando intervalo minimo")
                    time.sleep(SISCOMEX_AUTH_INTERVAL_SEC)
                    response_auth = self.request(
                        "POST",
                        URL_AUTH,
                        json={},
                        headers=headers_auth,
                        timeout=DEFAULT_HTTP_TIMEOUT_SEC,
                    )

                if response_auth.status_code == 401:
                    logger.info("Credenciais invalidas (401)")
                    return False
                if response_auth.status_code == 403:
                    logger.info("Acesso negado (403) - verificar permissoes")
                    return False

                response_auth.raise_for_status()

                self.set_token = response_auth.headers.get("set-token") or response_auth.headers.get("Set-Token")
                self.csrf_token = response_auth.headers.get("x-csrf-token") or response_auth.headers.get("X-CSRF-Token")
                if not (self.set_token and self.csrf_token):
                    logger.info("Tokens nao encontrados nos headers")
                    return False

                expiracao_header = response_auth.headers.get("x-csrf-expiration") or response_auth.headers.get(
                    "X-CSRF-Expiration"
                )
                if expiracao_header:
                    try:
                        expiracao_ms = int(expiracao_header)
                        self.expiracao = datetime.fromtimestamp(expiracao_ms / 1000, tz=timezone.utc).replace(
                            tzinfo=None
                        )
                    except (ValueError, TypeError):
                        self.expiracao = datetime.utcnow() + timedelta(minutes=60)
                else:
                    self.expiracao = datetime.utcnow() + timedelta(minutes=60)

                self.ultima_autenticacao = datetime.utcnow()
                self._salvar_token_cache()
                return True
            except Exception as exc:
                logger.info("Erro ao autenticar: %s", exc)
                return False

    def _salvar_token_cache(self) -> None:
        """Salva token no cache persistente."""
        if self.set_token and self.csrf_token and self.expiracao:
            try:
                cache_data = {
                    "set_token": self.set_token,
                    "csrf_token": self.csrf_token,
                    "expiracao": self.expiracao.isoformat(),
                    "cached_at": datetime.utcnow().isoformat(),
                    "ultima_autenticacao": self.ultima_autenticacao.isoformat() if self.ultima_autenticacao else None,
                }
                with open(TOKEN_CACHE_FILE, "wb") as f:
                    pickle.dump(cache_data, f)
                logger.info("Token salvo em cache: %s", TOKEN_CACHE_FILE)
            except Exception as exc:
                logger.info("Erro ao salvar cache do token: %s", exc)

    def _carregar_token_cache(self) -> None:
        """Carrega token do cache se válido"""
        try:
            if os.path.exists(TOKEN_CACHE_FILE):
                with open(TOKEN_CACHE_FILE, 'rb') as f:
                    cache_data = pickle.load(f)
                
                # Verificar se cache não está muito antigo (máximo 90 minutos = 60min + margem)
                cached_at = datetime.fromisoformat(cache_data['cached_at'])
                if (datetime.utcnow() - cached_at).total_seconds() > 5400:  # 90 minutos
                    logger.info("🗑️  Cache do token muito antigo (>90min) - ignorando")
                    os.remove(TOKEN_CACHE_FILE)
                    return
                
                # Restaurar dados do token
                self.set_token = cache_data['set_token']
                self.csrf_token = cache_data['csrf_token']
                self.expiracao = datetime.fromisoformat(cache_data['expiracao'])
                
                # Restaurar timestamp da última autenticação (se existir no cache)
                if 'ultima_autenticacao' in cache_data and cache_data['ultima_autenticacao']:
                    try:
                        self.ultima_autenticacao = datetime.fromisoformat(cache_data['ultima_autenticacao'])
                    except (ValueError, TypeError):
                        self.ultima_autenticacao = None
                
                if self.token_valido():
                    tempo_restante = (self.expiracao - datetime.utcnow()).total_seconds() / 60
                    logger.info(f"🔄 Token carregado do cache! Válido por mais {tempo_restante:.1f} minutos")
                else:
                    logger.info("🗑️  Token do cache expirado - removendo")
                    os.remove(TOKEN_CACHE_FILE)
                    self.set_token = None
                    self.csrf_token = None
                    self.expiracao = None
                    self.ultima_autenticacao = None
            else:
                logger.info("📝 Nenhum cache de token encontrado")
        except Exception as e:
            logger.info(f"⚠️  Erro ao carregar cache do token: {e}")
            # Limpar dados inválidos
            if os.path.exists(TOKEN_CACHE_FILE):
                os.remove(TOKEN_CACHE_FILE)
    
    def status_token(self) -> str:
        """Retorna status atual do token para debugging"""
        if not (self.set_token and self.csrf_token and self.expiracao):
            return "Token não inicializado"
        
        agora = datetime.utcnow()
        tempo_real_restante = (self.expiracao - agora).total_seconds() / 60
        
        if tempo_real_restante <= 0:
            return f"Token EXPIRADO há {abs(tempo_real_restante):.1f} minutos"
        elif self.token_valido():
            return f"Token VÁLIDO por mais {tempo_real_restante:.1f} minutos"
        else:
            return f"Token em MARGEM DE SEGURANÇA ({tempo_real_restante:.1f} min restantes)"

# Instancia global compartilhada
token_manager = SharedTokenManager()
