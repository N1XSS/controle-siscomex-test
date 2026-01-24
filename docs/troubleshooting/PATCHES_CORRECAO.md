# 🔧 PATCHES DE CORREÇÃO - SISTEMA SISCOMEX

Este arquivo contém os patches prontos para aplicar as correções nos bugs identificados.

---

## 📦 PATCH #1: Corrigir Import com Escopo Incorreto (Bug #2)

### Arquivo: `/app/src/sync/new_dues.py`

### Localização: Início do arquivo (após os imports existentes)

```python
# ADICIONAR estes imports no topo do arquivo, após os imports existentes:

from src.processors.due import (
    consultar_due_por_nf,
    consultar_due_completa,
    processar_dados_due,
    salvar_resultados_normalizados,
)
```

### Localização: Dentro da função `processar_novas_nfs()` (~linha 280-290)

**REMOVER este bloco:**
```python
        # 5. Importar funcoes
        try:
            from src.processors.due import consultar_due_por_nf, processar_dados_due, salvar_resultados_normalizados, consultar_due_completa
        except ImportError as e:
            raise DUEProcessingError(f"Nao foi possivel importar due_processor: {e}") from e
```

**SUBSTITUIR por:**
```python
        # 5. Validar imports (já importados no topo do arquivo)
        # Imports movidos para o escopo global para evitar NameError em funções paralelas
```

---

## 📦 PATCH #2: Corrigir Reconexão do Banco (Bug #1)

### Arquivo: `/app/src/sync/new_dues.py`

### Localização: Função `salvar_novos_vinculos()` (~linha 160-180)

**SUBSTITUIR a função completa por:**

```python
def salvar_novos_vinculos(novos_vinculos: dict[str, str]) -> None:
    """Salva novos vinculos NF->DUE no PostgreSQL.

    Args:
        novos_vinculos: Mapa {chave_nf: numero_due}.
    """
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
    
    # Tentar salvar no PostgreSQL com retry
    max_tentativas = 3
    for tentativa in range(max_tentativas):
        try:
            # Verificar e reconectar se necessário
            if not db_manager.conn or db_manager.conn.closed:
                logger.info(f"Reconectando ao banco (tentativa {tentativa + 1}/{max_tentativas})...")
                if not db_manager.conectar():
                    logger.warning(f"Falha ao reconectar (tentativa {tentativa + 1})")
                    if tentativa < max_tentativas - 1:
                        time.sleep(2)
                        continue
                    else:
                        break
            
            # Tentar inserir
            count = db_manager.inserir_vinculos_batch(registros)
            if count > 0:
                logger.info(f"[OK] {count} novos vinculos salvos no PostgreSQL")
                return
            else:
                logger.warning(f"[AVISO] Nenhum vinculo foi salvo (tentativa {tentativa + 1})")
                
        except Exception as e:
            logger.warning(f"[AVISO] Erro ao salvar vinculos (tentativa {tentativa + 1}/{max_tentativas}): {e}")
            if tentativa < max_tentativas - 1:
                time.sleep(2)
                continue
    
    # Fallback para CSV apenas se todas as tentativas falharem
    logger.error("[ERRO] Todas as tentativas de salvar no PostgreSQL falharam!")
    logger.info("[FALLBACK] Salvando em CSV como backup...")
    
    try:
        import pandas as pd
        df = pd.DataFrame(registros)
        os.makedirs(os.path.dirname(CAMINHO_VINCULO), exist_ok=True)
        df.to_csv(CAMINHO_VINCULO, sep=';', index=False, encoding='utf-8-sig')
        logger.info(f"[OK] {len(registros)} vinculos salvos em CSV: {CAMINHO_VINCULO}")
        logger.warning("[ATENÇÃO] Dados em CSV precisam ser importados manualmente!")
    except Exception as e:
        logger.error(f"[ERRO CRÍTICO] Falha ao salvar em CSV: {e}")
        logger.error(f"[PERDA DE DADOS] {len(registros)} vínculos NÃO foram salvos!")
```

---

## 📦 PATCH #3: Corrigir Mapeamento de Campos da API (Bug #3)

### Arquivo: `/app/src/processors/due.py`

### 3.1. Corrigir Campo `exportador_nome` em Itens

**Localização: Função que processa itens (~linha 450-500)**

**ANTES:**
```python
            # Exportador
            'exportador_numeroDoDocumento': item.get('exportador', {}).get('numeroDoDocumento', ''),
            'exportador_tipoDoDocumento': item.get('exportador', {}).get('tipoDoDocumento', ''),
            'exportador_nome': item.get('exportador', {}).get('nome', ''),  # ❌ CAMPO NÃO EXISTE
            'exportador_estrangeiro': item.get('exportador', {}).get('estrangeiro', False),
```

**DEPOIS:**
```python
            # Exportador
            'exportador_numeroDoDocumento': item.get('exportador', {}).get('numeroDoDocumento', ''),
            'exportador_tipoDoDocumento': item.get('exportador', {}).get('tipoDoDocumento', ''),
            # REMOVIDO: 'exportador_nome' - Campo não disponível na API Siscomex
            # Se necessário, pode ser obtido consultando API da Receita com o CNPJ
            'exportador_nome': '',  # Manter vazio até implementar consulta externa
            'exportador_estrangeiro': item.get('exportador', {}).get('estrangeiro', False),
```

**OU (melhor opção):**
```python
            # Exportador
            'exportador_numeroDoDocumento': item.get('exportador', {}).get('numeroDoDocumento', ''),
            'exportador_tipoDoDocumento': item.get('exportador', {}).get('tipoDoDocumento', ''),
            # Usar identificação completa ao invés de nome
            'exportador_identificacao': (
                f"{item.get('exportador', {}).get('tipoDoDocumento', '')} "
                f"{item.get('exportador', {}).get('numeroDoDocumento', '')}"
            ).strip(),
            'exportador_estrangeiro': item.get('exportador', {}).get('estrangeiro', False),
```

### 3.2. Corrigir Campos de Eventos

**Localização: Função que processa eventos (~linha 350-380)**

**ANTES:**
```python
    # 2. Eventos do histórico
    for evento in dados_due.get('eventosDoHistorico', []):
        evento_row = {
            'numero_due': numero_due,
            'dataEHoraDoEvento': evento.get('dataEHoraDoEvento', ''),
            'evento': evento.get('evento', ''),
            'responsavel': evento.get('responsavel', ''),
            'informacoesAdicionais': evento.get('informacoesAdicionais', ''),
            'detalhes': evento.get('detalhes', ''),      # ❌ NÃO EXISTE NA API
            'motivo': evento.get('motivo', '')           # ❌ NÃO EXISTE NA API
        }
        dados_normalizados['due_eventos_historico'].append(evento_row)
```

**DEPOIS:**
```python
    # 2. Eventos do histórico
    for evento in dados_due.get('eventosDoHistorico', []):
        evento_row = {
            'numero_due': numero_due,
            'dataEHoraDoEvento': evento.get('dataEHoraDoEvento', ''),
            'evento': evento.get('evento', ''),
            'responsavel': evento.get('responsavel', ''),
            'informacoesAdicionais': evento.get('informacoesAdicionais', ''),
            # REMOVIDO: 'detalhes' e 'motivo' - Campos não disponíveis na API Siscomex
            # API retorna apenas: dataEHoraDoEvento, evento, responsavel, informacoesAdicionais (opcional)
        }
        dados_normalizados['due_eventos_historico'].append(evento_row)
```

---

## 📦 PATCH #4: Melhorar Validação e Logging

### Arquivo: `/app/src/sync/new_dues.py`

### Adicionar função de validação após sincronização

**Localização: Após a função `processar_novas_nfs()`, adicionar:**

```python
def validar_sincronizacao() -> dict[str, Any]:
    """Valida a integridade dos dados após sincronização.
    
    Returns:
        Dicionário com estatísticas e problemas encontrados.
    """
    if not db_manager.conn:
        db_manager.conectar()
    
    problemas = []
    stats = {}
    
    with db_manager.get_connection() as conn:
        with conn.cursor() as cur:
            # 1. Verificar vínculos órfãos
            cur.execute('''
                SELECT COUNT(*) 
                FROM nf_due_vinculo v
                LEFT JOIN due_principal d ON v.numero_due = d.numero
                WHERE d.numero IS NULL
            ''')
            vinculos_orfaos = cur.fetchone()[0]
            if vinculos_orfaos > 0:
                problemas.append(f"CRÍTICO: {vinculos_orfaos} vínculos sem DUE correspondente")
            
            # 2. Verificar DUEs sem itens
            cur.execute('''
                SELECT COUNT(*)
                FROM due_principal d
                LEFT JOIN due_itens i ON d.numero = i.numero_due
                WHERE i.numero_due IS NULL
            ''')
            dues_sem_itens = cur.fetchone()[0]
            if dues_sem_itens > 0:
                problemas.append(f"ATENÇÃO: {dues_sem_itens} DUEs sem itens")
            
            # 3. Estatísticas
            cur.execute('SELECT COUNT(*) FROM nf_due_vinculo')
            stats['vinculos'] = cur.fetchone()[0]
            
            cur.execute('SELECT COUNT(*) FROM due_principal')
            stats['dues'] = cur.fetchone()[0]
            
            cur.execute('SELECT COUNT(*) FROM due_itens')
            stats['itens'] = cur.fetchone()[0]
    
    return {
        'status': 'OK' if not problemas else 'ATENÇÃO',
        'problemas': problemas,
        'estatisticas': stats
    }
```

### Adicionar chamada de validação no final de `processar_novas_nfs()`

**ANTES do final da função, adicionar:**

```python
        # 9. Validar integridade
        logger.info("\n[VALIDANDO INTEGRIDADE DOS DADOS...]")
        validacao = validar_sincronizacao()
        
        logger.info(f"\n[ESTATÍSTICAS]")
        logger.info(f"  Vínculos: {validacao['estatisticas'].get('vinculos', 0)}")
        logger.info(f"  DUEs: {validacao['estatisticas'].get('dues', 0)}")
        logger.info(f"  Itens: {validacao['estatisticas'].get('itens', 0)}")
        
        if validacao['problemas']:
            logger.warning(f"\n[PROBLEMAS ENCONTRADOS]")
            for problema in validacao['problemas']:
                logger.warning(f"  • {problema}")
        else:
            logger.info("\n[OK] Nenhum problema de integridade encontrado!")
```

---

## 📦 PATCH #5: Schema do Banco de Dados (Opcional)

### Criar Migration para Limpar Colunas Desnecessárias

**Arquivo: Criar novo arquivo `migrations/001_clean_unused_columns.sql`**

```sql
-- Migration: Limpar colunas que não são populadas pela API
-- Data: 2026-01-20
-- Motivo: API Siscomex não retorna estes campos

BEGIN;

-- 1. Adicionar comentários em colunas vazias (documentação)
COMMENT ON COLUMN due_eventos_historico.detalhes IS 
    'DEPRECATED - Campo não disponível na API Siscomex. Sempre NULL.';

COMMENT ON COLUMN due_eventos_historico.motivo IS 
    'DEPRECATED - Campo não disponível na API Siscomex. Sempre NULL.';

COMMENT ON COLUMN due_itens.exportador_nome IS 
    'DEPRECATED - Campo não disponível na API Siscomex. API retorna apenas numeroDoDocumento e tipoDoDocumento.';

-- 2. (Opcional) Remover colunas completamente
-- DESCOMENTE SE QUISER REMOVER AS COLUNAS:

-- ALTER TABLE due_eventos_historico 
--     DROP COLUMN IF EXISTS detalhes,
--     DROP COLUMN IF EXISTS motivo;

-- ALTER TABLE due_itens
--     DROP COLUMN IF EXISTS exportador_nome;

-- 3. Adicionar índices para melhorar performance
CREATE INDEX IF NOT EXISTS idx_due_eventos_numero_due 
    ON due_eventos_historico(numero_due);

CREATE INDEX IF NOT EXISTS idx_due_itens_numero_due 
    ON due_itens(numero_due);

CREATE INDEX IF NOT EXISTS idx_nf_due_vinculo_numero_due 
    ON nf_due_vinculo(numero_due);

-- 4. Adicionar constraint para garantir integridade
ALTER TABLE nf_due_vinculo
    ADD CONSTRAINT fk_nf_due_vinculo_due_principal
    FOREIGN KEY (numero_due) REFERENCES due_principal(numero)
    ON DELETE CASCADE;

COMMIT;
```

---

## 🧪 SCRIPT DE TESTE

### Criar script para testar as correções

**Arquivo: `/app/tests/test_sincronizacao.py`**

```python
"""
Script de teste para validar correções de bugs.
Uso: python -m tests.test_sincronizacao
"""

import sys
sys.path.insert(0, '/app')

from src.database.manager import db_manager
from src.processors.due import consultar_due_completa, processar_dados_due
from src.api.siscomex.token import token_manager
import os

def test_import_escopo():
    """Testa se imports estão no escopo correto."""
    print("\n" + "="*80)
    print("TEST 1: Validar Imports no Escopo Global")
    print("="*80)
    
    try:
        from src.sync.new_dues import (
            consultar_due_completa,
            processar_dados_due,
            baixar_due_completa
        )
        print("✅ Imports estão no escopo global")
        print("✅ Função baixar_due_completa tem acesso aos imports")
        return True
    except ImportError as e:
        print(f"❌ FALHA: {e}")
        return False

def test_reconexao_banco():
    """Testa reconexão do banco."""
    print("\n" + "="*80)
    print("TEST 2: Validar Reconexão do Banco")
    print("="*80)
    
    try:
        # Conectar
        db_manager.conectar()
        print("✅ Conexão inicial OK")
        
        # Simular fechamento
        db_manager.desconectar()
        print("✅ Desconexão OK")
        
        # Verificar se reconecta
        if not db_manager.conn or db_manager.conn.closed:
            db_manager.conectar()
            print("✅ Reconexão OK")
        
        # Testar operação
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT 1')
                result = cur.fetchone()[0]
                if result == 1:
                    print("✅ Query após reconexão OK")
                    return True
    except Exception as e:
        print(f"❌ FALHA: {e}")
        return False
    finally:
        db_manager.desconectar()

def test_mapeamento_api():
    """Testa mapeamento de campos da API."""
    print("\n" + "="*80)
    print("TEST 3: Validar Mapeamento de Campos da API")
    print("="*80)
    
    try:
        # Configurar
        client_id = os.getenv('SISCOMEX_CLIENT_ID')
        client_secret = os.getenv('SISCOMEX_CLIENT_SECRET')
        token_manager.configurar_credenciais(client_id, client_secret)
        token_manager.autenticar()
        
        # Buscar uma DUE de teste
        db_manager.conectar()
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT numero FROM due_principal LIMIT 1')
                numero_due = cur.fetchone()[0]
        
        print(f"Testando com DUE: {numero_due}")
        
        # Consultar API
        dados_due = consultar_due_completa(numero_due)
        if not dados_due:
            print("❌ FALHA: Não conseguiu consultar DUE")
            return False
        
        # Validar estrutura
        print("✅ DUE consultada com sucesso")
        
        # Verificar eventos
        if 'eventosDoHistorico' in dados_due:
            eventos = dados_due['eventosDoHistorico']
            if eventos:
                evento = eventos[0]
                campos_esperados = ['dataEHoraDoEvento', 'evento', 'responsavel']
                campos_invalidos = ['detalhes', 'motivo', 'tipo_evento', 'data']
                
                for campo in campos_esperados:
                    if campo in evento:
                        print(f"✅ Campo válido: {campo}")
                    else:
                        print(f"⚠️  Campo esperado não encontrado: {campo}")
                
                for campo in campos_invalidos:
                    if campo in evento:
                        print(f"❌ Campo inválido encontrado: {campo}")
                    else:
                        print(f"✅ Campo inválido corretamente ausente: {campo}")
        
        # Verificar itens
        if 'itens' in dados_due:
            itens = dados_due['itens']
            if itens:
                item = itens[0]
                if 'exportador' in item:
                    exportador = item['exportador']
                    if 'nome' in exportador:
                        print("❌ Campo 'exportador.nome' existe (inesperado)")
                    else:
                        print("✅ Campo 'exportador.nome' ausente (correto)")
                    
                    if 'numeroDoDocumento' in exportador:
                        print("✅ Campo 'exportador.numeroDoDocumento' presente (correto)")
        
        print("\n✅ Mapeamento validado com sucesso")
        return True
        
    except Exception as e:
        print(f"❌ FALHA: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db_manager.desconectar()

def main():
    """Executa todos os testes."""
    print("\n" + "="*80)
    print("SUITE DE TESTES - CORREÇÕES DE BUGS SISCOMEX")
    print("="*80)
    
    resultados = {
        'Test 1 - Imports': test_import_escopo(),
        'Test 2 - Reconexão': test_reconexao_banco(),
        'Test 3 - Mapeamento API': test_mapeamento_api(),
    }
    
    print("\n" + "="*80)
    print("RESUMO DOS TESTES")
    print("="*80)
    
    total = len(resultados)
    passou = sum(1 for v in resultados.values() if v)
    
    for nome, resultado in resultados.items():
        status = "✅ PASSOU" if resultado else "❌ FALHOU"
        print(f"{status} - {nome}")
    
    print("\n" + "-"*80)
    print(f"Resultado: {passou}/{total} testes passaram")
    print("="*80)
    
    return passou == total

if __name__ == "__main__":
    sucesso = main()
    sys.exit(0 if sucesso else 1)
```

---

## 📋 CHECKLIST DE APLICAÇÃO DOS PATCHES

### Antes de Aplicar
- [ ] Fazer backup do banco de dados
- [ ] Fazer backup dos arquivos que serão modificados
- [ ] Revisar todos os patches com a equipe
- [ ] Testar em ambiente de desenvolvimento primeiro

### Aplicar Patches
- [ ] Patch #1: Corrigir imports (Bug #2) - CRÍTICO
- [ ] Patch #2: Corrigir reconexão (Bug #1) - CRÍTICO
- [ ] Patch #3: Corrigir mapeamento API (Bug #3) - ALTO
- [ ] Patch #4: Adicionar validação - RECOMENDADO
- [ ] Patch #5: Limpar schema do banco - OPCIONAL

### Após Aplicar
- [ ] Executar script de testes
- [ ] Executar sincronização manual de teste
- [ ] Validar integridade dos dados
- [ ] Monitorar logs por 24h
- [ ] Documentar mudanças no README

### Deploy em Produção
- [ ] Criar tag de versão no Git
- [ ] Fazer commit das mudanças
- [ ] Fazer deploy no container
- [ ] Reiniciar serviço
- [ ] Validar próxima sincronização agendada

---

**Arquivo criado em:** 20/01/2026  
**Para ser aplicado em:** Container testes-controle-siscomex-teste-tu8gsi  
**Versão:** 1.0.0
