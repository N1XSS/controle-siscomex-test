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
    python3 << 'PYTHON_SCRIPT'
from src.database.manager import db_manager
import sys

try:
    if db_manager.conectar():
        db_manager.desconectar()
        print("[OK] Conexao com PostgreSQL OK")
        sys.exit(0)
    else:
        print("[AVISO] Nao foi possivel conectar ao PostgreSQL (verifique firewall/rede)")
        sys.exit(1)
except Exception as e:
    print(f"[AVISO] Erro ao verificar conexao: {e}")
    sys.exit(1)
PYTHON_SCRIPT
    
    if [ $? -eq 0 ]; then
        echo "[OK] Verificacao de conexao concluida com sucesso"
    else
        echo "[AVISO] Verificacao de conexao falhou, mas continuando..."
    fi
else
    echo "[AVISO] Pulando verificacao de conexao (variaveis nao configuradas)"
fi

# Executar primeira sincronizacao ao iniciar (opcional)
# Descomente a linha abaixo se desejar executar ao iniciar o container
# python3 -m src.main --completo

echo "[INFO] Iniciando cron daemon..."
echo "[INFO] Agendamento configurado para executar diariamente as 06:00 (horario de Brasilia)"

# Iniciar cron em foreground
exec "$@"
