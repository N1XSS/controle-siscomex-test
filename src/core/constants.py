"""Constantes compartilhadas pelo sistema."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

ENV_CONFIG_FILE = "config.env"
SCRIPTS_DIR = "scripts"

SCRIPT_SAP = "src.api.athena.client"
SCRIPT_SYNC_NOVAS = "src.sync.new_dues"
SCRIPT_SYNC_ATUALIZAR = "src.sync.update_dues"

LOGS_DIR = "logs"

# =============================================================================
# LIMITES DE API SISCOMEX
# =============================================================================
SISCOMEX_RATE_LIMIT_HOUR = 1000
SISCOMEX_RATE_LIMIT_BURST = 20
SISCOMEX_TOKEN_VALIDITY_MIN = 60
SISCOMEX_TOKEN_SAFETY_MARGIN_MIN = 2
SISCOMEX_AUTH_INTERVAL_SEC = 60

# =============================================================================
# LIMITES DE PROCESSAMENTO
# =============================================================================
MAX_CONSULTAS_NF_POR_EXECUCAO = 400
MAX_ATUALIZACOES_POR_EXECUCAO = 500
HORAS_PARA_ATUALIZACAO = 24
DIAS_AVERBACAO_RECENTE = 7

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
