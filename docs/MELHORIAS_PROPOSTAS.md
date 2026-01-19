# Plano de Melhorias - Controle Siscomex

**Data:** Janeiro 2026
**Versão:** 1.0
**Objetivo:** Otimizar e organizar o projeto para maior qualidade, manutenibilidade e escalabilidade.

---

## Progresso das Melhorias

### 2026-01-19
- Ajustado `DatabaseManager` para usar o pool via context manager em operacoes de banco, devolvendo conexoes quando abertas internamente.
- Adicionado `use_connection()` para permitir operacoes batch com `self.conn` consistente no escopo.
- Integradas metricas (`timed`) e excecoes customizadas nos fluxos de sincronizacao.
- Adicionados testes para `DatabaseManager` e helpers de `sync_novas`/`sync_atualizar`.
- Removidos wrappers Python da raiz e padronizada a execucao via `python -m` com scripts atualizados.
- Implementado rate limiter em token bucket para respeitar limites da API Siscomex com burst configuravel.

### 2026-01-17
- Criado `constants.py` para centralizar valores usados pelo orquestrador (scripts, timeouts, intervalo de status).
- Refatorado `src/main.py` para usar as constantes compartilhadas e evitar duplicacao de valores.
- Adicionadas anotacoes de tipo nas funcoes de `src/main.py` para facilitar manutencao.
- Criados `exceptions.py`, `logger.py` e `metrics.py` para padronizar erros, logs e metricas.
- Substituidos `print()` por logging estruturado nos scripts principais (main, syncs, consulta_sap, due_processor, download_tabelas, db_manager, token_manager).
- Centralizados limites, status e timeouts em `constants.py` e aplicada carga de `config.env` via constante.
- Atualizado `AGENTS.md` com o mapa do repositorio.
- Adicionados testes iniciais com pytest (fixtures e testes de due_processor/token_manager).
- Criados `pyproject.toml`, `.pre-commit-config.yaml` e workflow de CI para testes.
- Aplicadas anotacoes de tipo em `src/processors/due.py`, `src/database/manager.py` e `src/api/siscomex/token.py` para comecar a cobertura de tipagem.
- Reorganizada a base para estrutura em `src/` com subpacotes (core, database, api, processors, sync).
- Criados wrappers na raiz para manter compatibilidade com os scripts atuais.
- Atualizado Dockerfile para copiar `src/` durante build.
- Removidos diret?rios gerados (`__pycache__`, `logs`) do workspace.
- Implementado connection pooling em `src/database/manager.py` com ThreadedConnectionPool.
- Padronizadas docstrings (Google style) em modulos principais de sync, Siscomex e Athena.
- Adicionados modulos opcionais: cliente async (`src/api/siscomex/async_client.py`) e cache Redis (`src/cache/redis_cache.py`).
- Adicionadas dependencias opcionais `aiohttp` e `redis` para async/cache.
- Testes executados com pytest (4 passed).
- Executado flake8 em src/tests (0 erros).
- README.md reorganizado para refletir estrutura em src e uso atual.
- Limpeza de caches gerados (__pycache__, logs, .mypy_cache, .pytest_cache).
- Adicionado wrapper REST basico em `src/api/siscomex/rest_wrapper.py`.

---

## Sumário Executivo

O projeto **Controle Siscomex** é um sistema maduro e funcional para gerenciamento de DUEs (Declaração Única de Exportação) com integração SAP/Athena. Após análise detalhada do código-fonte (6.565 linhas em 10 arquivos Python), identificamos oportunidades de melhoria em 5 áreas principais:

| Área | Prioridade | Impacto | Esforço |
|------|------------|---------|---------|
| Qualidade de Código | Alta | Alto | Médio |
| Logging e Monitoramento | Alta | Alto | Baixo |
| Testes Automatizados | Alta | Alto | Médio |
| Configuração e Constantes | Média | Médio | Baixo |
| Arquitetura e Performance | Média | Alto | Alto |

---

## 1. Qualidade de Código

### 1.1 Type Hints (Tipagem Estática)

**Problema:** O código atual não utiliza type hints, dificultando a manutenção e prevenção de bugs.

**Solução:** Adicionar tipagem estática em todos os módulos.

**Antes:**
```python
def consultar_due_por_nf(chave_nf):
    resultados = []
    # ...
    return resultados
```

**Depois:**
```python
from typing import Optional

def consultar_due_por_nf(chave_nf: str) -> list[dict]:
    """Consulta DUEs vinculadas a uma chave de NF.

    Args:
        chave_nf: Chave de acesso da nota fiscal (44 dígitos)

    Returns:
        Lista de dicionários com dados das DUEs encontradas
    """
    resultados: list[dict] = []
    # ...
    return resultados
```

**Arquivos prioritários:**
1. `src/database/manager.py` - Métodos públicos do DatabaseManager
2. `src/api/siscomex/token.py` - Métodos públicos do SharedTokenManager
3. `src/processors/due.py` - Funções de normalização
4. `src/main.py` - Funções de orquestração

**Benefícios:**
- Detecção de bugs em tempo de desenvolvimento (mypy)
- Autocomplete melhorado na IDE
- Documentação implícita do código

---

### 1.2 Docstrings Padronizadas

**Problema:** Docstrings inconsistentes - algumas funções bem documentadas, outras sem documentação.

**Solução:** Adotar padrão Google Style para todas as funções públicas.

**Template:**
```python
def funcao_exemplo(param1: str, param2: int = 10) -> bool:
    """Descrição breve da função.

    Descrição detalhada se necessário, explicando o comportamento
    e casos especiais.

    Args:
        param1: Descrição do primeiro parâmetro
        param2: Descrição do segundo parâmetro (padrão: 10)

    Returns:
        True se operação bem sucedida, False caso contrário

    Raises:
        ValueError: Se param1 for vazio
        ConnectionError: Se não conseguir conectar ao banco

    Example:
        >>> funcao_exemplo("teste", 5)
        True
    """
```

---

### 1.3 Constantes Centralizadas

**Problema:** Valores "mágicos" espalhados pelo código (limites, timeouts, intervalos).

**Solução:** Criar arquivo `constants.py` centralizando todas as constantes.

**Novo arquivo: `constants.py`**
```python
"""Constantes globais do sistema Controle Siscomex."""

# =============================================================================
# LIMITES DE API SISCOMEX
# =============================================================================
SISCOMEX_RATE_LIMIT_HOUR = 1000  # Requisições por hora
SISCOMEX_TOKEN_VALIDITY_MIN = 60  # Minutos de validade do token
SISCOMEX_TOKEN_SAFETY_MARGIN_MIN = 2  # Margem de segurança para renovação
SISCOMEX_AUTH_INTERVAL_SEC = 60  # Intervalo mínimo entre autenticações

# =============================================================================
# LIMITES DE PROCESSAMENTO
# =============================================================================
MAX_CONSULTAS_NF_POR_EXECUCAO = 400  # NFs por execução de sync_novas
MAX_ATUALIZACOES_POR_EXECUCAO = 500  # DUEs por execução de sync_atualizar
HORAS_PARA_ATUALIZACAO = 24  # Horas para considerar DUE desatualizada

# =============================================================================
# TIMEOUTS E RETRIES
# =============================================================================
DB_CONNECTION_TIMEOUT_SEC = 30
HTTP_REQUEST_TIMEOUT_SEC = 30
HTTP_MAX_RETRIES = 3
HTTP_RETRY_BACKOFF_FACTOR = 0.5

# =============================================================================
# SITUAÇÕES DUE
# =============================================================================
SITUACOES_CANCELADAS = frozenset([
    "CANCELADA",
    "REGISTRO_CANCELADO",
    "REGISTRO_CANCELADO_SISTEMA",
    "REGISTRO_CANCELADO_USUARIO"
])

SITUACOES_PENDENTES = frozenset([
    "EM_CARGA",
    "SOLICITADA",
    "EM_ANALISE",
    "PENDENTE_DESPACHO",
    "PENDENTE_EMBARQUE",
    "PENDENTE_AVERBACAO",
    "AGUARDANDO_RETIFICACAO",
    "RETIFICACAO_SOLICITADA",
    "PENDENTE"
])

SITUACOES_AVERBADAS = frozenset([
    "AVERBADA",
    "DESEMBARACADA"
])

# =============================================================================
# DIAS PARA VERIFICAÇÃO
# =============================================================================
DIAS_VERIFICACAO_AVERBADA = 7  # Dias após averbação para verificar mudanças

# =============================================================================
# CONFIGURAÇÃO AWS ATHENA
# =============================================================================
ATHENA_DEFAULT_REGION = "us-east-1"
ATHENA_QUERY_RESULT_LOCATION = "s3://aws-athena-query-results-default/"
```

---

### 1.4 Tratamento de Erros Melhorado

**Problema:** Exceções genéricas com tratamento inconsistente.

**Solução:** Criar exceções customizadas e tratamento padronizado.

**Novo arquivo: `exceptions.py`**
```python
"""Exceções customizadas do sistema Controle Siscomex."""


class ControleSiscomexError(Exception):
    """Exceção base para todos os erros do sistema."""
    pass


class DatabaseError(ControleSiscomexError):
    """Erro relacionado a operações de banco de dados."""
    pass


class ConnectionError(DatabaseError):
    """Erro de conexão com o banco de dados."""
    pass


class QueryError(DatabaseError):
    """Erro na execução de queries."""
    pass


class SiscomexAPIError(ControleSiscomexError):
    """Erro relacionado à API do Siscomex."""
    pass


class AuthenticationError(SiscomexAPIError):
    """Erro de autenticação na API."""
    pass


class RateLimitError(SiscomexAPIError):
    """Limite de requisições excedido."""

    def __init__(self, message: str, retry_after: int = 3600):
        super().__init__(message)
        self.retry_after = retry_after


class TokenExpiredError(SiscomexAPIError):
    """Token de autenticação expirado."""
    pass


class DUEProcessingError(ControleSiscomexError):
    """Erro no processamento de DUE."""
    pass


class ValidationError(ControleSiscomexError):
    """Erro de validação de dados."""
    pass


class ConfigurationError(ControleSiscomexError):
    """Erro de configuração do sistema."""
    pass
```

---

## 2. Logging e Monitoramento

### 2.1 Sistema de Logging Estruturado

**Problema:** Uso de `print()` para logs, dificultando rastreamento e análise.

**Solução:** Implementar logging estruturado com níveis e rotação de arquivos.

**Novo arquivo: `logger.py`**
```python
"""Configuração centralizada de logging."""

import logging
import logging.handlers
import sys
from pathlib import Path
from datetime import datetime


def setup_logging(
    level: str = "INFO",
    log_dir: str = "logs",
    app_name: str = "controle_siscomex"
) -> logging.Logger:
    """Configura o sistema de logging.

    Args:
        level: Nível de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Diretório para arquivos de log
        app_name: Nome da aplicação para o logger

    Returns:
        Logger configurado
    """
    # Criar diretório de logs se não existir
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Configurar logger
    logger = logging.getLogger(app_name)
    logger.setLevel(getattr(logging, level.upper()))

    # Evitar duplicação de handlers
    if logger.handlers:
        return logger

    # Formato detalhado para arquivo
    file_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Formato simplificado para console
    console_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S"
    )

    # Handler para arquivo com rotação diária
    today = datetime.now().strftime("%Y-%m-%d")
    file_handler = logging.handlers.TimedRotatingFileHandler(
        log_path / f"{app_name}.log",
        when="midnight",
        interval=1,
        backupCount=30,  # Manter 30 dias
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)

    # Handler para console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)

    # Handler separado para erros
    error_handler = logging.handlers.RotatingFileHandler(
        log_path / f"{app_name}_errors.log",
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)

    # Adicionar handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    logger.addHandler(error_handler)

    return logger


# Logger global
logger = setup_logging()
```

**Exemplo de uso nos módulos:**
```python
# Em src/database/manager.py
from logger import logger

class DatabaseManager:
    def conectar(self) -> bool:
        logger.info("Iniciando conexão com PostgreSQL")
        try:
            self.conn = psycopg2.connect(...)
            logger.info("Conexão estabelecida com sucesso")
            return True
        except psycopg2.Error as e:
            logger.error(f"Falha na conexão: {e}", exc_info=True)
            return False
```

---

### 2.2 Métricas de Performance

**Problema:** Sem métricas para monitorar performance e identificar gargalos.

**Solução:** Adicionar decoradores para métricas de tempo de execução.

**Novo arquivo: `metrics.py`**
```python
"""Sistema de métricas e monitoramento."""

import time
import functools
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Any
from collections import defaultdict

from logger import logger


@dataclass
class ExecutionMetric:
    """Métrica de execução de uma função."""
    function_name: str
    execution_time: float
    success: bool
    timestamp: datetime = field(default_factory=datetime.now)
    error_message: str | None = None


class MetricsCollector:
    """Coletor centralizado de métricas."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._metrics: list[ExecutionMetric] = []
            cls._instance._counters: dict[str, int] = defaultdict(int)
        return cls._instance

    def record(self, metric: ExecutionMetric) -> None:
        """Registra uma métrica de execução."""
        self._metrics.append(metric)
        self._counters[f"{metric.function_name}_calls"] += 1
        if not metric.success:
            self._counters[f"{metric.function_name}_errors"] += 1

    def increment(self, counter_name: str, value: int = 1) -> None:
        """Incrementa um contador."""
        self._counters[counter_name] += value

    def get_summary(self) -> dict:
        """Retorna resumo das métricas."""
        if not self._metrics:
            return {"total_calls": 0, "functions": {}}

        summary = {
            "total_calls": len(self._metrics),
            "total_errors": sum(1 for m in self._metrics if not m.success),
            "functions": {}
        }

        # Agrupar por função
        by_function = defaultdict(list)
        for m in self._metrics:
            by_function[m.function_name].append(m)

        for func_name, metrics in by_function.items():
            times = [m.execution_time for m in metrics]
            summary["functions"][func_name] = {
                "calls": len(metrics),
                "errors": sum(1 for m in metrics if not m.success),
                "avg_time_ms": sum(times) / len(times) * 1000,
                "max_time_ms": max(times) * 1000,
                "min_time_ms": min(times) * 1000
            }

        return summary


def timed(func: Callable) -> Callable:
    """Decorador para medir tempo de execução."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        collector = MetricsCollector()
        start = time.perf_counter()
        success = True
        error_msg = None

        try:
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            success = False
            error_msg = str(e)
            raise
        finally:
            elapsed = time.perf_counter() - start
            metric = ExecutionMetric(
                function_name=func.__name__,
                execution_time=elapsed,
                success=success,
                error_message=error_msg
            )
            collector.record(metric)

            if elapsed > 5:  # Log se demorar mais de 5 segundos
                logger.warning(
                    f"{func.__name__} demorou {elapsed:.2f}s para executar"
                )

    return wrapper
```

---

## 3. Testes Automatizados

### 3.1 Estrutura de Testes

**Problema:** Sem testes automatizados, aumentando risco de regressões.

**Solução:** Criar suíte de testes com pytest.

**Estrutura proposta:**
```
tests/
├── __init__.py
├── conftest.py              # Fixtures compartilhadas
├── test_src/database/manager.py       # Testes do DatabaseManager
├── test_src/api/siscomex/token.py    # Testes do TokenManager
├── test_src/processors/due.py    # Testes de normalização
├── test_src/sync/new_dues.py       # Testes de sincronização
├── test_src/sync/update_dues.py   # Testes de atualização
├── test_integration.py      # Testes de integração
└── fixtures/
    ├── due_sample.json      # DUE de exemplo
    ├── nf_sample.json       # NF de exemplo
    └── api_responses/       # Respostas mockadas da API
```

**Arquivo: `tests/conftest.py`**
```python
"""Fixtures compartilhadas para testes."""

import pytest
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

# Caminho para fixtures
FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def mock_db_connection():
    """Mock de conexão com banco de dados."""
    with patch("db_manager.psycopg2.connect") as mock_connect:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        yield mock_conn, mock_cursor


@pytest.fixture
def sample_due_response():
    """Resposta de exemplo da API de DUE."""
    with open(FIXTURES_DIR / "due_sample.json", "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def mock_siscomex_api():
    """Mock da API do Siscomex."""
    with patch("requests.Session") as mock_session:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "test_token"}
        mock_session.return_value.post.return_value = mock_response
        mock_session.return_value.get.return_value = mock_response
        yield mock_session


@pytest.fixture
def sample_nf_keys():
    """Lista de chaves de NF de exemplo."""
    return [
        "12345678901234567890123456789012345678901234",
        "98765432109876543210987654321098765432109876"
    ]


@pytest.fixture(scope="session")
def test_config():
    """Configuração de teste."""
    return {
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5432",
        "POSTGRES_USER": "test",
        "POSTGRES_PASSWORD": "test",
        "POSTGRES_DB": "test_siscomex"
    }
```

**Arquivo: `tests/test_src/processors/due.py`**
```python
"""Testes para o módulo due_processor."""

import pytest
from due_processor import processar_dados_due


class TestProcessarDadosDue:
    """Testes para a função processar_dados_due."""

    def test_due_completa_normalizada(self, sample_due_response):
        """Verifica se DUE completa é normalizada corretamente."""
        resultado = processar_dados_due(
            sample_due_response,
            atos_concessorios=[],
            atos_isencao=[],
            exigencias_fiscais=[]
        )

        assert "principal" in resultado
        assert "itens" in resultado
        assert resultado["principal"]["numero_due"] is not None

    def test_due_sem_itens(self):
        """Verifica tratamento de DUE sem itens."""
        due_vazia = {"numero": "24BR0001", "itens": []}

        resultado = processar_dados_due(
            due_vazia,
            atos_concessorios=[],
            atos_isencao=[],
            exigencias_fiscais=[]
        )

        assert resultado["itens"] == []

    def test_campos_obrigatorios(self, sample_due_response):
        """Verifica se campos obrigatórios estão presentes."""
        resultado = processar_dados_due(
            sample_due_response,
            atos_concessorios=[],
            atos_isencao=[],
            exigencias_fiscais=[]
        )

        campos_obrigatorios = [
            "numero_due",
            "situacao",
            "data_registro"
        ]

        for campo in campos_obrigatorios:
            assert campo in resultado["principal"], f"Campo {campo} ausente"
```

---

### 3.2 Configuração de CI/CD

**Arquivo: `.github/workflows/tests.yml`**
```yaml
name: Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test_siscomex
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-mock

      - name: Run tests
        env:
          POSTGRES_HOST: localhost
          POSTGRES_PORT: 5432
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test_siscomex
        run: |
          pytest tests/ -v --cov=. --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: ./coverage.xml
```

---

## 4. Configuração e Organização

### 4.1 Estrutura de Diretórios Proposta

**Estrutura atual:**
```
controle-siscomex/
├── src/main.py
├── src/database/manager.py
├── src/api/siscomex/token.py
├── src/processors/due.py
├── ... (todos na raiz)
```

**Estrutura proposta:**
```
controle-siscomex/
├── src/
│   ├── __init__.py
│   ├── src/main.py                 # Entry point
│   ├── cli.py                  # Interface de linha de comando
│   │
│   ├── core/                   # Núcleo do sistema
│   │   ├── __init__.py
│   │   ├── constants.py        # Constantes globais
│   │   ├── exceptions.py       # Exceções customizadas
│   │   ├── logger.py           # Configuração de logging
│   │   └── metrics.py          # Sistema de métricas
│   │
│   ├── database/               # Camada de dados
│   │   ├── __init__.py
│   │   ├── manager.py          # DatabaseManager
│   │   ├── schema.py           # Definições de schema
│   │   └── migrations/         # Migrações de banco
│   │
│   ├── api/                    # Integrações externas
│   │   ├── __init__.py
│   │   ├── siscomex/
│   │   │   ├── __init__.py
│   │   │   ├── client.py       # Cliente HTTP
│   │   │   ├── token.py        # TokenManager
│   │   │   └── endpoints.py    # Endpoints da API
│   │   └── athena/
│   │       ├── __init__.py
│   │       └── client.py       # Cliente Athena
│   │
│   ├── processors/             # Processamento de dados
│   │   ├── __init__.py
│   │   ├── due.py              # Processador de DUE
│   │   └── normalization.py    # Normalização de dados
│   │
│   └── sync/                   # Sincronização
│       ├── __init__.py
│       ├── new_dues.py         # sync_novas
│       └── update_dues.py      # sync_atualizar
│
├── tests/                      # Testes automatizados
│   ├── __init__.py
│   ├── conftest.py
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│
├── docs/                       # Documentação
│   ├── SCHEMA_POSTGRESQL.md
│   ├── API_REFERENCE.md
│   └── MELHORIAS_PROPOSTAS.md
│
├── scripts/                    # Scripts auxiliares
│   ├── install.py
│   └── migrate.py
│
├── config/                     # Configurações
│   ├── config_exemplo.env
│   └── logging.yaml
│
├── logs/                       # Logs (gitignore)
│
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── pyproject.toml              # Configuração do projeto
├── README.md
└── .gitignore
```

---

### 4.2 Arquivo pyproject.toml

**Novo arquivo: `pyproject.toml`**
```toml
[project]
name = "controle-siscomex"
version = "2.0.0"
description = "Sistema de gerenciamento de DUEs e integração Siscomex/SAP"
readme = "README.md"
requires-python = ">=3.10"
license = {text = "MIT"}
authors = [
    {name = "Equipe de Desenvolvimento"}
]
keywords = ["siscomex", "due", "exportacao", "sap", "drawback"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]

dependencies = [
    "psycopg2-binary>=2.9.9",
    "requests>=2.31.0",
    "boto3>=1.34.0",
    "pandas>=2.1.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "pytest-mock>=3.12.0",
    "black>=23.0.0",
    "flake8>=6.1.0",
    "mypy>=1.7.0",
    "pre-commit>=3.6.0",
]

[project.scripts]
siscomex = "src.main:main"

[tool.black]
line-length = 100
target-version = ['py310', 'py311']
include = '\.pyi?$'
exclude = '''
/(
    \.git
    | \.venv
    | build
    | dist
)/
'''

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
ignore_missing_imports = true

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
addopts = "-v --tb=short"

[tool.coverage.run]
source = ["src"]
omit = ["tests/*", "**/__init__.py"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "if __name__ == .__main__.:",
]
```

---

### 4.3 Pre-commit Hooks

**Novo arquivo: `.pre-commit-config.yaml`**
```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: check-added-large-files
      - id: check-merge-conflict
      - id: detect-private-key

  - repo: https://github.com/psf/black
    rev: 23.12.1
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/pycqa/flake8
    rev: 7.0.0
    hooks:
      - id: flake8
        args: ['--max-line-length=100', '--ignore=E501,W503']

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [types-requests]
        args: ['--ignore-missing-imports']
```

---

## 5. Arquitetura e Performance

### 5.1 Connection Pooling para PostgreSQL

**Problema:** Cada operação cria nova conexão, ineficiente para alto volume.

**Solução:** Implementar pool de conexões.

**Modificação em `src/database/manager.py`:**
```python
from psycopg2 import pool
from contextlib import contextmanager

class DatabaseManager:
    """Gerenciador de banco de dados com connection pooling."""

    _instance = None
    _pool: pool.ThreadedConnectionPool | None = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize_pool()
        return cls._instance

    def _initialize_pool(self) -> None:
        """Inicializa o pool de conexões."""
        self._pool = pool.ThreadedConnectionPool(
            minconn=2,
            maxconn=10,
            host=os.getenv("POSTGRES_HOST"),
            port=os.getenv("POSTGRES_PORT"),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
            database=os.getenv("POSTGRES_DB"),
            connect_timeout=30
        )
        logger.info("Pool de conexões inicializado (2-10 conexões)")

    @contextmanager
    def get_connection(self):
        """Context manager para obter conexão do pool."""
        conn = None
        try:
            conn = self._pool.getconn()
            yield conn
        finally:
            if conn:
                self._pool.putconn(conn)

    def executar_query(self, query: str, params: tuple = None) -> list:
        """Executa query usando conexão do pool."""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                if cursor.description:
                    return cursor.fetchall()
                conn.commit()
                return []
```

---

### 5.2 Async/Await para I/O Bound

**Problema:** Operações I/O-bound bloqueiam threads desnecessariamente.

**Solução:** Migrar para asyncio para chamadas HTTP.

**Exemplo de refatoração (futuro):**
```python
import asyncio
import aiohttp
from typing import AsyncGenerator

class AsyncSiscomexClient:
    """Cliente assíncrono para API Siscomex."""

    def __init__(self, token_manager: SharedTokenManager):
        self.token_manager = token_manager
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers=self.token_manager.obter_headers()
            )
        return self._session

    async def consultar_due(self, numero_due: str) -> dict:
        """Consulta DUE de forma assíncrona."""
        session = await self._get_session()
        url = f"https://api.siscomex.gov.br/due/{numero_due}"

        async with session.get(url) as response:
            response.raise_for_status()
            return await response.json()

    async def consultar_dues_batch(
        self,
        numeros_due: list[str],
        max_concurrent: int = 5
    ) -> AsyncGenerator[dict, None]:
        """Consulta múltiplas DUEs com concorrência limitada."""
        semaphore = asyncio.Semaphore(max_concurrent)

        async def fetch_with_semaphore(numero: str) -> dict:
            async with semaphore:
                return await self.consultar_due(numero)

        tasks = [fetch_with_semaphore(n) for n in numeros_due]

        for coro in asyncio.as_completed(tasks):
            yield await coro

    async def close(self) -> None:
        """Fecha a sessão HTTP."""
        if self._session:
            await self._session.close()
```

---

### 5.3 Cache com Redis (Opcional)

**Para cenários de alta escala:**

```python
import redis
import json
from typing import Optional

class CacheManager:
    """Gerenciador de cache com Redis."""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self._client = redis.from_url(redis_url)
        self._default_ttl = 3600  # 1 hora

    def get(self, key: str) -> Optional[dict]:
        """Obtém valor do cache."""
        data = self._client.get(key)
        if data:
            return json.loads(data)
        return None

    def set(self, key: str, value: dict, ttl: int = None) -> None:
        """Define valor no cache."""
        self._client.setex(
            key,
            ttl or self._default_ttl,
            json.dumps(value)
        )

    def invalidate(self, pattern: str) -> int:
        """Invalida chaves que correspondem ao padrão."""
        keys = self._client.keys(pattern)
        if keys:
            return self._client.delete(*keys)
        return 0
```

---

## 6. Cronograma de Implementação

### Fase 1: Fundação (Prioridade Alta)
| Item | Descrição | Arquivos Afetados |
|------|-----------|-------------------|
| 1.1 | Criar `constants.py` | Novo arquivo |
| 1.2 | Criar `exceptions.py` | Novo arquivo |
| 1.3 | Criar `logger.py` | Novo arquivo |
| 1.4 | Migrar prints para logging | Todos os .py |

### Fase 2: Qualidade de Código (Prioridade Alta)
| Item | Descrição | Arquivos Afetados |
|------|-----------|-------------------|
| 2.1 | Adicionar type hints | Todos os .py |
| 2.2 | Padronizar docstrings | Funções públicas |
| 2.3 | Configurar mypy e flake8 | pyproject.toml |
| 2.4 | Configurar pre-commit | .pre-commit-config.yaml |

### Fase 3: Testes (Prioridade Alta)
| Item | Descrição | Arquivos Afetados |
|------|-----------|-------------------|
| 3.1 | Criar estrutura de testes | tests/ |
| 3.2 | Testes unitários críticos | test_src/processors/due.py |
| 3.3 | Testes de integração | test_integration.py |
| 3.4 | CI/CD com GitHub Actions | .github/workflows/ |

### Fase 4: Organização (Prioridade Média)
| Item | Descrição | Arquivos Afetados |
|------|-----------|-------------------|
| 4.1 | Reorganizar em src/ | Estrutura de diretórios |
| 4.2 | Criar pyproject.toml | Novo arquivo |
| 4.3 | Atualizar imports | Todos os .py |

### Fase 5: Performance (Prioridade Média)
| Item | Descrição | Arquivos Afetados |
|------|-----------|-------------------|
| 5.1 | Connection pooling | src/database/manager.py |
| 5.2 | Métricas de performance | metrics.py |
| 5.3 | Otimizar queries SQL | src/database/manager.py |

### Fase 6: Avançado (Prioridade Baixa)
| Item | Descrição | Arquivos Afetados |
|------|-----------|-------------------|
| 6.1 | Migração para async | Novos arquivos |
| 6.2 | Cache Redis | Novo módulo |
| 6.3 | API REST wrapper | Novo módulo |

---

## 7. Métricas de Sucesso

### Qualidade de Código
- [ ] 100% de cobertura de type hints em funções públicas
- [ ] 0 erros no mypy --strict
- [ ] 0 warnings no flake8
- [ ] 100% de funções públicas com docstrings

### Testes
- [ ] Cobertura de testes >= 80%
- [ ] Testes executam em < 60 segundos
- [ ] CI/CD verde em todas as branches

### Performance
- [ ] Tempo médio de sync_novas < 10 minutos
- [ ] Conexões de banco reutilizadas (pool)
- [ ] Logs estruturados em produção

### Manutenibilidade
- [ ] Documentação atualizada
- [ ] Código formatado automaticamente (black)
- [ ] Commits validados por pre-commit

---

## 8. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Quebra de compatibilidade com reorganização | Média | Alto | Testes extensivos antes de deploy |
| Aumento de complexidade | Baixa | Médio | Documentar decisões arquiteturais |
| Curva de aprendizado da equipe | Média | Baixo | Treinamento e pair programming |
| Performance degradada durante migração | Baixa | Alto | Feature flags para rollback |

---

## 9. Conclusão

Este plano de melhorias visa transformar o projeto Controle Siscomex de um sistema funcional para um sistema **enterprise-ready** com:

- **Código mais seguro** através de tipagem e validações
- **Maior visibilidade** com logging estruturado e métricas
- **Confiabilidade** através de testes automatizados
- **Manutenibilidade** com organização clara e padrões definidos
- **Escalabilidade** preparada para crescimento futuro

A implementação pode ser feita de forma incremental, começando pelas melhorias de maior impacto e menor risco (Fases 1-3), permitindo entregas contínuas de valor.

---

**Documento preparado por:** Claude AI
**Data:** Janeiro 2026
**Versão:** 1.0
