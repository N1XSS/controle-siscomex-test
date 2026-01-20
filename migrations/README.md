# Migrations - Sistema Controle Siscomex

Este diretório contém as migrations (migrações) do banco de dados PostgreSQL.

## Como Executar uma Migration

### Opção 1: Via psql (Recomendado)

```bash
# Conectar ao banco e executar a migration
psql -h 31.97.22.234 -p 5440 -U gestor_siscomex -d siscomex_export_db -f migrations/001_remove_nonexistent_api_fields.sql
```

### Opção 2: Via Python

```python
import psycopg2
from pathlib import Path

# Configuração da conexão
conn = psycopg2.connect(
    host="31.97.22.234",
    port=5440,
    database="siscomex_export_db",
    user="gestor_siscomex",
    password="SUA_SENHA"
)

# Ler e executar a migration
migration_file = Path("migrations/001_remove_nonexistent_api_fields.sql")
with open(migration_file, 'r', encoding='utf-8') as f:
    sql = f.read()

with conn.cursor() as cur:
    cur.execute(sql)
    conn.commit()

print("Migration executada com sucesso!")
conn.close()
```

### Opção 3: Via código do projeto

```python
from src.database.manager import db_manager
from pathlib import Path

if db_manager.conectar():
    migration_file = Path("migrations/001_remove_nonexistent_api_fields.sql")

    with open(migration_file, 'r', encoding='utf-8') as f:
        sql = f.read()

    with db_manager.conn.cursor() as cur:
        cur.execute(sql)
        db_manager.conn.commit()

    print("Migration executada com sucesso!")
    db_manager.desconectar()
```

## Migrations Disponíveis

### 001_remove_nonexistent_api_fields.sql
**Data:** 2026-01-20
**Descrição:** Remove campos que não existem na API Siscomex
**Impacto:** Nenhum - Estes campos nunca foram populados
**Tabelas afetadas:**
- `due_eventos_historico`: Remove colunas `detalhes`, `motivo`, `tipo_evento`, `data`
- `due_itens`: Remove coluna `exportador_nome`

**Status:** ⏳ Pendente de execução

## Ordem de Execução

Execute as migrations em ordem numérica:
1. `001_remove_nonexistent_api_fields.sql`
2. (futuras migrations)

## Rollback

Cada migration possui instruções de rollback comentadas no final do arquivo. Use apenas se necessário desfazer a migration.

## Checklist Antes de Executar

- [ ] Fazer backup do banco de dados
- [ ] Revisar o conteúdo da migration
- [ ] Confirmar que o ambiente está correto (dev/prod)
- [ ] Testar em ambiente de desenvolvimento primeiro
- [ ] Executar a migration
- [ ] Validar que as mudanças foram aplicadas corretamente
- [ ] Testar a aplicação após a migration

## Validação Pós-Migration

Após executar a migration 001:

```sql
-- Verificar se as colunas foram removidas
SELECT column_name
FROM information_schema.columns
WHERE table_name = 'due_eventos_historico'
AND column_name IN ('detalhes', 'motivo', 'tipo_evento', 'data');
-- Deve retornar 0 linhas

SELECT column_name
FROM information_schema.columns
WHERE table_name = 'due_itens'
AND column_name = 'exportador_nome';
-- Deve retornar 0 linhas
```

## Logs

Registre aqui quando cada migration for executada:

| Migration | Data Execução | Executor | Ambiente | Observações |
|-----------|---------------|----------|----------|-------------|
| 001 | | | | |
