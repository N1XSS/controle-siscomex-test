# RELATÓRIO TÉCNICO: Problemas de Rate Limiting e Perda de Dados no Sistema Siscomex

**Data:** 25/01/2026  
**Sistema:** Controle Siscomex - Sincronização de DUEs  
**Ambiente:** Teste (testes-controle-siscomex-teste)

---

## 1. RESUMO EXECUTIVO

Durante a execução da sincronização de DUEs, o sistema processou 425 de 500 DUEs antes de atingir o limite de rate limiting da API do Siscomex. Os dados foram coletados com sucesso, mas **não foram salvos no banco de dados** porque o processo foi interrompido antes de concluir todas as 500 DUEs. Além disso, foi identificado um **problema crítico de race condition** no sistema de rate limiting que permite múltiplas threads ultrapassarem o limite simultaneamente.

**Impacto:**
- 425 DUEs processadas e perdidas (dados em memória não persistidos)
- Taxa de requisições muito acima do limite (25.500 req/h vs 900 req/h configurado)
- Perda de tempo e recursos da API

---

## 2. CRONOLOGIA DOS EVENTOS

### 2.1. Execução da Sincronização (14:48:36)

**Etapa 1: Novas DUEs**
- 1422 NFs carregadas do SAP
- 1406 vínculos existentes no banco
- 16 NFs sem vínculo identificadas
- 16 NFs consultadas na API do Siscomex
- **Resultado:** 0 novas DUEs encontradas (essas NFs não têm DUE no Siscomex)
- **Erro:** `UnboundLocalError: 'dues_erro'` (variável não inicializada) - **CORRIGIDO**

**Etapa 2: Atualização de DUEs Existentes (14:49:22)**
- 975 DUEs órfãs encontradas (vínculo sem dados)
- Limitado a 500 DUEs por execução
- Processamento iniciado com 20 workers paralelos
- Cada DUE faz 1 requisição (apenas atos suspensão habilitado)

### 2.2. Processamento e Limite (14:49:23 - 14:49:38)

- **14:49:23:** Início do processamento paralelo
- **14:49:24:** 25/500 DUEs processadas
- **14:49:25:** 50/500 DUEs processadas
- **14:49:38:** 425/500 DUEs processadas
- **14:49:38:** **Limite de rate limiting atingido (900 req/h)**
- **14:49:38:** Múltiplas threads aguardando 10.4 minutos
- **14:52:** Processo suspenso manualmente

### 2.3. Resultado Final

- **DUEs processadas:** 425/500 (85%)
- **Dados coletados:** 425 DUEs em memória (`dados_consolidados`)
- **Dados salvos no banco:** 0 (processo interrompido antes de salvar)
- **Dados perdidos:** 425 DUEs

---

## 3. PROBLEMAS IDENTIFICADOS

### 3.1. PROBLEMA CRÍTICO: Race Condition no Rate Limiter

**Arquivo:** `/app/src/api/siscomex/token.py`  
**Função:** `_wait_for_safe_limit()`

**Código Problemático:**
```python
def _wait_for_safe_limit(self) -> None:
    while True:
        with self._request_lock:
            if self._requests_in_window < self._safe_request_limit:
                self._requests_in_window += 1
                return  # ← PROBLEMA: Retorna antes da requisição HTTP
```

**Problema:**
1. Múltiplas threads verificam `if self._requests_in_window < self._safe_request_limit` **simultaneamente**
2. Todas passam pela verificação antes do incremento
3. Todas incrementam o contador e retornam
4. A requisição HTTP real acontece **DEPOIS** do return
5. Resultado: várias threads fazem requisições mesmo após o limite

**Evidência:**
- Taxa observada: ~425 req/min = **25.500 req/h**
- Limite configurado: 900 req/h
- **28x acima do limite!**

### 3.2. PROBLEMA: Perda de Dados por Interrupção

**Arquivo:** `/app/src/sync/update_dues.py`

**Fluxo Atual:**
```python
# 1. Coleta TODAS as DUEs em memória
for future in as_completed(...):
    dados_consolidados[tabela].extend(dados)  # Em memória

# 2. Só salva DEPOIS de processar todas
if total_atualizadas > 0:
    salvar_resultados_normalizados(dados_consolidados)  # Nunca chegou aqui
```

**Problema:**
- Dados ficam apenas em memória durante todo o processamento
- Se o processo for interrompido, todos os dados são perdidos
- Não há salvamento incremental ou em lotes

### 3.3. PROBLEMA: Processamento Paralelo Excessivo

**Configuração Atual:**
- 20 workers paralelos processando simultaneamente
- Cada worker faz requisições independentemente
- Competição pelo mesmo recurso (rate limit)

**Problema:**
- Muitos workers aumentam a chance de race condition
- Dificulta o controle preciso de rate limiting
- Pode causar bloqueios da API

### 3.4. PROBLEMA: TokenBucket Desabilitado

**Arquivo:** `/app/src/api/siscomex/token.py`

**Código:**
```python
def _build_rate_limiter(self) -> TokenBucket | None:
    """Rate limiter DESABILITADO para maximizar throughput."""
    return None  # Desabilitado
```

**Problema:**
- TokenBucket foi desabilitado porque "serializa threads"
- Mas isso é exatamente o que precisamos para evitar race condition
- Sistema confia apenas na contagem manual (com race condition)

---

## 4. ANÁLISE TÉCNICA

### 4.1. Fluxo de Execução

```
1. ThreadPoolExecutor inicia 20 workers
2. Cada worker chama _wait_for_safe_limit()
3. Múltiplas threads passam pela verificação simultaneamente (race condition)
4. Todas incrementam contador e fazem requisições
5. Contador ultrapassa limite rapidamente
6. Quando detecta limite, todas aguardam 10.4 minutos
7. Processo é interrompido antes de completar
8. Dados em memória são perdidos
```

### 4.2. Comportamento do Rate Limiter

**Quando atinge limite:**
- ✅ Identifica corretamente o limite
- ✅ Calcula tempo até próxima hora cheia
- ✅ Aguarda o tempo necessário
- ✅ Continua após a espera (não aborta)
- ❌ **MAS:** Race condition permite ultrapassar limite antes

**Tratamento de Erro PUCX-ER1001:**
- ✅ Detecta bloqueio da API
- ✅ Extrai horário de desbloqueio
- ✅ Coordena todas as threads para aguardar juntas
- ✅ Continua após desbloqueio

### 4.3. Métricas Observadas

| Métrica | Valor Observado | Valor Esperado | Status |
|---------|----------------|----------------|--------|
| DUEs processadas | 425/500 | 500/500 | ⚠️ Incompleto |
| Requisições/min | ~425 | ~15 | ❌ 28x acima |
| Requisições/hora | ~25.500 | 900 | ❌ 28x acima |
| Dados salvos | 0 | 425+ | ❌ Perdidos |
| Tempo até limite | ~1 minuto | N/A | ❌ Muito rápido |

---

## 5. SUGESTÕES DE CORREÇÃO

### 5.1. CORREÇÃO CRÍTICA: Race Condition no Rate Limiter

**Prioridade:** 🔴 URGENTE

**Opção A: Usar Semáforo (RECOMENDADO)**

**Arquivo:** `/app/src/api/siscomex/token.py`

```python
import threading

class SharedTokenManager:
    def __init__(self):
        # ... código existente ...
        # Semáforo para limitar requisições simultâneas
        self._rate_limit_semaphore = threading.Semaphore(self._safe_request_limit)
        self._semaphore_reset_time = self._current_window_start()
    
    def _wait_for_safe_limit(self) -> None:
        """Usa semáforo para garantir limite de requisições."""
        now = datetime.now()
        
        # Resetar semáforo a cada hora
        with self._request_lock:
            if now >= self._semaphore_reset_time + timedelta(hours=1):
                # Resetar semáforo liberando todos os slots
                current_value = self._rate_limit_semaphore._value
                for _ in range(self._safe_request_limit - current_value):
                    self._rate_limit_semaphore.release()
                self._semaphore_reset_time = self._current_window_start()
        
        # Aguardar slot disponível (bloqueia automaticamente se limite atingido)
        self._rate_limit_semaphore.acquire()
        
        # Atualizar contador para logs
        with self._request_lock:
            self._requests_in_window += 1
```

**Vantagens:**
- Thread-safe por design
- Bloqueia automaticamente quando limite atingido
- Não permite race condition
- Simples de implementar

**Opção B: Corrigir Loop com Sleep Fora do Lock**

```python
def _wait_for_safe_limit(self) -> None:
    """Pausa automaticamente quando atingir limite preventivo."""
    if self._safe_request_limit <= 0:
        return

    while True:
        with self._request_lock:
            now = datetime.now()
            if now >= self._request_window_start + timedelta(hours=1):
                self._request_window_start = self._current_window_start()
                self._requests_in_window = 0

            if self._requests_in_window < self._safe_request_limit:
                self._requests_in_window += 1
                return  # OK para fazer requisição
        
        # Sleep FORA do lock para não bloquear outras threads
        wait_seconds = self._seconds_until_next_hour()
        logger.warning(
            "⏸️  Limite preventivo SISCOMEX atingido (%s req/h). Aguardando %.1f minutos...",
            self._safe_request_limit,
            wait_seconds / 60.0,
        )
        time.sleep(wait_seconds + 1)
```

**Vantagens:**
- Mantém lógica atual
- Corrige race condition
- Não bloqueia outras threads desnecessariamente

### 5.2. CORREÇÃO: Salvamento Incremental em Lotes

**Prioridade:** 🟡 IMPORTANTE

**Arquivo:** `/app/src/sync/update_dues.py`

**Solução: Salvar a cada N DUEs processadas**

```python
# Configuração
LOTE_SALVAMENTO = 50  # Salvar a cada 50 DUEs

# No loop de processamento
dados_consolidados = {...}
dados_temporarios = {...}  # Para acumular até o lote

for i, future in enumerate(as_completed(future_to_due), 1):
    # ... processar DUE ...
    
    if dados_norm:
        for tabela, dados in dados_norm.items():
            dados_temporarios[tabela].extend(dados)
    
    # Salvar em lotes
    if i % LOTE_SALVAMENTO == 0 or i == len(dues_pendentes):
        logger.info(f"[INFO] Salvando lote de {len(dados_temporarios['due_principal'])} DUEs...")
        salvar_resultados_normalizados(dados_temporarios)
        
        # Consolidar com dados principais
        for tabela, dados in dados_temporarios.items():
            dados_consolidados[tabela].extend(dados)
        
        # Limpar temporários
        dados_temporarios = {k: [] for k in dados_consolidados.keys()}
```

**Vantagens:**
- Dados salvos progressivamente
- Menor perda em caso de interrupção
- Melhor rastreabilidade

### 5.3. CORREÇÃO: Reduzir Workers Paralelos

**Prioridade:** 🟡 IMPORTANTE

**Arquivo:** `/app/src/sync/update_dues.py`

**Solução: Calcular workers dinamicamente**

```python
from src.core.constants import SISCOMEX_SAFE_REQUEST_LIMIT

# Calcular workers baseado no limite de rate
# Ex: 900 req/h / 100 = 9 workers máximo
# Isso garante que não ultrapasse o limite mesmo com race condition
max_workers_calculado = max(1, int(SISCOMEX_SAFE_REQUEST_LIMIT / 100))
max_workers = min(max_workers, max_workers_calculado)

logger.info(f"[INFO] Workers ajustados: {max_workers} (limite: {SISCOMEX_SAFE_REQUEST_LIMIT} req/h)")
```

**Vantagens:**
- Reduz competição por rate limit
- Facilita controle preciso
- Menor chance de race condition

### 5.4. CORREÇÃO: Reativar TokenBucket (Opcional)

**Prioridade:** 🟢 RECOMENDADO

**Arquivo:** `/app/src/api/siscomex/token.py`

**Solução: Reativar com configuração adequada**

```python
def _build_rate_limiter(self) -> TokenBucket | None:
    """Rate limiter para controlar taxa de requisições."""
    from src.core.constants import SISCOMEX_RATE_LIMIT_HOUR, SISCOMEX_RATE_LIMIT_BURST
    
    if SISCOMEX_RATE_LIMIT_HOUR <= 0:
        return None
    
    # 900 req/h = 0.25 req/s (com margem de segurança)
    rate_per_sec = SISCOMEX_SAFE_REQUEST_LIMIT / 3600.0
    capacity = SISCOMEX_RATE_LIMIT_BURST  # Ex: 20
    
    return TokenBucket(rate_per_sec, capacity)
```

**Uso:**
```python
def request(self, method: str, url: str, **kwargs) -> requests.Response:
    # Rate limiting em camadas
    self._wait_for_safe_limit()  # Controle por hora
    if self._limiter:
        self._limiter.acquire()  # Controle por segundo (TokenBucket)
    
    # Fazer requisição
    resposta = self.session.request(method, url, **kwargs)
    # ...
```

**Vantagens:**
- Camada adicional de proteção
- Controle mais fino (por segundo)
- Suporta burst (picos temporários)

### 5.5. CORREÇÃO: Melhorar Logging e Monitoramento

**Prioridade:** 🟢 RECOMENDADO

**Sugestões:**
1. Logar taxa de requisições em tempo real
2. Alertar quando próximo do limite (ex: 80%)
3. Logar quando dados são salvos em lotes
4. Métricas de performance (req/s, DUEs/s)

```python
# Exemplo de logging melhorado
if self._requests_in_window >= int(self._safe_request_limit * 0.8):
    logger.warning(
        "⚠️  Aproximando do limite: %d/%d req/h (%.1f%%)",
        self._requests_in_window,
        self._safe_request_limit,
        (self._requests_in_window / self._safe_request_limit) * 100
    )
```

---

## 6. PLANO DE IMPLEMENTAÇÃO

### Fase 1: Correções Críticas (URGENTE)
1. ✅ Corrigir race condition no `_wait_for_safe_limit()` (Semáforo)
2. ✅ Implementar salvamento em lotes
3. ✅ Reduzir workers paralelos dinamicamente

**Prazo:** 1-2 dias  
**Impacto:** Resolve perda de dados e race condition

### Fase 2: Melhorias (IMPORTANTE)
1. Reativar TokenBucket como camada adicional
2. Melhorar logging e monitoramento
3. Adicionar métricas de performance

**Prazo:** 3-5 dias  
**Impacto:** Melhora controle e observabilidade

### Fase 3: Otimizações (RECOMENDADO)
1. Implementar retry inteligente
2. Cache de dados quando possível
3. Otimizar queries de banco

**Prazo:** 1-2 semanas  
**Impacto:** Melhora performance geral

---

## 7. TESTES RECOMENDADOS

### Teste 1: Rate Limiting
- Processar 100 DUEs
- Verificar que não ultrapassa 900 req/h
- Confirmar que threads aguardam corretamente

### Teste 2: Salvamento em Lotes
- Processar 200 DUEs
- Interromper no meio (ex: 150 DUEs)
- Verificar que pelo menos 100-150 DUEs foram salvas

### Teste 3: Recuperação após Limite
- Processar até atingir limite
- Aguardar reset da janela
- Verificar que continua processando

### Teste 4: Stress Test
- Processar 1000 DUEs
- Monitorar taxa de requisições
- Verificar que não ultrapassa limite
- Confirmar que todos os dados são salvos

---

## 8. CONCLUSÕES

### Problemas Identificados
1. ✅ **Race condition crítica** no rate limiter
2. ✅ **Perda de dados** por falta de salvamento incremental
3. ✅ **Processamento paralelo excessivo** (20 workers)
4. ✅ **TokenBucket desabilitado** (camada de proteção removida)

### Impacto
- **Alto:** Perda de dados e violação de rate limiting
- **Médio:** Ineficiência e desperdício de recursos
- **Baixo:** Falta de observabilidade

### Soluções Propostas
1. ✅ Semáforo para rate limiting thread-safe
2. ✅ Salvamento incremental em lotes
3. ✅ Workers dinâmicos baseados no limite
4. ✅ TokenBucket como camada adicional

### Próximos Passos
1. Implementar correções críticas (Fase 1)
2. Testar em ambiente de teste
3. Validar que resolve os problemas
4. Deploy em produção com monitoramento

---

## 9. ANEXOS

### 9.1. Logs Relevantes

```
2026-01-25 14:49:38 | INFO | [PROGRESSO] 425/500...
2026-01-25 14:49:38 | WARNING | ⏸️  Limite preventivo SISCOMEX atingido (900 req/h). Aguardando 10.4 minutos...
```

### 9.2. Configurações Atuais

- `SISCOMEX_SAFE_REQUEST_LIMIT`: 900 req/h
- `SISCOMEX_RATE_LIMIT_HOUR`: 1000 req/h
- `DUE_DOWNLOAD_WORKERS`: 20 (padrão)
- `MAX_ATUALIZACOES_POR_EXECUCAO`: 500

### 9.3. Arquivos Afetados

- `/app/src/api/siscomex/token.py` (rate limiting)
- `/app/src/sync/update_dues.py` (processamento e salvamento)
- `/app/src/sync/new_dues.py` (variável não inicializada - corrigido)

---

**Relatório gerado em:** 25/01/2026  
**Versão:** 1.0  
**Autor:** Análise Técnica - Sistema Controle Siscomex
