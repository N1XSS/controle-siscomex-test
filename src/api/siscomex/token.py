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
from src.core.exceptions import RateLimitError
from src.notifications.whatsapp import notify_rate_limit

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
        self._token_refresh_lock = threading.Lock()  # Lock para renovação de token
        self._last_token_refresh: datetime | None = None  # Evitar renovações duplicadas

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
        """Rate limiter DESABILITADO para maximizar throughput.

        O TokenBucket serializa threads, causando gargalo com 20 workers paralelos.
        O sistema agora confia em:
        - Contagem de requisicoes por hora (_wait_for_safe_limit)
        - Tratamento automatico de PUCX-ER1001 com bloqueio global

        Para reativar, defina SISCOMEX_RATE_LIMIT_HOUR > 0 no config.env
        """
        # Desabilitado por padrao - confiar na contagem por hora + PUCX-ER1001
        # O tratamento de bloqueio e mais inteligente que o TokenBucket
        return None

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
        """Verifica limites e lança exceção se bloqueio ativo.

        Verifica primeiro se há bloqueio PUCX-ER1001 ativo,
        depois verifica o limite preventivo de requisições por hora.

        Raises:
            RateLimitError: Se houver bloqueio PUCX-ER1001 ativo ou limite preventivo atingido.
        """
        # Verificar se está em período de bloqueio PUCX-ER1001
        # NOVO: Lançar exceção em vez de fazer sleep - permite salvar dados parciais
        if self._blocked_until is not None:
            wait = (self._blocked_until - datetime.now()).total_seconds()
            if wait > 0:
                raise RateLimitError(
                    f"PUCX-ER1001: Bloqueio ativo. Desbloqueio às {self._blocked_until.strftime('%H:%M:%S')}",
                    retry_after=int(wait)
                )
            else:
                # Bloqueio expirou, limpar
                with self._request_lock:
                    self._blocked_until = None

        if self._safe_request_limit <= 0:
            return

        with self._request_lock:
            now = datetime.now()
            if now >= self._request_window_start + timedelta(hours=1):
                self._request_window_start = self._current_window_start()
                self._requests_in_window = 0

            if self._requests_in_window < self._safe_request_limit:
                self._requests_in_window += 1
                return

            wait_seconds = self._seconds_until_next_hour()

        # NOVO: Lançar exceção em vez de fazer sleep - permite salvar dados parciais
        raise RateLimitError(
            f"Limite preventivo SISCOMEX atingido ({self._safe_request_limit} req/h)",
            retry_after=int(wait_seconds)
        )

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

            unblock_time = desbloqueio.strftime("%H:%M:%S") if desbloqueio else "próxima hora"
            wait_minutes = wait_seconds / 60.0

            logger.warning("⏸️  Bloqueio SISCOMEX detectado (PUCX-ER1001).")
            if message:
                logger.warning("📋 Mensagem: %s", message)
            logger.warning("⏰ Aguardando até %s (%.1f minutos)...", unblock_time, wait_minutes)

            # Notificar via WhatsApp
            notify_rate_limit(wait_minutes=wait_minutes, unblock_time=unblock_time)

            return wait_seconds

        return None

    def _handle_401_with_retry(self, method: str, url: str, **kwargs) -> requests.Response:
        """Trata HTTP 401 com renovacao de token e retry.

        Usa lock para garantir que apenas 1 thread renova o token,
        enquanto outras aguardam e usam o token renovado.

        Args:
            method: Metodo HTTP (GET, POST, etc).
            url: URL da requisicao.
            **kwargs: Argumentos adicionais para a requisicao.

        Returns:
            Resposta HTTP apos retry com token renovado.
        """
        with self._token_refresh_lock:
            # Verificar se outra thread ja renovou recentemente (ultimos 5 segundos)
            if self._last_token_refresh:
                tempo_desde_refresh = (datetime.utcnow() - self._last_token_refresh).total_seconds()
                if tempo_desde_refresh < 5:
                    # Token foi renovado por outra thread, so atualizar headers e retry
                    logger.debug("Token ja renovado por outra thread, usando novo token...")
                    if 'headers' in kwargs:
                        kwargs['headers'] = self.obter_headers()
                    return self.session.request(method, url, **kwargs)

            # Renovar token
            logger.warning("🔄 HTTP 401 - Renovando token...")
            if self.autenticar(forcar_nova_auth=True):
                self._last_token_refresh = datetime.utcnow()
                logger.info("✅ Token renovado com sucesso")

                # Atualizar headers e retry
                if 'headers' in kwargs:
                    kwargs['headers'] = self.obter_headers()
                resposta = self.session.request(method, url, **kwargs)

                if resposta.status_code == 200:
                    logger.debug("✅ Requisicao bem-sucedida apos renovar token")
                return resposta
            else:
                logger.error("❌ Falha ao renovar token")
                # Retorna resposta vazia com status 401
                resp = requests.Response()
                resp.status_code = 401
                return resp

    def request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Executa requisicao com renovacao automatica de token.

        Otimizado para paralelismo:
        - NAO verifica token antes (sem overhead)
        - So renova quando receber 401
        - Lock garante apenas 1 renovacao por vez
        - Retry automatico apos renovar

        Quando detecta bloqueio PUCX-ER1001, aguarda o tempo indicado.
        Conforme documentacao oficial do Siscomex, cada tentativa durante
        bloqueio AUMENTA a penalidade.
        """
        # Verificar se e requisicao de autenticacao (nao precisa de token)
        is_auth_request = URL_AUTH in url

        # Rate limiting
        self._wait_for_safe_limit()
        if self._limiter:
            self._limiter.acquire()

        # Fazer requisicao SEM verificar token antes
        resposta = self.session.request(method, url, **kwargs)

        # Se recebeu 401 e nao e auth, renovar e retry
        if resposta.status_code == 401 and not is_auth_request:
            resposta = self._handle_401_with_retry(method, url, **kwargs)

        # Detectar bloqueio PUCX-ER1001 - LANÇAR EXCEÇÃO para salvar dados parciais
        wait_seconds = self._extract_rate_limit_wait(resposta)
        if wait_seconds is not None:
            with self._request_lock:
                # Setar horário de desbloqueio para outras threads saberem
                if self._blocked_until is None:
                    self._blocked_until = datetime.now() + timedelta(seconds=wait_seconds)
                    logger.warning(
                        "🚫 BLOQUEIO SISCOMEX (PUCX-ER1001) - Lançando exceção para salvar dados parciais..."
                    )

            # NOVO: Lançar exceção em vez de fazer sleep
            # Isso permite que o código de nível superior salve os dados antes de pausar
            raise RateLimitError(
                f"PUCX-ER1001: Rate limit atingido. Desbloqueio às {self._blocked_until.strftime('%H:%M:%S')}",
                retry_after=int(wait_seconds)
            )

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
