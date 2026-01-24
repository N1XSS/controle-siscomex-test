# 🐛 RELATÓRIO DE BUGS E CORREÇÕES - SISTEMA SISCOMEX

**Data:** 20/01/2026  
**Container:** testes-controle-siscomex-teste-tu8gsi  
**Banco:** siscomex_export_db_test

---

## 📋 SUMÁRIO EXECUTIVO

### Status Atual do Banco de Dados
- ✅ **26.809 registros** salvos com sucesso
- ✅ **285 DUEs** completas processadas
- ✅ **339 vínculos** NF-DUE criados
- ⚠️ **3 bugs críticos** encontrados e documentados
- ⚠️ **Múltiplos campos vazios** por problemas de mapeamento

### Bugs Identificados
1. **Bug #1**: Conexão do banco fecha durante processamento longo (CRÍTICO)
2. **Bug #2**: Import com escopo incorreto impede download de DUEs (CRÍTICO)
3. **Bug #3**: Mapeamento incorreto de campos da API (ALTO)

---

## 🔴 BUG #1: CONEXÃO DO BANCO FECHA PREMATURAMENTE

### Descrição
Durante processamentos longos (>1 hora), a conexão com PostgreSQL fecha antes de salvar os dados no banco, causando fallback para CSV.

### Impacto
- **Severidade:** CRÍTICO
- **Dados afetados:** Vínculos NF-DUE salvos apenas em CSV
- **Frequência:** Toda sincronização que demore > 1 hora

### Evidência
```log
2026-01-20 07:03:53 | WARNING | [AVISO] Erro ao salvar vinculos: connection already closed
2026-01-20 07:03:53 | INFO    | [OK] 339 vinculos salvos em CSV
```

### Causa Raiz
**Arquivo:** `/app/src/sync/new_dues.py`  
**Função:** `salvar_novos_vinculos()`

```python
# PROBLEMA: Verifica se conexão existe, mas não reconecta se fechou
if db_manager.conn:
    try:
        count = db_manager.inserir_vinculos_batch(registros)
        if count > 0:
            logger.info(f"[OK] {count} novos vinculos salvos")
            return
    except Exception as e:
        logger.warning(f"[AVISO] Erro ao salvar vinculos: {e}")

# Fallback para CSV (não deveria ser necessário!)
```

### Correção Sugerida

```python
def salvar_novos_vinculos(novos_vinculos: dict[str, str]) -> None:
    """Salva novos vinculos NF->DUE no PostgreSQL."""
    if not novos_vinculos:
        return
    
    agora = datetime.utcnow().isoformat()
    registros = [
        {
            'chave_nf': chave_nf,
            'numero_due': numero_due,
            'data_vinculo': agora,
            'origem': 'SISCOMEX'
        }
        for chave_nf, numero_due in novos_vinculos.items()
    ]
    
    # CORREÇÃO: Garantir conexão ativa antes de salvar
    max_tentativas = 3
    for tentativa in range(max_tentativas):
        try:
            # Verificar e reconectar se necessário
            if not db_manager.conn or db_manager.conn.closed:
                logger.info(f"Reconectando ao banco (tentativa {tentativa + 1}/{max_tentativas})...")
                db_manager.conectar()
            
            count = db_manager.inserir_vinculos_batch(registros)
            if count > 0:
                logger.info(f"[OK] {count} novos vinculos salvos no PostgreSQL")
                return
        except Exception as e:
            logger.warning(f"[AVISO] Erro ao salvar vinculos (tentativa {tentativa + 1}): {e}")
            if tentativa < max_tentativas - 1:
                time.sleep(2)  # Aguardar antes de tentar novamente
            continue
    
    # Fallback para CSV apenas se todas as tentativas falharem
    logger.error("[ERRO] Todas as tentativas de salvar no PostgreSQL falharam, usando CSV")
    try:
        df = pd.DataFrame(registros)
        df.to_csv(CAMINHO_VINCULO, sep=';', index=False, encoding='utf-8-sig')
        logger.info(f"[OK] {len(registros)} vinculos salvos em CSV (fallback)")
    except Exception as e:
        logger.error(f"[ERRO CRÍTICO] Falha ao salvar em CSV: {e}")
```

**Alternativa:** Usar pool de conexões corretamente com `get_connection()` context manager em vez de `db_manager.conn` direto.

---

## 🔴 BUG #2: IMPORT COM ESCOPO INCORRETO

### Descrição
A função `consultar_due_completa` é importada DENTRO da função `processar_novas_nfs()`, mas é chamada pela função `baixar_due_completa()` que está FORA do escopo, causando `NameError`.

### Impacto
- **Severidade:** CRÍTICO
- **Dados afetados:** TODAS as 285 DUEs falharam ao baixar
- **Taxa de erro:** 100% (0 DUEs baixadas com sucesso)

### Evidência
```log
2026-01-20 07:03:53 | WARNING | Erro ao baixar DUE: name 'consultar_due_completa' is not defined
2026-01-20 07:03:53 | INFO    | [OK] 0 DUEs baixadas com sucesso
2026-01-20 07:03:53 | WARNING | [AVISO] 285 DUEs com erro
```

### Causa Raiz
**Arquivo:** `/app/src/sync/new_dues.py`

```python
def baixar_due_completa(numero_due: str) -> dict[str, Any] | None:
    """Baixa uma DUE completa (função no escopo global)."""
    try:
        # PROBLEMA: consultar_due_completa não está no escopo!
        dados_due = consultar_due_completa(numero_due)
        # ...

@timed
def processar_novas_nfs() -> None:
    """Processa NFs do SAP."""
    try:
        # ...
        
        # PROBLEMA: Import está DENTRO da função
        try:
            from src.processors.due import consultar_due_por_nf, processar_dados_due, salvar_resultados_normalizados, consultar_due_completa
        except ImportError as e:
            raise DUEProcessingError(f"Nao foi possivel importar due_processor: {e}") from e
        
        # A função baixar_due_completa() NÃO tem acesso a esse import!
```

### Correção Sugerida

**Mover o import para o topo do arquivo:**

```python
# NO INÍCIO DO ARQUIVO /app/src/sync/new_dues.py

import argparse
import os
import time
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any

import pandas as pd
from dotenv import load_dotenv

from src.core.constants import (
    # ... constantes
)
from src.database.manager import db_manager
from src.core.logger import logger
from src.core.metrics import timed
from src.core.exceptions import (
    # ... exceções
)
from src.api.siscomex.token import token_manager

# CORREÇÃO: Mover imports para o escopo global
from src.processors.due import (
    consultar_due_por_nf,
    consultar_due_completa,
    processar_dados_due,
    salvar_resultados_normalizados,
)

# Resto do código...
```

**Remover o bloco de import dentro da função `processar_novas_nfs()`**

---

## 🟠 BUG #3: MAPEAMENTO INCORRETO DE CAMPOS DA API

### Descrição
O código tenta extrair campos que NÃO existem na resposta da API Siscomex, resultando em colunas vazias no banco de dados.

### Impacto
- **Severidade:** ALTO
- **Dados afetados:** Múltiplas tabelas com colunas vazias

### Campos Afetados

#### 3.1. Tabela `due_itens` - Campo `exportador_nome`
**Status:** 100% vazio (1.270 registros)

**Código Atual:**
```python
'exportador_nome': item.get('exportador', {}).get('nome', ''),
```

**Estrutura Real da API:**
```json
{
  "exportador": {
    "numeroDoDocumento": "01982131000346",
    "tipoDoDocumento": "CNPJ",
    "estrangeiro": false,
    "nacionalidade": {
      "codigo": 105,
      "nome": "BRASIL",
      "nomeResumido": "BRA"
    }
  }
}
```

**Problema:** Campo `nome` NÃO existe em `exportador`!

**Correção Sugerida:**
```python
# Opção 1: Remover o campo (se não for essencial)
# 'exportador_nome': '',  # Campo não disponível na API

# Opção 2: Usar o número do documento como identificador
'exportador_identificacao': item.get('exportador', {}).get('numeroDoDocumento', ''),
'exportador_tipo_documento': item.get('exportador', {}).get('tipoDoDocumento', ''),

# Opção 3: Buscar nome em outra fonte (se disponível)
# Consultar API de CNPJ ou manter tabela auxiliar
```

#### 3.2. Tabela `due_eventos_historico` - Múltiplos Campos

**Campos Vazios:**
- `detalhes`: 100% vazio (13.383 registros)
- `motivo`: 100% vazio (13.383 registros)
- `tipo_evento`: 100% vazio (13.383 registros)
- `data`: 100% vazio (13.383 registros)
- `informacoes_adicionais`: 88.3% vazio (11.821/13.383)

**Código Atual:**
```python
evento_row = {
    'numero_due': numero_due,
    'dataEHoraDoEvento': evento.get('dataEHoraDoEvento', ''),
    'evento': evento.get('evento', ''),
    'responsavel': evento.get('responsavel', ''),
    'informacoesAdicionais': evento.get('informacoesAdicionais', ''),
    'detalhes': evento.get('detalhes', ''),          # ❌ NÃO EXISTE
    'motivo': evento.get('motivo', '')               # ❌ NÃO EXISTE
}
```

**Estrutura Real da API:**
```json
{
  "dataEHoraDoEvento": "2020-02-18T19:45:18.018-0300",
  "evento": "Registro",
  "responsavel": "***468438**"
}
```

**Problema:** API retorna apenas 3 campos, código espera 5+

**Correção Sugerida:**

1. **No código Python (`/app/src/processors/due.py`):**
```python
evento_row = {
    'numero_due': numero_due,
    'dataEHoraDoEvento': evento.get('dataEHoraDoEvento', ''),
    'evento': evento.get('evento', ''),
    'responsavel': evento.get('responsavel', ''),
    'informacoesAdicionais': evento.get('informacoesAdicionais', ''),
    # REMOVER campos que não existem na API:
    # 'detalhes': '',
    # 'motivo': ''
}
```

2. **No banco de dados (opcional):**
```sql
-- Se os campos não são usados, remover da tabela
ALTER TABLE due_eventos_historico 
DROP COLUMN IF EXISTS detalhes,
DROP COLUMN IF EXISTS motivo,
DROP COLUMN IF EXISTS tipo_evento,
DROP COLUMN IF EXISTS data;

-- Ou marcar como deprecated
COMMENT ON COLUMN due_eventos_historico.detalhes IS 'DEPRECATED - Campo não disponível na API Siscomex';
```

---

## 📊 ANÁLISE DE INTEGRIDADE DE DADOS

### Tabelas Com Dados (13 tabelas)
| Tabela | Registros | Status |
|--------|-----------|--------|
| due_eventos_historico | 13.383 | ⚠️ Colunas vazias |
| due_item_notas_remessa | 2.694 | ✅ OK |
| due_item_enquadramentos | 2.530 | ✅ OK |
| due_item_tratamentos_administrativos | 1.473 | ✅ OK |
| nfe_sap | 1.422 | ✅ OK |
| due_item_nota_fiscal_exportacao | 1.270 | ✅ OK |
| due_itens | 1.270 | ⚠️ exportador_nome vazio |
| nf_due_vinculo | 339 | ✅ OK |
| due_situacoes_carga | 326 | ✅ OK |
| due_principal | 285 | ✅ OK |
| due_solicitacoes | 547 | ✅ OK |

### Tabelas Vazias (25 tabelas)

#### Críticas (provavelmente deveriam ter dados)
- ❌ `due_atos_concessorios_suspensao` (0 registros)
- ❌ `due_atos_concessorios_isencao` (0 registros)
- ❌ `due_exigencias_fiscais` (0 registros)
- ❌ `due_declaracao_tributaria_compensacoes` (0 registros)
- ❌ `due_declaracao_tributaria_recolhimentos` (0 registros)

#### Tabelas de Item (dependem dos dados da DUE)
- ⚠️ `due_item_atributos` (0 registros)
- ⚠️ `due_item_notas_complementares` (0 registros)
- ⚠️ `due_item_documentos_importacao` (0 registros)
- ⚠️ `due_item_documentos_transformacao` (0 registros)
- ⚠️ `due_item_calculo_tributario_tratamentos` (0 registros)
- ⚠️ `due_item_calculo_tributario_quadros` (0 registros)

#### Tabelas de Suporte/Lookup (OK estarem vazias inicialmente)
- ℹ️ `suporte_*` (16 tabelas) - Precisam ser populadas manualmente ou via seeds

### Validação de Relacionamentos
✅ **Todos os relacionamentos OK:**
- Vínculos NF-DUE: 100% têm DUE correspondente
- DUEs: 100% têm itens
- DUEs: 100% têm eventos
- Itens: 100% têm enquadramento

### Estatísticas
- 📊 Média de **4.46 itens** por DUE
- 📊 Média de **46.96 eventos** por DUE
- 📅 Período: **2020-03-03** a **2026-01-20**

### Distribuição por Situação
| Situação | Quantidade | % |
|----------|------------|---|
| AVERBADA_SEM_DIVERGENCIA | 276 | 96.8% |
| DESEMBARACADA | 5 | 1.8% |
| CANCELADA_POR_EXPIRACAO_DE_PRAZO | 4 | 1.4% |

---

## 🔧 PLANO DE CORREÇÃO RECOMENDADO

### Prioridade CRÍTICA (Imediato)
1. ✅ **CONCLUÍDO**: Importar vínculos do CSV para o banco *(já executado)*
2. ✅ **CONCLUÍDO**: Baixar DUEs manualmente *(já executado)*
3. 🔴 **PENDENTE**: Corrigir Bug #2 (import com escopo incorreto)
4. 🔴 **PENDENTE**: Corrigir Bug #1 (conexão do banco)

### Prioridade ALTA (Esta Semana)
5. 🟠 **PENDENTE**: Corrigir mapeamento de campos da API (Bug #3)
6. 🟠 **PENDENTE**: Revisar schema do banco para remover colunas desnecessárias
7. 🟠 **PENDENTE**: Testar sincronização completa após correções

### Prioridade MÉDIA (Próximas 2 Semanas)
8. 🟡 **PENDENTE**: Investigar por que tabelas críticas estão vazias
9. 🟡 **PENDENTE**: Implementar validação de dados após sincronização
10. 🟡 **PENDENTE**: Adicionar logs mais detalhados para debugging

### Prioridade BAIXA (Backlog)
11. 🔵 **PENDENTE**: Popular tabelas de suporte (`suporte_*`)
12. 🔵 **PENDENTE**: Criar dashboard de monitoramento
13. 🔵 **PENDENTE**: Documentar estrutura completa da API

---

## 📝 ARQUIVOS QUE PRECISAM SER ALTERADOS

### 1. `/app/src/sync/new_dues.py`
**Linhas a modificar:**
- Mover imports para o topo do arquivo (linha ~25)
- Corrigir função `salvar_novos_vinculos()` (linha ~160)

### 2. `/app/src/processors/due.py`
**Linhas a modificar:**
- Remover/comentar campos inexistentes em `evento_row` (linha ~XXX)
- Corrigir extração de `exportador_nome` em `item_row` (linha ~XXX)
- Adicionar validação de campos antes de inserir

### 3. Schema do banco (opcional)
**Migrations a criar:**
- Remover colunas vazias de `due_eventos_historico`
- Adicionar comentários em colunas deprecated
- Criar índices para melhorar performance de queries

---

## ⚠️ IMPACTO DA SINCRONIZAÇÃO DE HOJE (20/01/2026)

### O que aconteceu:
1. ❌ Sincronização às 06:00 **FALHOU PARCIALMENTE**
2. ⚠️ Vínculos salvos apenas em CSV (Bug #1)
3. ❌ 0 DUEs baixadas com sucesso (Bug #2)
4. ✅ Correção manual executada com sucesso

### Estado Final (após correção manual):
- ✅ **26.809 registros** no banco
- ✅ **285 DUEs** completas
- ✅ **339 vínculos** NF-DUE
- ✅ **Integridade 100%** validada

### Próxima Sincronização:
**⚠️ ATENÇÃO**: Os bugs ainda existem no código! A próxima execução agendada (amanhã às 06:00) falhará da mesma forma se não forem corrigidos.

---

## 🎯 RECOMENDAÇÕES FINAIS

### Urgente
1. **Aplicar correções dos Bugs #1 e #2 HOJE**
2. **Testar sincronização manualmente** antes da próxima execução agendada
3. **Adicionar alertas** para monitorar falhas de sincronização

### Importante
4. Revisar TODA a lógica de reconexão do banco
5. Implementar retry logic com backoff exponencial
6. Adicionar health checks no container

### Melhorias Futuras
7. Migrar para async/await para melhor performance
8. Implementar circuit breaker para API do Siscomex
9. Adicionar métricas e observabilidade (Prometheus/Grafana)
10. Criar testes automatizados de integração

---

## 📞 PRÓXIMOS PASSOS

1. **Revisar este relatório** com a equipe
2. **Priorizar correções** conforme criticidade
3. **Implementar fixes** nos arquivos indicados
4. **Testar em ambiente de teste** antes de deploy
5. **Monitorar próxima sincronização** após deploy

---

**Relatório gerado por:** Sistema de Análise Automatizada  
**Análise baseada em:** Logs, banco de dados e código-fonte  
**Última atualização:** 20/01/2026 10:50 BRT
