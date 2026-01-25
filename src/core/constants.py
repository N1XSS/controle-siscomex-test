"""Constantes compartilhadas pelo sistema."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Use an absolute path so config.env loads correctly even when cwd is elsewhere.
ENV_CONFIG_FILE = str(PROJECT_ROOT / "config.env")

# Carregar variaveis do .env antes de ler configuracoes.
# Em producao (ex: Dokploy), prefira variables do ambiente.
USE_DOTENV = os.getenv("USE_DOTENV", "true").strip().lower() in {"1", "true", "yes", "y", "on"}
if USE_DOTENV:
    load_dotenv(ENV_CONFIG_FILE, override=False)
SCRIPTS_DIR = "scripts"

SCRIPT_SAP = "src.api.athena.client"
SCRIPT_SYNC_NOVAS = "src.sync.new_dues"
SCRIPT_SYNC_ATUALIZAR = "src.sync.update_dues"

LOGS_DIR = "logs"

# =============================================================================
# LIMITES DE API SISCOMEX
# =============================================================================
SISCOMEX_RATE_LIMIT_HOUR = int(os.getenv("SISCOMEX_RATE_LIMIT_HOUR", "1000"))
SISCOMEX_RATE_LIMIT_BURST = int(os.getenv("SISCOMEX_RATE_LIMIT_BURST", "20"))
SISCOMEX_TOKEN_VALIDITY_MIN = 60
SISCOMEX_TOKEN_SAFETY_MARGIN_MIN = 2
SISCOMEX_AUTH_INTERVAL_SEC = 60
SISCOMEX_SAFE_REQUEST_LIMIT = int(os.getenv("SISCOMEX_SAFE_REQUEST_LIMIT", "950"))

# =============================================================================
# CONSULTAS SUPLEMENTARES DUE
# =============================================================================
def _get_bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


SISCOMEX_FETCH_ATOS_SUSPENSAO = _get_bool_env("SISCOMEX_FETCH_ATOS_SUSPENSAO", True)
SISCOMEX_FETCH_ATOS_ISENCAO = _get_bool_env("SISCOMEX_FETCH_ATOS_ISENCAO", False)
SISCOMEX_FETCH_EXIGENCIAS_FISCAIS = _get_bool_env("SISCOMEX_FETCH_EXIGENCIAS_FISCAIS", True)

# =============================================================================
# LIMITES DE PROCESSAMENTO
# =============================================================================
# MAX_CONSULTAS_NF_POR_EXECUCAO foi removido - o sistema agora confia no
# rate limiting inteligente que detecta PUCX-ER1001 e pausa automaticamente.
# Conforme docs.portalunico.siscomex.gov.br, o bloqueio é progressivo:
# - 1a violação: bloqueio até fim da hora atual
# - 2a violação: +1 hora de penalidade
# - 3a+ violação: +2 horas de penalidade
MAX_ATUALIZACOES_POR_EXECUCAO = 500
HORAS_PARA_ATUALIZACAO = 24
DIAS_AVERBACAO_RECENTE = 7

# =============================================================================
# PARALELIZAÇÃO DE DOWNLOADS
# =============================================================================
# Otimização: Aumentado de 5 para 20 workers para melhorar throughput
# Com 4 requisições por DUE (principal + atos + exigências), cada worker
# processa ~8s. Com 20 workers: 50 DUEs em ~1.5min (vs 6min com 5 workers)
DUE_DOWNLOAD_WORKERS = 20  # Número de threads paralelas para download de DUEs
ENABLE_PARALLEL_DOWNLOADS = True  # Feature flag para ativar/desativar paralelização

# =============================================================================
# TIMEOUTS E RETRIES
# =============================================================================
DB_CONNECTION_TIMEOUT_SEC = 30
DEFAULT_HTTP_TIMEOUT_SEC = 10
HTTP_REQUEST_TIMEOUT_SEC = 30
HTTP_MAX_RETRIES = 3
HTTP_RETRY_BACKOFF_FACTOR = 0.5

# =============================================================================
# SITUACOES DUE
# =============================================================================
SITUACOES_CANCELADAS = frozenset(
    [
        "CANCELADA_POR_EXPIRACAO_DE_PRAZO",
        "CANCELADA_PELA_ADUANA_A_PEDIDO_DO_EXPORTADOR",
        "CANCELADA_PELO_EXPORTADOR",
        "CANCELADA_PELO_SISCOMEX",
    ]
)

SITUACOES_AVERBADAS = frozenset(
    [
        "AVERBADA_SEM_DIVERGENCIA",
        "AVERBADA_COM_DIVERGENCIA",
    ]
)

SITUACOES_PENDENTES = frozenset(
    [
        "EM_CARGA",
        "DESEMBARACADA",
        "AGUARDANDO_AVERBACAO",
        "EM_ELABORACAO",
        "REGISTRADA",
        "PARAMETRIZADA_VERDE",
        "PARAMETRIZADA_AMARELO",
        "PARAMETRIZADA_VERMELHO",
        "INTERROMPIDA",
    ]
)

# =============================================================================
# DIAS PARA VERIFICACAO
# =============================================================================
DIAS_VERIFICACAO_AVERBADA = 7

# =============================================================================
# CONFIGURACAO AWS ATHENA
# =============================================================================
ATHENA_DEFAULT_REGION = "us-east-1"
ATHENA_QUERY_RESULT_LOCATION = "s3://aws-athena-query-results-default/"

# =============================================================================
# STATUS E INTERVALOS LOCAIS
# =============================================================================
DEFAULT_DB_STATUS_INTERVAL_HOURS = 24

# =============================================================================
# WHATSAPP NOTIFICATIONS (EVOLUTION API)
# =============================================================================

WHATSAPP_ENABLED = os.getenv('WHATSAPP_ENABLED', 'false').lower() == 'true'
WHATSAPP_BASE_URL = os.getenv('WHATSAPP_BASE_URL', '')
WHATSAPP_INSTANCE = os.getenv('WHATSAPP_INSTANCE', '')
WHATSAPP_APIKEY = os.getenv('WHATSAPP_APIKEY', '')
WHATSAPP_REMOTE_JID = os.getenv('WHATSAPP_REMOTE_JID', '')  # Número direto do destinatário
