#!/bin/bash
set -e

echo "========================================="
echo "Sistema de Controle DUE - Siscomex"
echo "========================================="
echo "Data/Hora: $(date)"
echo "========================================="

# Verificar variáveis de ambiente críticas
echo "[INFO] Verificando variaveis de ambiente..."
MISSING_VARS=0

if [ -z "$POSTGRES_HOST" ]; then
    echo "[ERRO] POSTGRES_HOST nao configurado"
    MISSING_VARS=1
fi

if [ -z "$POSTGRES_USER" ]; then
    echo "[ERRO] POSTGRES_USER nao configurado"
    MISSING_VARS=1
fi

if [ -z "$POSTGRES_PASSWORD" ]; then
    echo "[ERRO] POSTGRES_PASSWORD nao configurado"
    MISSING_VARS=1
fi

if [ -z "$POSTGRES_DB" ]; then
    echo "[ERRO] POSTGRES_DB nao configurado"
    MISSING_VARS=1
fi

if [ -z "$SISCOMEX_CLIENT_ID" ]; then
    echo "[AVISO] SISCOMEX_CLIENT_ID nao configurado"
fi

if [ -z "$SISCOMEX_CLIENT_SECRET" ]; then
    echo "[AVISO] SISCOMEX_CLIENT_SECRET nao configurado"
fi

if [ -z "$AWS_ACCESS_KEY" ]; then
    echo "[AVISO] AWS_ACCESS_KEY nao configurado"
fi

if [ -z "$AWS_SECRET_KEY" ]; then
    echo "[AVISO] AWS_SECRET_KEY nao configurado"
fi

if [ $MISSING_VARS -eq 1 ]; then
    echo "[ERRO] Variaveis de ambiente obrigatorias faltando!"
    echo "[INFO] Configure as variaveis de ambiente no Dokploy"
    echo "[INFO] Consulte DEPLOY_DOKPLOY.md para mais informacoes"
fi

# Verificar conexão com PostgreSQL (apenas se variáveis estiverem configuradas)
if [ $MISSING_VARS -eq 0 ]; then
    echo "[INFO] Verificando conexao com PostgreSQL..."
    python3 -c "from db_manager import db_manager; db_manager.conectar() and db_manager.desconectar() or exit(1)" 2>/dev/null && echo "[OK] Conexao com PostgreSQL OK" || echo "[AVISO] Nao foi possivel conectar ao PostgreSQL (verifique firewall/rede)"
else
    echo "[AVISO] Pulando verificacao de conexao (variaveis nao configuradas)"
fi

# Executar primeira sincronizacao ao iniciar (opcional)
# Descomente a linha abaixo se desejar executar ao iniciar o container
# python3 main.py --completo

echo "[INFO] Iniciando cron daemon..."
echo "[INFO] Agendamento configurado para executar diariamente as 06:00 (horario de Brasilia)"

# Iniciar cron em foreground
exec "$@"
