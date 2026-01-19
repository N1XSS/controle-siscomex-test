---
status: filled
generated: 2026-01-17
updated: 2026-01-17
version: 2.0.0
---

# Project Overview

## Problema que Resolve

Sistema completo para consulta, sincronização e normalização de dados de DU-Es (Declaração Única de Exportação) do Portal Único de Comércio Exterior (Siscomex), com integração ao SAP HANA e persistência em PostgreSQL.

**Versão 2.0.0** - Arquitetura modular refatorada com estrutura profissional.

**Beneficiários:**
- Equipes de exportação que precisam rastrear DUEs
- Gestores que precisam de visibilidade sobre processos de exportação
- Analistas fiscais que precisam de dados estruturados para análise
- Sistemas que precisam integrar dados do Siscomex

## Quick Facts

- **Root path**: `c:\Users\marcos.colombo\OneDrive\Desenvolvimento\controle-siscomex`
- **Version**: 2.0.0 (arquitetura modular)
- **Primary language**: Python 3.10+
- **Database**: PostgreSQL (37 tabelas)
- **External APIs**: Siscomex Portal Único, SAP HANA (via AWS Athena)
- **Deployment**: Docker/Dokploy (VPS)
- **Architecture**: Modular package structure (`src/`)
- **Testing**: pytest com cobertura
- **CI/CD**: GitHub Actions
- **Code Quality**: Black, Flake8, MyPy, Pre-commit hooks

## Entry Points

**Ponto de entrada principal:**
- [`main.py`](../main.py) - Wrapper que importa de `src.main`
- [`src/main.py`](../src/main.py) - Menu interativo e CLI para orquestração (código principal)

**Módulos principais (`src/`):**
- [`src/sync/new_dues.py`](../src/sync/new_dues.py) - Sincronização de novas DUEs
- [`src/sync/update_dues.py`](../src/sync/update_dues.py) - Atualização de DUEs existentes  
- [`src/processors/due.py`](../src/processors/due.py) - Processamento e normalização de DUEs
- [`src/database/manager.py`](../src/database/manager.py) - Gerenciador PostgreSQL
- [`src/api/siscomex/token.py`](../src/api/siscomex/token.py) - Autenticação Siscomex
- [`src/api/athena/client.py`](../src/api/athena/client.py) - Cliente AWS Athena (SAP)
- [`src/scripts/install.py`](../src/scripts/install.py) - Script de instalação

**Scripts legados (retrocompatibilidade):**
- `consulta_sap.py`, `sync_novas.py`, `sync_atualizar.py`, etc. - Mantidos para compatibilidade

## Key Exports

**Classes principais:**
- [`DatabaseManager`](../db_manager.py#L54) - Gerenciador de conexão e operações PostgreSQL
- [`SharedTokenManager`](../token_manager.py#L26) - Gerenciador singleton de autenticação Siscomex

**Funções principais:**
- `sincronizar_novas()` - Orquestra sincronização de novas DUEs
- `atualizar_existentes()` - Orquestra atualização de DUEs existentes
- `atualizar_due_especifica()` - Atualiza uma DUE específica
- `atualizar_drawback()` - Atualiza apenas atos concessórios de drawback
- `processar_dados_due()` - Normaliza dados da API em 24 tabelas relacionais

## File Structure & Code Organization

### Arquitetura Modular v2.0 (`src/`)

**Core do sistema:**
- **`src/main.py`** — Ponto de entrada principal refatorado. Menu interativo e CLI
- **`src/core/`** — Núcleo do sistema
  - `constants.py` — Constantes compartilhadas (timeouts, limites, situações)
  - `logger.py` — Sistema de logging centralizado
  - `exceptions.py` — Exceções personalizadas
  - `metrics.py` — Métricas e monitoramento

**APIs externas:**
- **`src/api/siscomex/`** — Cliente Siscomex Portal Único
  - `token.py` — Autenticação OAuth2 e gerenciamento de tokens
  - `rest_wrapper.py` — Wrapper REST da API
  - `async_client.py` — Cliente assíncrono (opcional)
  - `tabx.py` — Download de tabelas TABX
- **`src/api/athena/`** — Cliente AWS Athena
  - `client.py` — Cliente para consulta SAP HANA via Athena

**Banco de dados:**
- **`src/database/`** — Camada de dados
  - `manager.py` — Gerenciador de conexão e operações PostgreSQL
  - `schema.py` — DDL das 37 tabelas (23 DUE + 14 suporte)

**Processamento:**
- **`src/processors/`** — Processadores de dados
  - `due.py` — Processamento e normalização de DUEs em 24 tabelas

**Sincronização:**
- **`src/sync/`** — Lógica de sincronização
  - `new_dues.py` — Sincronização de novas DUEs com cache inteligente
  - `update_dues.py` — Atualização de DUEs existentes com verificação por `dataDeRegistro`

**Cache (opcional):**
- **`src/cache/`** — Sistema de cache
  - `redis_cache.py` — Implementação Redis para cache distribuído

**Scripts utilitários:**
- **`src/scripts/`** — Scripts auxiliares
  - `install.py` — Script de instalação e configuração

### Scripts Legados (Retrocompatibilidade)

Mantidos no root para compatibilidade com scripts existentes:
- **`consulta_sap.py`** — Wrapper legado (chama `src.api.athena`)
- **`sync_novas.py`** — Wrapper legado (chama `src.sync.new_dues`)
- **`sync_atualizar.py`** — Wrapper legado (chama `src.sync.update_dues`)
- **`due_processor.py`** — Wrapper legado (chama `src.processors.due`)
- **`db_manager.py`** — Wrapper legado (chama `src.database.manager`)
- **`token_manager.py`** — Wrapper legado (chama `src.api.siscomex.token`)

### Testes

- **`tests/`** — Suite de testes
  - `conftest.py` — Configuração pytest
  - `test_due_processor.py` — Testes do processador
  - `test_token_manager.py` — Testes de autenticação

### Configuração e Deploy

- **`pyproject.toml`** — Configuração do projeto Python (Poetry/PEP 621)
- **`requirements.txt`** — Dependências pip (gerado do pyproject.toml)
- **`config_exemplo.env`** — Template de configuração
- **`.pre-commit-config.yaml`** — Hooks pre-commit (Black, Flake8, MyPy)
- **`.flake8`** — Configuração do linter
- **`.github/workflows/tests.yml`** — CI/CD GitHub Actions
- **`Dockerfile`** — Container Docker
- **`docker-compose.yml`** — Orquestração Docker
- **`entrypoint.sh`** — Inicialização do container

### Documentação

- **`docs/`** — Documentação técnica
  - `SCHEMA_POSTGRESQL.md` — Schema completo do banco
  - `DIAGRAMA_RELACIONAMENTOS.md` — Relacionamentos entre tabelas
  - `ANALISE_EXTRATO_DUE.md` — Análise PDF vs banco + queries
  - `MELHORIAS_PROPOSTAS.md` — Propostas de melhorias
  - Outros arquivos técnicos
- **`.context/`** — Contexto AI-Coders (este documento)
- **`.serena/`** — Configuração MCP Serena

### Scripts de Agendamento

- **`scripts/`** — Scripts de automação
  - `sync_diario.sh` — Cron Linux
  - `sync_diario.bat` — Task Scheduler Windows

## Technology Stack Summary

### Runtime & Language
- **Python 3.10+** — Linguagem principal com type hints
- **PostgreSQL** — Banco de dados relacional (37 tabelas)

### Core Dependencies
- **psycopg2-binary >=2.9.9** — Driver PostgreSQL
- **requests >=2.31.0** — Cliente HTTP para APIs
- **boto3 >=1.34.0** — SDK AWS (Athena, S3)
- **pandas >=2.1.0** — Manipulação e análise de dados
- **python-dotenv >=1.0.0** — Gerenciamento de variáveis de ambiente

### Optional Dependencies
- **aiohttp >=3.9.0** — Cliente HTTP assíncrono
- **redis >=5.0.0** — Cache distribuído

### Development Tools
- **pytest >=7.4.0** — Framework de testes
- **pytest-cov >=4.1.0** — Cobertura de código
- **pytest-mock >=3.12.0** — Mocking para testes
- **black >=23.0.0** — Formatação automática de código
- **flake8 >=6.1.0** — Linting e análise estática
- **mypy >=1.7.0** — Verificação de tipos estáticos
- **pre-commit >=3.6.0** — Git hooks automáticos

### Quality Assurance
- **Black** — Code formatter (line-length: 100)
- **Flake8** — Linter
- **MyPy** — Type checker
- **Pre-commit hooks** — Validação automática antes de commits
- **GitHub Actions** — CI/CD pipeline

### Infrastructure
- **Docker** — Containerização
- **Dokploy** — Plataforma de deploy (VPS)
- **Cron/Task Scheduler** — Agendamento de tarefas
- **Redis (opcional)** — Cache distribuído

## Core Framework Stack

### Backend/Data Layer
- **PostgreSQL** — Persistência de dados estruturados
- **Singleton Pattern** — `SharedTokenManager` para autenticação
- **Manager Pattern** — `DatabaseManager` para operações de banco

### External Integrations
- **Siscomex Portal Único API** — REST API OAuth2 para consulta de DUEs
- **AWS Athena** —** SQL sobre dados SAP HANA no S3
- **AWS S3** — Armazenamento de dados SAP

### Architectural Patterns
- **Modular Design** — Scripts independentes com responsabilidades claras
- **Cache Strategy** — Cache inteligente de vínculos NF-DUE e tokens
- **Optimization Strategy** — Verificação inteligente para evitar requisições desnecessárias
- **Normalization** — Dados da API normalizados em 24 tabelas relacionais

## UI & Interaction Libraries

Este é um sistema backend/CLI, sem interface gráfica. Interação via:
- **Menu interativo** — `main.py` sem argumentos
- **CLI arguments** — Argumentos de linha de comando para automação
- **Logs estruturados** — Saída formatada para acompanhamento

## Development Tools Overview

### Setup Inicial
```bash
# Instalar dependências
pip install -r requirements.txt

# Configurar credenciais
cp config_exemplo.env config.env
# Editar config.env com credenciais reais

# Criar tabelas no banco
python -c "from db_manager import db_manager; db_manager.conectar(); db_manager.criar_tabelas(); db_manager.desconectar()"
```

### Execução
```bash
# Menu interativo
python main.py

# Comandos CLI
python main.py --novas              # Sincronizar novas DUEs
python main.py --atualizar          # Atualizar DUEs existentes
python main.py --completo           # Sincronização completa
python main.py --atualizar-due 24BR...  # Atualizar DUE específica
python main.py --status             # Status do sistema
```

### Agendamento
- **Linux**: Usar `scripts/sync_diario.sh` com cron
- **Windows**: Usar `scripts/sync_diario.bat` com Task Scheduler
- **Docker**: Usar `cron_job.sh` no container

Ver [Development Workflow](./development-workflow.md) para mais detalhes.

## Getting Started Checklist

1. ✅ Instalar dependências: `pip install -r requirements.txt`
2. ✅ Configurar credenciais: Copiar `config_exemplo.env` para `config.env` e preencher
3. ✅ Criar tabelas: Executar script de criação via `db_manager`
4. ✅ Testar conexão: `python main.py --status`
5. ✅ Executar primeira sincronização: `python main.py --novas`
6. ✅ Revisar [Development Workflow](./development-workflow.md) para tarefas do dia a dia
7. ✅ Configurar agendamento: Usar scripts em `scripts/` conforme ambiente

## Next Steps

### Para Desenvolvedores
- Revisar [Architecture](./architecture.md) para entender a arquitetura completa
- Consultar [Data Flow](./data-flow.md) para entender o fluxo de dados
- Ver [Testing Strategy](./testing-strategy.md) para estratégia de testes

### Para Deploy
- Seguir [DEPLOY_DOKPLOY.md](../DEPLOY_DOKPLOY.md) para deploy em VPS
- Consultar [TUTORIAL_TESTES_VPS.md](../TUTORIAL_TESTES_VPS.md) para testes pós-deploy

### Documentação Externa
- **Siscomex Portal Único**: https://portalunico.siscomex.gov.br
- **PostgreSQL Docs**: https://www.postgresql.org/docs/
- **AWS Athena Docs**: https://docs.aws.amazon.com/athena/

### Stakeholders
- **Equipe de Exportação** — Usuários finais que precisam rastrear DUEs
- **Analistas Fiscais** — Usuários que analisam dados estruturados
- **Equipe de TI** — Mantenedores do sistema e integrações
