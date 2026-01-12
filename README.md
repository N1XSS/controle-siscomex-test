# Sistema de Controle de DUEs e Drawback - Siscomex

Sistema completo para consulta, sincronizacao e normalizacao de dados de DU-Es (Declaracao Unica de Exportacao) do Portal Unico de Comercio Exterior (Siscomex), com integracao ao SAP HANA e persistencia em PostgreSQL.

## Indice

- [Funcionalidades Principais](#funcionalidades-principais)
- [Arquitetura do Sistema](#arquitetura-do-sistema)
- [Instalacao e Configuracao](#instalacao-e-configuracao)
- [Uso do Sistema](#uso-do-sistema)
- [Politica de Atualizacao](#politica-de-atualizacao)
- [Estrutura de Dados](#estrutura-de-dados)
- [Deploy em VPS](#deploy-em-vps)

## Funcionalidades Principais

### 1. Consulta SAP (`consulta_sap.py`)
- Consulta 4 databases SAP HANA (AGROPECUARIA, AGROBUSINESS, AGRICOLA, SAMUELMAGGI)
- Extrai chaves de NF de exportacao de algodao em pluma (CFOP 7504)
- Salva diretamente no PostgreSQL (tabela `nfe_sap`)

### 2. Sincronizacao de Novas DUEs (`sync_novas.py`)
- Identifica NFs do SAP sem DUE vinculada
- **Cache inteligente**: Nao reconsulta NFs ja vinculadas
- Agrupa requisicoes por DUE (otimizacao)
- Consulta dados completos incluindo drawback

### 3. Atualizacao de DUEs (`sync_atualizar.py`)
- **Verificacao inteligente**: Compara `dataDeRegistro` para detectar mudancas
- Ignora DUEs CANCELADAS (nunca atualiza)
- DUEs pendentes: atualiza sempre
- DUEs averbadas antigas: verifica se mudou antes de atualizar
- Economia de requisicoes em DUEs sem alteracao

### 4. Gerenciador Principal (`main.py`)
- Menu interativo para execucao manual
- Argumentos de linha de comando para automacao
- **Atualizar DUE especifica**: `--atualizar-due NUMERO`
- **Atualizar drawback**: `--atualizar-drawback DUES` ou `--atualizar-drawback` (todas)
- Exibicao de status do sistema

### 5. Processamento de DUEs (`due_processor.py`)
- Normalizacao em 24 tabelas relacionais
- Consulta de atos concessorios de drawback (suspensao e isencao)
- Exigencias fiscais estruturadas

## Arquitetura do Sistema

```
controle-due-drawback/
├── config.env                    # Credenciais (NAO versionar!)
├── config_exemplo.env            # Template de configuracao
├── requirements.txt              # Dependencias Python
├── README.md                     # Documentacao principal
├── LICENSE                       # Licenca
├── .gitignore                    # Arquivos ignorados pelo Git
│
├── main.py                       # PONTO DE ENTRADA - Menu e CLI
├── consulta_sap.py               # Consulta SAP HANA -> nfe_sap
├── due_processor.py              # Processamento e normalizacao DUE
├── sync_novas.py                 # Sincronizar novas DUEs
├── sync_atualizar.py             # Atualizar DUEs existentes
│
├── token_manager.py              # Autenticacao Siscomex (singleton)
├── db_manager.py                 # Operacoes PostgreSQL + constantes
├── db_schema.py                  # DDL das 37 tabelas
│
├── download_tabelas.py           # Download tabelas TABX (ocasional)
├── instalar.py                   # Script de instalacao
│
├── scripts/                      # Scripts de agendamento
│   ├── sync_diario.sh            # Cron Linux
│   └── sync_diario.bat           # Agendador Windows
│
└── docs/                         # Documentacao adicional
    ├── SCHEMA_POSTGRESQL.md      # Documentacao detalhada do banco
    ├── schema.md                 # Schema original (CSV)
    ├── ANALISE_EXTRATO_DUE.md    # Analise PDF vs banco + queries
    └── DIAGRAMA_RELACIONAMENTOS.md # Diagrama de relacionamentos
```

### Fluxo de Dados

```
┌─────────────┐     ┌──────────────┐     ┌──────────────────┐
│  SAP HANA   │────>│ consulta_sap │────>│   PostgreSQL     │
│   (NFs)     │     │     .py      │     │   (nfe_sap)      │
└─────────────┘     └──────────────┘     └──────────────────┘
                                                  │
                    ┌──────────────┐               │
                    │  sync_novas  │<──────────────┘
                    │     .py      │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐     ┌──────────────────┐
                    │   Siscomex   │────>│   PostgreSQL     │
                    │     API      │     │  (37 tabelas)    │
                    └──────────────┘     └──────────────────┘
```

## Instalacao e Configuracao

### 1. Pre-requisitos

```bash
pip install -r requirements.txt
```

### 2. Configuracao das Credenciais

Crie o arquivo `config.env` (copie de `config_exemplo.env`):

```env
# Credenciais Siscomex
SISCOMEX_CLIENT_ID=seu_client_id_aqui
SISCOMEX_CLIENT_SECRET=seu_client_secret_aqui

# PostgreSQL
POSTGRES_HOST=31.97.22.234
POSTGRES_PORT=5440
POSTGRES_USER=gestor_siscomex
POSTGRES_PASSWORD=sua_senha_aqui
POSTGRES_DB=siscomex_export_db
```

### 3. Criar Tabelas no Banco

```bash
python -c "from db_manager import db_manager; db_manager.conectar(); db_manager.criar_tabelas(); db_manager.desconectar()"
```

## Uso do Sistema

### Menu Interativo (Recomendado)

```bash
python main.py
```

### Linha de Comando

```bash
# Sincronizar novas DUEs (SAP + Siscomex)
python main.py --novas

# Atualizar DUEs existentes (inteligente)
python main.py --atualizar

# Sincronizacao completa
python main.py --completo

# Atualizar uma DUE especifica (todos os dados)
python main.py --atualizar-due 24BR0008165929

# Atualizar drawback de DUEs especificas
python main.py --atualizar-drawback 24BR0008165929,25BR0006149047

# Atualizar drawback de TODAS as DUEs com atos
python main.py --atualizar-drawback

# Ver status do sistema
python main.py --status
```

### Requisicoes por Operacao

| Operacao | Requisicoes/DUE | Total para 1000 DUEs |
|----------|-----------------|----------------------|
| Descobrir DUE por NF | 1 | 1000 (se todas novas) |
| Dados completos | 4 | 4000 |
| Apenas drawback | 1 | 1000 |
| Verificar se mudou | 1 | 1000 |

**Otimizacao**: Cache de vinculos evita reconsultar NFs ja conhecidas.

## Politica de Atualizacao Inteligente

### Gestao Inteligente de DUEs

O sistema implementa uma **gestao inteligente** que otimiza requisicoes baseada no estado da DUE:

#### Categorias de DUEs

| Situacao | Acao | Frequencia | Requisicoes |
|----------|------|------------|-------------|
| CANCELADA | Ignorar sempre | Nunca | 0 |
| EM_CARGA, DESEMBARACADA | Atualizar completo | Diaria | 4 req/DUE |
| AVERBADA (< 7 dias) | Atualizar completo | Diaria | 4 req/DUE |
| AVERBADA (> 7 dias) | Verificar dataDeRegistro | Diaria | 1 req (se mudou: +3) |

#### Verificacao Inteligente por `dataDeRegistro`

O campo `dataDeRegistro` da API **muda sempre que ha retificacao**. O sistema:

1. **Consulta leve**: Compara `dataDeRegistro` da API com banco (1 requisicao)
2. **Se mudou**: Baixa dados completos (4 requisicoes)
3. **Se nao mudou**: Ignora atualizacao (economia de 3 requisicoes)

**Resultado**: 75% de economia em DUEs averbadas sem alteracoes.

#### Cache de Vinculos NF-DUE

- **Cache persistente**: Vinculos NF->DUE armazenados no PostgreSQL
- **Nao reconsulta**: NFs ja vinculadas nao sao consultadas novamente
- **Economia**: 100% de requisicoes economizadas em NFs conhecidas

### Fluxo Diario Recomendado

```
SYNC DIARIO (06:00) - 1x ao dia
       │
       ├── 1. Novas NFs do SAP
       │   └── sync_novas.py
       │       ├── Carrega NFs do SAP
       │       ├── Filtra NFs sem vinculo (cache)
       │       ├── Consulta API apenas para NFs novas
       │       └── Agrupa por DUE (evita duplicatas)
       │
       └── 2. Atualizar DUEs Existentes
           └── sync_atualizar.py
               ├── Pendentes: atualiza direto (4 req/DUE)
               ├── Averbadas recentes: atualiza direto (4 req/DUE)
               └── Averbadas antigas: verifica dataDeRegistro
                   ├── Se mudou: atualiza completo (4 req/DUE)
                   └── Se nao mudou: ignora (1 req/DUE)
```

### Economia de Requisicoes

| Cenario | Antes | Depois | Economia |
|--------|-------|--------|----------|
| DUE averbada sem mudanca | 4 req | 1 req | 75% |
| NF ja vinculada | 1 req | 0 req | 100% |
| 1000 DUEs averbadas (5% mudam) | 4000 req | 1400 req | 65% |

### Constantes de Situacoes

O sistema define constantes em `db_manager.py`:

- `SITUACOES_CANCELADAS`: DUEs que nunca mudam (ignorar sempre)
- `SITUACOES_AVERBADAS`: DUEs que podem ter retificacoes (verificar)
- `SITUACOES_PENDENTES`: DUEs em andamento (atualizar sempre)

## Estrutura de Dados

### 37 Tabelas PostgreSQL

**Tabelas de DUE (23):**
- `due_principal` - Dados principais da DUE
- `nf_due_vinculo` - Vinculo NF->DUE
- `due_itens` - Itens da DUE
- `due_eventos_historico` - Historico de eventos
- `due_solicitacoes` - Retificacoes, cancelamentos
- `due_atos_concessorios_suspensao` - Drawback suspensao
- `due_atos_concessorios_isencao` - Drawback isencao
- `due_exigencias_fiscais` - Exigencias fiscais
- E mais 15 tabelas de detalhes...

**Tabelas de Suporte (14):**
- `nfe_sap` - NFs importadas do SAP
- `suporte_pais`, `suporte_moeda`, `suporte_porto`, etc.

Ver `docs/SCHEMA_POSTGRESQL.md` para documentacao completa.

### Gerar Extrato PDF

Para gerar um extrato similar ao PDF do Siscomex, consulte:
- `docs/ANALISE_EXTRATO_DUE.md` - Queries SQL para extrair todos os dados
- `docs/DIAGRAMA_RELACIONAMENTOS.md` - Relacionamentos entre tabelas
- `docs/TESTES_API_ENDPOINTS.md` - Testes de endpoints e descobertas

**Cobertura**: 97% dos campos do PDF estao capturados. 

**Campos faltantes** (testados multiplos endpoints):
- Coordenadas geograficas (nao disponivel na API - testado endpoints de recintos)
- Nome completo da equipe de analise fiscal (apenas codigo - testado endpoints de unidades)

**Campos resolvidos**:
- ✅ Tipo documento fiscal: Campo `tipo` capturado (ex: NOTA_FISCAL_ELETRONICA)

### Campos Importantes

| Campo | Tabela | Descricao |
|-------|--------|-----------|
| `data_de_registro` | due_principal | Muda quando ha retificacao |
| `data_ultima_atualizacao` | due_principal | Quando consultamos a API |
| `situacao` | due_principal | Status atual da DUE |

## Deploy em VPS

> **📚 Documentação Completa de Deploy:**
> - **[DEPLOY_DOKPLOY.md](DEPLOY_DOKPLOY.md)** - Guia completo de deploy no Dokploy (Docker)
> - **[TUTORIAL_TESTES_VPS.md](TUTORIAL_TESTES_VPS.md)** - Tutorial passo a passo para testar e verificar o sistema na VPS (para leigos)

### Deploy Manual (Sem Docker)

### 1. Clonar Repositorio

```bash
git clone https://github.com/seu-usuario/controle-due-drawback.git
cd controle-due-drawback
```

### 2. Configurar Ambiente

```bash
python -m venv venv
source venv/bin/activate  # Linux
pip install -r requirements.txt
```

### 3. Configurar Credenciais

```bash
cp config_exemplo.env config.env
nano config.env  # Editar com credenciais reais
```

### 4. Agendar Execucao (Cron)

```bash
# Editar crontab
crontab -e

# Adicionar linha:
0 6 * * * /caminho/controle-due-drawback/scripts/sync_diario.sh >> /var/log/due-sync.log 2>&1
```

### 5. Verificar Execucao

```bash
python main.py --status
```

### Deploy com Dokploy (Docker - Recomendado)

Para deploy usando Docker no Dokploy, consulte:
- **[DEPLOY_DOKPLOY.md](DEPLOY_DOKPLOY.md)** - Instruções completas de deploy
- **[TUTORIAL_TESTES_VPS.md](TUTORIAL_TESTES_VPS.md)** - Como testar e verificar após o deploy

## Troubleshooting

### Problemas Comuns

**1. "Credenciais nao configuradas"**
```bash
cat config.env  # Verificar arquivo
```

**2. "Rate limit atingido"**
```bash
# Aguardar 1 hora
python main.py --status
```

**3. "Conexao PostgreSQL falhou"**
```bash
python -c "from db_manager import db_manager; print(db_manager.conectar())"
```

**4. DUE nao atualiza**
```bash
# Forcar atualizacao
python main.py --atualizar-due NUMERO_DUE
```

## Licenca

Uso interno - sujeito as politicas de uso da API do Siscomex.
