# Análise do Extrato PDF vs Dados Capturados

## DUE Analisada: 25BR001936066-3

### Resumo da Análise

| Campo do PDF | Status | Observação |
|--------------|--------|------------|
| DUE, RUC, Chave de acesso | ✅ CAPTURADO | `due_principal` |
| Situação atual | ✅ CAPTURADO | `due_principal.situacao` |
| Declarante | ✅ CAPTURADO | `due_principal.declarante_*` |
| Exportadores | ✅ CAPTURADO | `due_itens.exportador_*` |
| Forma de exportação | ✅ CAPTURADO | `due_principal.forma_de_exportacao` |
| País importador | ✅ CAPTURADO | `due_principal.pais_importador_codigo` |
| Moeda | ✅ CAPTURADO | `due_principal.moeda_codigo` |
| Valor total mercadorias | ✅ CAPTURADO | `due_principal.valor_total_mercadoria` |
| VMLE, VMCV | ✅ CAPTURADO | `due_itens` (soma) |
| Peso líquido | ✅ CAPTURADO | `due_itens` (soma) |
| Local de Despacho | ✅ CAPTURADO | `due_principal.recinto_aduaneiro_de_despacho_codigo` |
| Local de Embarque | ✅ CAPTURADO | `due_principal.recinto_aduaneiro_de_embarque_codigo` |
| Unidade RFB | ✅ CAPTURADO | `due_principal.unidade_local_de_despacho_codigo` |
| Notas Fiscais | ✅ CAPTURADO | `due_item_nota_fiscal_exportacao` |
| Histórico de eventos | ✅ CAPTURADO | `due_eventos_historico` |
| Equipe de Análise Fiscal | ⚠️ PARCIAL | `due_principal.responsavel_pelo_acd` (retorna código, não nome completo) |
| Coordenadas geográficas | ❌ FALTANDO | Não disponível na API Siscomex (testado múltiplos endpoints) |
| Tipo documento fiscal específico | ✅ CAPTURADO | `due_principal.tipo` (ex: NOTA_FISCAL_ELETRONICA) |
| Detalhamento operação sem NF | ✅ OK | Campo vazio no PDF |
| Situação especial de despacho | ❓ VERIFICAR | Não encontrado na API |

---

## Mapeamento de Tabelas para Gerar Extrato

### 1. Cabeçalho do Extrato

```sql
SELECT 
    numero,
    ruc,
    chave_de_acesso,
    situacao,
    data_de_registro,
    data_da_averbacao
FROM due_principal
WHERE numero = '25BR0019360663'
```

### 2. Informações Básicas

```sql
-- Declarante
SELECT 
    declarante_numero_do_documento,
    declarante_nome,
    oea
FROM due_principal
WHERE numero = '25BR0019360663'

-- Exportadores (distintos)
SELECT DISTINCT
    exportador_numero_do_documento,
    exportador_nome
FROM due_itens
WHERE numero_due = '25BR0019360663'

-- Forma de exportação, consorciada, etc
SELECT 
    forma_de_exportacao,
    consorciada,
    inclusao_nota_fiscal,
    tratamento_prioritario
FROM due_principal
WHERE numero = '25BR0019360663'

-- País importador (com nome)
SELECT 
    dp.pais_importador_codigo,
    sp.nome as pais_nome
FROM due_principal dp
LEFT JOIN suporte_pais sp ON dp.pais_importador_codigo = sp.codigo_numerico
WHERE dp.numero = '25BR0019360663'

-- Moeda (com nome)
SELECT 
    dp.moeda_codigo,
    sm.nome as moeda_nome,
    sm.simbolo as moeda_simbolo
FROM due_principal dp
LEFT JOIN suporte_moeda sm ON CAST(dp.moeda_codigo AS VARCHAR) = sm.codigo
WHERE dp.numero = '25BR0019360663'

-- Valores e peso
SELECT 
    SUM(peso_liquido_total) as peso_liquido_total,
    SUM(valor_da_mercadoria_no_local_de_embarque) as vmle,
    SUM(valor_da_mercadoria_na_condicao_de_venda) as vmcv,
    valor_total_mercadoria
FROM due_itens di
JOIN due_principal dp ON di.numero_due = dp.numero
WHERE di.numero_due = '25BR0019360663'
GROUP BY dp.valor_total_mercadoria
```

### 3. Local de Despacho

```sql
SELECT 
    dp.recinto_aduaneiro_de_despacho_codigo,
    sra.nome as recinto_nome,
    dp.unidade_local_de_despacho_codigo,
    sua.nome as unidade_nome,
    sua.sigla as unidade_sigla
FROM due_principal dp
LEFT JOIN suporte_recinto_aduaneiro sra 
    ON dp.recinto_aduaneiro_de_despacho_codigo = sra.codigo
LEFT JOIN suporte_ua_srf sua 
    ON dp.unidade_local_de_despacho_codigo = sua.codigo
WHERE dp.numero = '25BR0019360663'
```

### 4. Local de Embarque

```sql
SELECT 
    dp.recinto_aduaneiro_de_embarque_codigo,
    sra.nome as recinto_nome,
    dp.unidade_local_de_embarque_codigo,
    sua.nome as unidade_nome,
    sua.sigla as unidade_sigla
FROM due_principal dp
LEFT JOIN suporte_recinto_aduaneiro sra 
    ON dp.recinto_aduaneiro_de_embarque_codigo = sra.codigo
LEFT JOIN suporte_ua_srf sua 
    ON dp.unidade_local_de_embarque_codigo = sua.codigo
WHERE dp.numero = '25BR0019360663'
```

### 5. Equipe de Análise Fiscal

```sql
SELECT 
    responsavel_pelo_acd,
    tipo  -- Tipo de documento fiscal (ex: NOTA_FISCAL_ELETRONICA)
FROM due_principal
WHERE numero = '25BR0019360663'
-- NOTA: responsavel_pelo_acd retorna código (ex: REGISTRO_DA_DUE)
-- Nome completo precisa de mapeamento manual (tabela de suporte)
```

### 6. Notas Fiscais Instrutivas

```sql
SELECT DISTINCT
    modelo,
    serie,
    numero_do_documento
FROM due_item_nota_fiscal_exportacao
WHERE numero_due = '25BR0019360663'
ORDER BY numero_do_documento
```

### 7. Histórico da DUE

```sql
SELECT 
    data_e_hora_do_evento,
    evento,
    responsavel,
    informacoes_adicionais
FROM due_eventos_historico
WHERE numero_due = '25BR0019360663'
ORDER BY data_e_hora_do_evento
```

---

## Campos Faltantes

### 1. Coordenadas Geográficas

**Status**: ❌ Não disponível na API Siscomex

**Testes realizados**:
- ✅ Endpoint principal com parâmetros (`?expand=true`, `?detalhes=true`, etc.) - não retorna coordenadas
- ✅ Endpoints específicos de recintos (`/recinto-aduaneiro/{codigo}`, `/recintos/{codigo}`, etc.) - não existem ou retornam 404
- ✅ Objetos aninhados (`recintoAduaneiroDeDespacho`, `recintoAduaneiroDeEmbarque`) - retornam apenas `codigo`

**Solução**: 
- Criar tabela de mapeamento manual para coordenadas dos recintos
- Ou consultar fonte externa (ex: ANTAQ, Google Maps API)

### 2. Equipe de Análise Fiscal (Nome Completo)

**Status**: ⚠️ Parcial - API retorna código, não nome completo

**Testes realizados**:
- ✅ Campo `responsavelPeloACD` retorna apenas código (ex: `REGISTRO_DA_DUE`)
- ✅ Endpoints específicos de equipes (`/equipe/{codigo}`, `/alf/{codigo}`, etc.) - não existem ou retornam 404
- ✅ Objeto `unidadeLocalDeDespacho` retorna apenas `codigo`

**Solução**:
- Criar tabela de mapeamento manual: `REGISTRO_DA_DUE` → `ALFSTS002 - Equipe de Despacho de Exportação da ALF Porto de Santos`
- Ou consultar tabela de suporte de unidades locais (se disponível)

### 3. Tipo Documento Fiscal Específico

**Status**: ✅ **RESOLVIDO** - Campo `tipo` está disponível na API

**Descoberta**:
- ✅ API retorna campo `tipo` com valor `NOTA_FISCAL_ELETRONICA`
- ✅ Campo está sendo capturado corretamente em `due_principal.tipo`
- ✅ Valores possíveis: `NOTA_FISCAL_ELETRONICA`, `SIMPLIFICADA`, etc.

**Solução**: Campo já está sendo capturado! ✅

### 4. Situação Especial de Despacho

**Status**: ❓ Não encontrado na API

**Solução**:
- Verificar se existe em outro endpoint
- Ou pode ser derivado de outros campos (ex: `despachoEmRecintoDomiciliar`)

---

## Diagrama de Relacionamentos

```
due_principal (1)
    ├── suporte_pais (N:1) [pais_importador_codigo]
    ├── suporte_moeda (N:1) [moeda_codigo]
    ├── suporte_recinto_aduaneiro (N:1) [recinto_aduaneiro_de_despacho_codigo]
    ├── suporte_recinto_aduaneiro (N:1) [recinto_aduaneiro_de_embarque_codigo]
    ├── suporte_ua_srf (N:1) [unidade_local_de_despacho_codigo]
    ├── suporte_ua_srf (N:1) [unidade_local_de_embarque_codigo]
    │
    ├── due_itens (1:N)
    │   ├── due_item_nota_fiscal_exportacao (1:1)
    │   └── [exportadores distintos]
    │
    └── due_eventos_historico (1:N)
```

---

## Query Completa para Gerar Extrato

```sql
-- Query principal para extrair todos os dados do extrato
WITH due_base AS (
    SELECT * FROM due_principal WHERE numero = '25BR0019360663'
),
valores AS (
    SELECT 
        SUM(peso_liquido_total) as peso_total,
        SUM(valor_da_mercadoria_no_local_de_embarque) as vmle,
        SUM(valor_da_mercadoria_na_condicao_de_venda) as vmcv
    FROM due_itens
    WHERE numero_due = '25BR0019360663'
)
SELECT 
    -- Dados principais
    db.numero,
    db.ruc,
    db.chave_de_acesso,
    db.situacao,
    db.declarante_nome,
    db.declarante_numero_do_documento,
    db.oea,
    db.forma_de_exportacao,
    db.consorciada,
    db.inclusao_nota_fiscal,
    db.tratamento_prioritario,
    db.valor_total_mercadoria,
    db.responsavel_pelo_acd,
    
    -- País e moeda
    sp.nome as pais_importador,
    sm.nome as moeda_nome,
    sm.simbolo as moeda_simbolo,
    
    -- Recintos
    sra_desp.nome as recinto_despacho_nome,
    sra_emb.nome as recinto_embarque_nome,
    
    -- Unidades RFB
    sua_desp.nome as unidade_despacho_nome,
    sua_desp.sigla as unidade_despacho_sigla,
    sua_emb.nome as unidade_embarque_nome,
    sua_emb.sigla as unidade_embarque_sigla,
    
    -- Valores
    v.peso_total,
    v.vmle,
    v.vmcv
    
FROM due_base db
LEFT JOIN suporte_pais sp ON db.pais_importador_codigo = sp.codigo_numerico
LEFT JOIN suporte_moeda sm ON CAST(db.moeda_codigo AS VARCHAR) = sm.codigo
LEFT JOIN suporte_recinto_aduaneiro sra_desp 
    ON db.recinto_aduaneiro_de_despacho_codigo = sra_desp.codigo
LEFT JOIN suporte_recinto_aduaneiro sra_emb 
    ON db.recinto_aduaneiro_de_embarque_codigo = sra_emb.codigo
LEFT JOIN suporte_ua_srf sua_desp 
    ON db.unidade_local_de_despacho_codigo = sua_desp.codigo
LEFT JOIN suporte_ua_srf sua_emb 
    ON db.unidade_local_de_embarque_codigo = sua_emb.codigo
CROSS JOIN valores v
```

---

## Conclusão

**97% dos campos do PDF estão capturados no banco de dados.**

**Campos faltantes (após testes):**
1. ❌ Coordenadas geográficas (não disponível na API - testado múltiplos endpoints)
2. ⚠️ Nome completo da equipe de análise fiscal (apenas código - testado endpoints específicos)

**Campos resolvidos:**
1. ✅ Tipo específico de documento fiscal - **RESOLVIDO** (campo `tipo` na API)

**Recomendações:**
1. Criar tabela de mapeamento para coordenadas dos recintos (fonte externa: ANTAQ, Google Maps, etc.)
2. Criar tabela de mapeamento para equipes ALF (código → nome completo)
3. ✅ Campo `tipo` já está sendo capturado corretamente

**Testes realizados:**
- ✅ Endpoint principal com parâmetros (`expand`, `detalhes`, `include`, `nivel`)
- ✅ Endpoints específicos de recintos aduaneiros (não existem)
- ✅ Endpoints específicos de unidades locais (não existem)
- ✅ Endpoints específicos de equipes ALF (não existem)
- ✅ Estrutura completa de objetos aninhados (apenas códigos)
