"""Validador de configurações do sistema."""

from __future__ import annotations

import os
from src.core.logger import logger


def validar_configuracao() -> bool:
    """Valida todas as variáveis de ambiente obrigatórias no startup.

    Returns:
        True se todas as configurações estão válidas, False caso contrário
    """
    required_vars = {
        # Credenciais Siscomex
        'SISCOMEX_CLIENT_ID': 'Client ID do Siscomex',
        'SISCOMEX_CLIENT_SECRET': 'Client Secret do Siscomex',

        # PostgreSQL
        'POSTGRES_HOST': 'Host do PostgreSQL',
        'POSTGRES_PORT': 'Porta do PostgreSQL',
        'POSTGRES_USER': 'Usuário do PostgreSQL',
        'POSTGRES_PASSWORD': 'Senha do PostgreSQL',
        'POSTGRES_DB': 'Nome do banco de dados',
    }

    optional_vars = {
        # AWS Athena (opcional)
        'AWS_REGION': 'Região AWS',
        'AWS_ATHENA_WORKGROUP': 'Workgroup do Athena',
        'AWS_ATHENA_OUTPUT_LOCATION': 'Local de saída do Athena',

        # WhatsApp (opcional)
        'WHATSAPP_ENABLED': 'Notificações WhatsApp habilitadas',
        'WHATSAPP_BASE_URL': 'URL base da Evolution API',
        'WHATSAPP_INSTANCE': 'Instância do WhatsApp',
        'WHATSAPP_APIKEY': 'API Key do WhatsApp',
        'WHATSAPP_REMOTE_JID': 'JID do destinatário',
    }

    missing_vars = []

    # Verificar variáveis obrigatórias
    for var, description in required_vars.items():
        value = os.getenv(var)
        if not value or value.strip() == '':
            missing_vars.append(f"  ❌ {var}: {description}")
            logger.error(f"Variável obrigatória ausente: {var}")

    if missing_vars:
        logger.error("=" * 60)
        logger.error("ERRO: Configurações obrigatórias ausentes")
        logger.error("=" * 60)
        for var in missing_vars:
            logger.error(var)
        logger.error("")
        logger.error("Configure as variáveis no arquivo config.env")
        logger.error("=" * 60)
        return False

    # Verificar variáveis opcionais (apenas aviso)
    missing_optional = []
    for var, description in optional_vars.items():
        value = os.getenv(var)
        if not value or value.strip() == '':
            missing_optional.append(f"  ⚠️  {var}: {description}")

    if missing_optional:
        logger.warning("Variáveis opcionais não configuradas:")
        for var in missing_optional:
            logger.warning(var)

    logger.info("✅ Configurações obrigatórias validadas com sucesso")
    return True


def validar_configuracao_postgres() -> bool:
    """Valida especificamente as configurações do PostgreSQL.

    Returns:
        True se as configurações do PostgreSQL estão válidas
    """
    postgres_vars = ['POSTGRES_HOST', 'POSTGRES_PORT', 'POSTGRES_USER',
                     'POSTGRES_PASSWORD', 'POSTGRES_DB']

    for var in postgres_vars:
        if not os.getenv(var):
            logger.error(f"Configuração PostgreSQL ausente: {var}")
            return False

    # Validar porta numérica
    try:
        port = int(os.getenv('POSTGRES_PORT', '0'))
        if port <= 0 or port > 65535:
            logger.error(f"Porta PostgreSQL inválida: {port}")
            return False
    except ValueError:
        logger.error(f"Porta PostgreSQL não é numérica: {os.getenv('POSTGRES_PORT')}")
        return False

    return True


def validar_configuracao_siscomex() -> bool:
    """Valida especificamente as configurações do Siscomex.

    Returns:
        True se as configurações do Siscomex estão válidas
    """
    client_id = os.getenv('SISCOMEX_CLIENT_ID')
    client_secret = os.getenv('SISCOMEX_CLIENT_SECRET')

    if not client_id or not client_secret:
        logger.error("Credenciais Siscomex ausentes")
        return False

    # Validar formato básico
    if len(client_id) < 10:
        logger.error("SISCOMEX_CLIENT_ID parece inválido (muito curto)")
        return False

    if len(client_secret) < 10:
        logger.error("SISCOMEX_CLIENT_SECRET parece inválido (muito curto)")
        return False

    return True
