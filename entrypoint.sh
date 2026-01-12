#!/bin/bash
set -e

echo "========================================="
echo "Sistema de Controle DUE - Siscomex"
echo "========================================="
echo "Data/Hora: $(date)"
echo "========================================="

# Verificar se o arquivo .env existe
if [ ! -f .env ] && [ ! -f config.env ]; then
    echo "[AVISO] Arquivo .env ou config.env nao encontrado"
    echo "[AVISO] Certifique-se de configurar as variaveis de ambiente no Dokploy"
fi

# Executar migração/setup do banco (se necessário)
echo "[INFO] Verificando conexao com PostgreSQL..."
python3 -c "from db_manager import db_manager; db_manager.conectar() and db_manager.desconectar() or exit(1)" 2>/dev/null && echo "[OK] Conexao com PostgreSQL OK" || echo "[AVISO] Nao foi possivel conectar ao PostgreSQL"

# Executar primeira sincronizacao ao iniciar (opcional)
# Descomente a linha abaixo se desejar executar ao iniciar o container
# python3 main.py --completo

echo "[INFO] Iniciando cron daemon..."
echo "[INFO] Agendamento configurado para executar diariamente as 06:00 (horario de Brasilia)"

# Iniciar cron em foreground
exec "$@"
