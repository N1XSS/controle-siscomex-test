#!/bin/bash
# Script para testar conexão com PostgreSQL

echo "========================================="
echo "Teste de Conexão PostgreSQL"
echo "========================================="
echo ""

# Verificar se variáveis estão configuradas
if [ -z "$POSTGRES_HOST" ] || [ -z "$POSTGRES_PORT" ] || [ -z "$POSTGRES_USER" ] || [ -z "$POSTGRES_PASSWORD" ] || [ -z "$POSTGRES_DB" ]; then
    echo "[ERRO] Variáveis de ambiente não configuradas"
    exit 1
fi

echo "Configuração:"
echo "  Host: $POSTGRES_HOST"
echo "  Port: $POSTGRES_PORT"
echo "  User: $POSTGRES_USER"
echo "  Database: $POSTGRES_DB"
echo ""

# Teste 1: Ping
echo "[TESTE 1] Ping para $POSTGRES_HOST..."
if ping -c 2 -W 2 $POSTGRES_HOST > /dev/null 2>&1; then
    echo "  [OK] Host alcançável"
else
    echo "  [ERRO] Host não alcançável"
fi
echo ""

# Teste 2: Conectividade de porta
echo "[TESTE 2] Testando porta $POSTGRES_PORT..."
if command -v nc > /dev/null 2>&1; then
    if nc -zv -w 5 $POSTGRES_HOST $POSTGRES_PORT 2>&1 | grep -q "succeeded\|open"; then
        echo "  [OK] Porta acessível"
    else
        echo "  [ERRO] Porta não acessível ou timeout"
    fi
else
    echo "  [AVISO] nc não disponível, pulando teste"
fi
echo ""

# Teste 3: Conexão PostgreSQL
echo "[TESTE 3] Testando conexão PostgreSQL..."
python3 << EOF
import psycopg2
import sys

try:
    conn = psycopg2.connect(
        host='$POSTGRES_HOST',
        port=$POSTGRES_PORT,
        user='$POSTGRES_USER',
        password='$POSTGRES_PASSWORD',
        database='$POSTGRES_DB',
        connect_timeout=10
    )
    print("  [OK] Conectado com sucesso!")
    
    # Testar query simples
    cur = conn.cursor()
    cur.execute("SELECT version();")
    version = cur.fetchone()[0]
    print(f"  [OK] PostgreSQL versão: {version.split(',')[0]}")
    
    conn.close()
    sys.exit(0)
except psycopg2.OperationalError as e:
    print(f"  [ERRO] Erro de conexão: {e}")
    sys.exit(1)
except Exception as e:
    print(f"  [ERRO] Erro: {e}")
    sys.exit(1)
EOF
