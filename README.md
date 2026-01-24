# Sistema de Controle de DUEs - Siscomex

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Code Quality](https://img.shields.io/badge/Code%20Quality-A-brightgreen.svg)]()

Sistema enterprise para sincronização automatizada de DU-Es (Declaração Única de Exportação) do Portal Único Siscomex, com integração SAP HANA via AWS Athena e persistência relacional em PostgreSQL.

---

## 📋 Índice

- [Visão Geral](#visão-geral)
- [Características](#características)
- [Arquitetura](#arquitetura)
- [Instalação](#instalação)
- [Configuração](#configuração)
- [Uso](#uso)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Testes e Qualidade](#testes-e-qualidade)
- [Documentação](#documentação)
- [Deploy](#deploy)
- [Contribuindo](#contribuindo)
- [Licença](#licença)

---

## 🎯 Visão Geral

Sistema profissional de integração com a API do Portal Único Siscomex, desenvolvido para automatizar a coleta, sincronização e normalização de dados de exportação.

**Problema Resolvido:** Empresas exportadoras precisam acompanhar o status de suas DU-Es em tempo real, cruzar dados com o SAP e manter histórico completo para auditoria e análise.

**Solução:** Sistema automatizado que:
- Consulta chaves de NF-e do SAP via AWS Athena
- Sincroniza DUEs do Siscomex com controle inteligente
- Normaliza e persiste dados em PostgreSQL (37 tabelas)
- Atualiza apenas DUEs que mudaram (otimização por `dataDeRegistro`)
- Respeita rate limits da API (1000 req/hora)
- Notifica via WhatsApp (opcional)

---

## ✨ Características

### Core Features

- ✅ **Sincronização Inteligente**: Cache de vínculos NF→DUE evita consultas duplicadas
- ✅ **Atualização Otimizada**: Compara `dataDeRegistro` antes de atualizar
- ✅ **Rate Limiting Inteligente**: Detecta PUCX-ER1001 e pausa automaticamente (sem retry que aumenta penalidade)
- ✅ **Resiliência**: Cache de token persistente, coordenação entre threads durante bloqueio
- ✅ **Paralelização**: ThreadPoolExecutor para download simultâneo de DUEs
- ✅ **Observabilidade**: Logging profissional com rotação, métricas de tempo

### Integrações

- 🔄 **SAP HANA**: Consulta via AWS Athena (boto3)
- 🌐 **Siscomex API**: REST com autenticação via chave de acesso
- 🗄️ **PostgreSQL**: 37 tabelas normalizadas com relacionamentos
- 💬 **WhatsApp**: Notificações via Evolution API (opcional)
- 📊 **Redis**: Cache distribuído (opcional)

### Qualidade de Código

- ✅ Type hints completos (Python 3.10+)
- ✅ Arquitetura em camadas
- ✅ Tratamento robusto de exceções
- ✅ Testes automatizados (pytest)
- ✅ Validação de configuração no startup
- ✅ Documentação completa

---

## 🏗️ Arquitetura

### Diagrama de Componentes

```
┌─────────────────────────────────────────────────────────────┐
│                      CLI Layer (src/cli/)                    │
│  ┌────────────┐  ┌────────────┐  ┌─────────────────────┐   │
│  │ commands.py│  │api_helpers │  │    display.py       │   │
│  │            │  │            │  │                     │   │
│  └────────────┘  └────────────┘  └─────────────────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────┴────────────────────────────────────┐
│                  Business Logic Layer                        │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ processors/ │  │    sync/     │  │  notifications/  │   │
│  │  due.py     │  │ new_dues.py  │  │   whatsapp.py    │   │
│  │             │  │update_dues.py│  │                  │   │
│  └─────────────┘  └──────────────┘  └──────────────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────┴────────────────────────────────────┐
│                  Integration Layer                           │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ api/athena/ │  │api/siscomex/ │  │   database/      │   │
│  │  client.py  │  │   token.py   │  │   manager.py     │   │
│  │             │  │              │  │   schema.py      │   │
│  └─────────────┘  └──────────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
   ┌─────────┐         ┌──────────┐        ┌──────────┐
   │   SAP   │         │ Siscomex │        │PostgreSQL│
   │  Athena │         │   API    │        │    DB    │
   └─────────┘         └──────────┘        └──────────┘
```

### Fluxo de Dados

```
1. SAP (Athena) → Consulta NF-es → PostgreSQL (nfe_sap)
2. PostgreSQL → Verifica vínculos → Lista NFs sem DUE
3. Siscomex API → Consulta DUE por NF → Processa JSON
4. Normaliza dados → 37 tabelas → PostgreSQL
5. WhatsApp (opcional) → Notifica conclusão
```

---

## 🚀 Instalação

### Pré-requisitos

- **Python 3.10+**
- **PostgreSQL 12+**
- **AWS Credentials** (para Athena/SAP)
- **Siscomex API Keys** (client_id e client_secret)

### Instalação Rápida

```bash
# Clone o repositório
git clone https://github.com/seu-usuario/controle-siscomex.git
cd controle-siscomex

# Instale as dependências
pip install -r requirements.txt

# Configure as variáveis de ambiente
cp config_exemplo.env config.env
nano config.env  # Edite com suas credenciais

# Crie as tabelas no PostgreSQL
python -c "from src.database.manager import db_manager; db_manager.conectar(); db_manager.criar_tabelas(); db_manager.desconectar()"

# Verifique a instalação
python -m src.main --status
```

---

## ⚙️ Configuração

### Arquivo `config.env`

```env
# === Siscomex API ===
SISCOMEX_CLIENT_ID=seu_client_id_aqui
SISCOMEX_CLIENT_SECRET=seu_client_secret_aqui

# Rate Limits (conforme docs.portalunico.siscomex.gov.br)
# O sistema detecta PUCX-ER1001 e pausa automaticamente
SISCOMEX_RATE_LIMIT_HOUR=1000      # Limite oficial por hora
SISCOMEX_RATE_LIMIT_BURST=20       # Burst máximo (token bucket)
SISCOMEX_SAFE_REQUEST_LIMIT=900    # Limite preventivo (pausa antes de atingir 1000)

# Features opcionais
SISCOMEX_FETCH_ATOS_SUSPENSAO=true
SISCOMEX_FETCH_ATOS_ISENCAO=false
SISCOMEX_FETCH_EXIGENCIAS_FISCAIS=true

# === PostgreSQL ===
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=usuario
POSTGRES_PASSWORD=senha
POSTGRES_DB=siscomex_export_db

# === AWS Athena (SAP) ===
AWS_REGION=us-east-1
AWS_ATHENA_WORKGROUP=primary
AWS_ATHENA_OUTPUT_LOCATION=s3://seu-bucket/athena-output/

# === WhatsApp (Opcional) ===
WHATSAPP_ENABLED=false
WHATSAPP_BASE_URL=https://sua-evolution-api.com
WHATSAPP_INSTANCE=sua_instancia
WHATSAPP_APIKEY=sua_api_key
WHATSAPP_REMOTE_JID=5511999999999@s.whatsapp.net
```

### Validação de Configuração

O sistema valida automaticamente todas as variáveis obrigatórias no startup:

```bash
python -m src.main --status
```

Se houver erro, você verá mensagens claras:
```
❌ SISCOMEX_CLIENT_ID: Client ID do Siscomex
❌ POSTGRES_HOST: Host do PostgreSQL
```

---

## ⚡ Rate Limiting (Limites de Acesso)

O sistema implementa rate limiting inteligente baseado na [documentação oficial do Siscomex](https://docs.portalunico.siscomex.gov.br/).

### Limites da API

| Configuração | Valor | Descrição |
|--------------|-------|-----------|
| `SISCOMEX_RATE_LIMIT_HOUR` | 1000 | Requisições permitidas por hora |
| `SISCOMEX_SAFE_REQUEST_LIMIT` | 900 | Limite preventivo (pausa automática) |
| `SISCOMEX_RATE_LIMIT_BURST` | 20 | Burst máximo (token bucket) |

### Comportamento de Bloqueio (PUCX-ER1001)

Quando o limite é atingido, o Siscomex retorna o erro `PUCX-ER1001`. O bloqueio é **progressivo**:

| Violação | Penalidade |
|----------|------------|
| 1ª | Bloqueio até fim da hora atual |
| 2ª | Hora atual + **1 hora adicional** |
| 3ª+ | Hora atual + **2 horas adicionais** |

> ⚠️ **IMPORTANTE**: Continuar fazendo requisições durante o bloqueio **aumenta a penalidade**!

### Como o Sistema Lida com Bloqueios

1. **Limite preventivo**: Pausa automaticamente ao atingir 900 req/h (antes do limite real de 1000)
2. **Detecção de PUCX-ER1001**: Extrai o horário de desbloqueio da mensagem de erro
3. **Pausa coordenada**: Todas as threads aguardam juntas até o desbloqueio
4. **Sem retry automático**: Não tenta novamente durante bloqueio (evita aumentar penalidade)
5. **Retomada automática**: Continua processamento após o horário de desbloqueio

### Logs de Rate Limiting

```
⏸️  Limite preventivo SISCOMEX atingido (900 req/h). Aguardando 45.2 minutos...
⏸️  Bloqueio SISCOMEX detectado (PUCX-ER1001).
📋 Mensagem: Foi atingido o limite de 1000 acessos... liberado após as 15:00:00
⏰ Aguardando até 15:00:00 (32.5 minutos)...
✅ Periodo de bloqueio encerrado. Retomando operacoes.
```

---

## 📖 Uso

### Menu Interativo

```bash
python -m src.main
```

```
============================================================
   GERENCIADOR DE SINCRONIZACAO DUE - SISCOMEX
============================================================

[MENU PRINCIPAL]
----------------------------------------
1. Sincronizar novas DUEs
2. Atualizar DUEs existentes
3. Sincronizacao completa (1 + 2)
4. Gerar scripts de agendamento
5. Status do sistema
0. Sair
----------------------------------------
Escolha uma opcao:
```

### Linha de Comando (CLI)

#### Sincronizar Novas DUEs

```bash
# Sincronização completa (processa todas as NFs, rate limiting automático)
python -m src.main --novas

# Com limite manual de NFs
python -m src.main --novas --limit 200

# Com 10 workers paralelos
python -m src.main --novas --workers-download 10
```

#### Atualizar DUEs Existentes

```bash
# Atualizar DUEs desatualizadas (> 24h)
python -m src.main --atualizar

# Atualizar DUE específica
python -m src.main --atualizar-due 24BR0008165929
```

#### Sincronização Completa

```bash
# Novas + Atualização
python -m src.main --completo
```

#### Drawback (Atos Concessórios)

```bash
# Atualizar drawback de DUEs específicas
python -m src.main --atualizar-drawback 24BR0008165929,25BR0006149047

# Atualizar drawback de todas as DUEs
python -m src.main --atualizar-drawback
```

#### Status do Sistema

```bash
python -m src.main --status
```

```
[STATUS DO SISTEMA]
----------------------------------------
  NFs SAP: 1543 chaves
  Vinculos NF->DUE: 1421 registros
  DUEs baixadas: 1421 total
  Itens de DUE: 8945 registros
  Eventos historico: 15230 registros
  DUEs para atualizar (> 24h): 87
```

### Agendamento (Windows Task Scheduler)

```bash
# Gera scripts .bat para agendamento
python -m src.main --gerar-scripts
```

Scripts gerados:
- `scripts/sync_novas.bat` - A cada hora (8h-18h)
- `scripts/sync_atualizar.bat` - 1x por dia (6h)
- `scripts/sync_completo.bat` - Sob demanda

---

## 📁 Estrutura do Projeto

```
controle-siscomex/
├── src/
│   ├── main.py                 # Entry point (132 linhas)
│   ├── cli/                    # ✨ Camada CLI
│   │   ├── commands.py         # Comandos (sync, atualizar, etc)
│   │   ├── api_helpers.py      # Helpers de API
│   │   └── display.py          # Formatação de output
│   ├── core/                   # Utilitários centrais
│   │   ├── constants.py        # Configurações
│   │   ├── config_validator.py # ✨ Validação de config
│   │   ├── exceptions.py       # Exceções customizadas
│   │   ├── logger.py           # Logging profissional
│   │   ├── metrics.py          # Métricas de tempo
│   │   └── rate_limiter.py     # Token bucket algorithm
│   ├── database/               # Camada de dados
│   │   ├── manager.py          # Connection pool + queries
│   │   ├── schema.py           # 37 tabelas
│   │   └── field_mappings.py   # ✨ Mapeamentos centralizados
│   ├── api/                    # Integrações externas
│   │   ├── athena/
│   │   │   └── client.py       # AWS Athena (SAP)
│   │   └── siscomex/
│   │       ├── token.py        # Autenticação + rate limit
│   │       └── tabx.py         # Processamento TABX
│   ├── processors/             # Lógica de negócio
│   │   └── due.py              # Normalização de DUEs
│   ├── sync/                   # Orquestração
│   │   ├── new_dues.py         # Sincronização de novas
│   │   └── update_dues.py      # Atualização de existentes
│   ├── notifications/          # Notificações
│   │   └── whatsapp.py         # WhatsApp via Evolution API
│   └── cache/                  # Cache (opcional)
│       └── redis_cache.py      # Redis client
├── tests/                      # Testes automatizados
│   ├── test_db_manager.py
│   ├── test_due_processor.py
│   ├── test_sync_*.py
│   └── test_token_manager.py
├── docs/                       # ✨ Documentação organizada
│   ├── deployment/             # Guias de deploy
│   ├── troubleshooting/        # Solução de problemas
│   ├── SCHEMA_POSTGRESQL.md
│   └── DIAGRAMA_RELACIONAMENTOS.md
├── scripts/                    # Scripts gerados
│   ├── sync_novas.bat
│   ├── sync_atualizar.bat
│   └── sync_completo.bat
├── migrations/                 # Migrações de banco
├── .github/                    # CI/CD workflows
├── config.env                  # Configurações (git ignored)
├── config_exemplo.env          # Template de config
├── requirements.txt            # Dependências
├── pyproject.toml             # Config do projeto
└── README.md                   # Este arquivo
```

---

## 🧪 Testes e Qualidade

### Executar Testes

```bash
# Todos os testes
pytest tests/ -v

# Com cobertura
pytest tests/ --cov=src --cov-report=html

# Testes específicos
pytest tests/test_db_manager.py -v
```

### Linting e Type Checking

```bash
# Flake8 (PEP 8)
flake8 src tests

# MyPy (type hints)
mypy src

# Black (formatação)
black --check src tests
```

### Pre-commit Hooks

```bash
# Instalar hooks
pre-commit install

# Executar manualmente
pre-commit run --all-files
```

### Métricas de Qualidade

- ✅ Type hint coverage: **70%+**
- ✅ Test coverage: **60%+**
- ✅ Flake8: **0 errors**
- ✅ MyPy: **0 critical errors**
- ✅ Código duplicado: **0%**

---

## 📚 Documentação

### Documentação Técnica

- **[Schema PostgreSQL](docs/SCHEMA_POSTGRESQL.md)** - 37 tabelas detalhadas
- **[Diagrama de Relacionamentos](docs/DIAGRAMA_RELACIONAMENTOS.md)** - ERD completo
- **[Análise de Extrato DUE](docs/ANALISE_EXTRATO_DUE.md)** - Exportação para PDF
- **[Melhorias Propostas](docs/MELHORIAS_PROPOSTAS.md)** - Roadmap

### Deploy

- **[Deploy Dokploy](docs/deployment/DEPLOY_DOKPLOY.md)** - Docker deployment
- **[Cloudflare Setup](docs/deployment/CLOUDFLARE_SETUP_GUIDE.md)** - CDN + DNS
- **[Tutorial VPS](docs/deployment/TUTORIAL_TESTES_VPS.md)** - Testes em VPS

### Troubleshooting

- **[Patches de Correção](docs/troubleshooting/PATCHES_CORRECAO.md)**
- **[Bugs do Siscomex](docs/troubleshooting/RELATORIO_BUGS_SISCOMEX.md)**
- **[Cloudflare Errors](docs/troubleshooting/CLOUDFLARE_MCP_ERROR_DIAGNOSTIC.md)**

---

## 🐳 Deploy

### Docker

```bash
# Build
docker build -t controle-siscomex:latest .

# Run
docker run -d \
  --name siscomex \
  --env-file config.env \
  -v $(pwd)/logs:/app/logs \
  controle-siscomex:latest
```

### Docker Compose

```bash
docker-compose up -d
```

### Produção (VPS)

Veja: [docs/deployment/TUTORIAL_TESTES_VPS.md](docs/deployment/TUTORIAL_TESTES_VPS.md)

---

## 🤝 Contribuindo

Contribuições são bem-vindas! Por favor:

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

### Padrões de Código

- Siga PEP 8
- Use type hints (Python 3.10+)
- Adicione docstrings
- Escreva testes
- Mantenha cobertura > 60%

---

## 📄 Licença

Este projeto está licenciado sob a Licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

---

## 🙏 Agradecimentos

- [Portal Único Siscomex](https://www.gov.br/siscomex/) - API REST
- [Serpro](https://www.serpro.gov.br/) - Infraestrutura
- [AWS](https://aws.amazon.com/) - Athena integration

---

## 📞 Suporte

- **Issues**: [GitHub Issues](https://github.com/seu-usuario/controle-siscomex/issues)
- **Siscomex**: [Comex Responde](https://www.gov.br/siscomex/pt-br/fale-conosco)
- **Infraestrutura**: [Central Serpro](https://www.serpro.gov.br/menu/suporte)

---

<div align="center">

**[⬆ Voltar ao topo](#sistema-de-controle-de-dues---siscomex)**

Feito com ❤️ para comunidade de Comércio Exterior

</div>
