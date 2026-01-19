#!/bin/bash
# =============================================================================
# SYNC DIARIO - Sistema DUE Siscomex
# =============================================================================
# Este script realiza a sincronizacao completa diaria das DUEs.
# Sugestao: Agendar via cron para executar 1x ao dia (ex: 06:00)
#
# Uso manual:
#   ./sync_diario.sh
#
# Configurar cron (editar com: crontab -e):
#   0 6 * * * /caminho/para/controle-due-drawback/scripts/sync_diario.sh >> /var/log/due-sync.log 2>&1
# =============================================================================

# Diretorio do projeto
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

# Ativar ambiente virtual (se existir)
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

# Data e hora de inicio
echo "=============================================="
echo "SYNC DIARIO - $(date '+%d/%m/%Y %H:%M:%S')"
echo "=============================================="

# Verificar se Python esta disponivel
if ! command -v python3 &> /dev/null; then
    echo "[ERRO] Python3 nao encontrado!"
    exit 1
fi

# 1. Sincronizar novas NFs do SAP e buscar DUEs
echo ""
echo "[FASE 1] Sincronizando novas NFs..."
echo "----------------------------------------------"
python3 -m src.api.athena.client
python3 -m src.sync.new_dues

# 2. Atualizar DUEs existentes (pendentes e com mudancas)
echo ""
echo "[FASE 2] Atualizando DUEs existentes..."
echo "----------------------------------------------"
python3 -m src.sync.update_dues

# Resumo
echo ""
echo "=============================================="
echo "SYNC CONCLUIDO - $(date '+%d/%m/%Y %H:%M:%S')"
echo "=============================================="

# Desativar ambiente virtual
if [ -n "$VIRTUAL_ENV" ]; then
    deactivate
fi

exit 0
