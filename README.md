# Sistema de Controle de DUEs e Drawback - Siscomex

Sistema para consulta, sincronizacao e normalizacao de dados de DU-Es (Declaracao Unica de Exportacao)
do Portal Unico de Comercio Exterior (Siscomex), com integracao ao SAP HANA e persistencia em PostgreSQL.

## Indice

- [Visao Geral](#visao-geral)
- [Quickstart](#quickstart)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Configuracao](#configuracao)
- [Uso](#uso)
- [Testes e Qualidade](#testes-e-qualidade)
- [Documentacao](#documentacao)
- [Deploy](#deploy)

## Visao Geral

Principais rotinas:
- Consulta SAP via AWS Athena para extrair chaves de NF-e de exportacao.
- Sincronizacao de DUEs novas com cache de vinculo NF-DUE.
- Atualizacao inteligente de DUEs existentes usando dataDeRegistro.
- Normalizacao de dados da API em tabelas relacionais no PostgreSQL.

## Quickstart

```bash
python -m pip install -r requirements.txt
cp config_exemplo.env config.env
python -c "from src.database.manager import db_manager; db_manager.conectar(); db_manager.criar_tabelas(); db_manager.desconectar()"
python -m src.main --status
```

## Estrutura do Projeto

O codigo principal fica em `src/`. Scripts auxiliares ficam em `scripts/`.

```
controle-siscomex/
  src/
    main.py
    core/
      constants.py
      exceptions.py
      logger.py
      metrics.py
    database/
      manager.py
      schema.py
    api/
      athena/
        client.py
      siscomex/
        token.py
        async_client.py
        rest_wrapper.py
        tabx.py
    cache/
      redis_cache.py
    processors/
      due.py
    sync/
      new_dues.py
      update_dues.py
  scripts/
    sync_diario.sh
    sync_diario.bat
  docs/
    SCHEMA_POSTGRESQL.md
    DIAGRAMA_RELACIONAMENTOS.md
    ANALISE_EXTRATO_DUE.md
```

Modulos opcionais (instalados via requirements, usados apenas quando importados):
- Async Siscomex: `src/api/siscomex/async_client.py` (aiohttp)
- Cache Redis: `src/cache/redis_cache.py` (redis)
- Wrapper REST: `src/api/siscomex/rest_wrapper.py` (requests)

## Configuracao

Copie `config_exemplo.env` para `config.env` e preencha as credenciais:

```env
SISCOMEX_CLIENT_ID=seu_client_id_aqui
SISCOMEX_CLIENT_SECRET=seu_client_secret_aqui
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=usuario
POSTGRES_PASSWORD=senha
POSTGRES_DB=siscomex_export_db
SISCOMEX_RATE_LIMIT_HOUR=1000
SISCOMEX_RATE_LIMIT_BURST=20
```

## Uso

Menu interativo:
```bash
python -m src.main
```

CLI:
```bash
python -m src.main --novas
python -m src.main --novas --workers 10
python -m src.main --atualizar
python -m src.main --completo
python -m src.main --atualizar-due 24BR0008165929
python -m src.main --atualizar-drawback 24BR0008165929,25BR0006149047
python -m src.main --atualizar-drawback
python -m src.main --status
```

## Testes e Qualidade

```bash
python -m pytest -q
python -m flake8 src tests
python -m mypy src
```

## Documentacao

- `docs/SCHEMA_POSTGRESQL.md` - Schema completo do banco
- `docs/DIAGRAMA_RELACIONAMENTOS.md` - Diagrama entre tabelas
- `docs/ANALISE_EXTRATO_DUE.md` - Extracao de dados para PDF
- `docs/MELHORIAS_PROPOSTAS.md` - Plano de melhorias e progresso

## Deploy

- `DEPLOY_DOKPLOY.md` - Deploy no Dokploy (Docker)
- `TUTORIAL_TESTES_VPS.md` - Testes e validacao em VPS
