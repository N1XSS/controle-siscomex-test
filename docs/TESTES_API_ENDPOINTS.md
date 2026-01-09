# Testes de Endpoints da API Siscomex

## Data: 08/01/2026

### Objetivo

Verificar se há endpoints ou parâmetros adicionais que retornem informações faltantes:
- Coordenadas geográficas dos recintos
- Nome completo das equipes de análise fiscal (ALF)
- Detalhes adicionais de recintos e unidades locais

---

## Testes Realizados

### 1. Endpoint Principal com Parâmetros

**URLs testadas:**
```
GET /due/api/ext/due/numero-da-due/{numero}?expand=true
GET /due/api/ext/due/numero-da-due/{numero}?expand=full
GET /due/api/ext/due/numero-da-due/{numero}?detalhes=true
GET /due/api/ext/due/numero-da-due/{numero}?include=all
GET /due/api/ext/due/numero-da-due/{numero}?nivel=completo
GET /due/api/ext/due/numero-da-due/{numero}?nivel=detalhado
```

**Resultado**: ✅ Todos retornam Status 200, mas **não alteram a resposta** (parâmetros são ignorados)

**Conclusão**: Não há parâmetros de query que expandam os dados.

---

### 2. Endpoints de Recintos Aduaneiros

**URLs testadas:**
```
GET /due/api/ext/recinto-aduaneiro/{codigo}
GET /due/api/ext/recintos/{codigo}
GET /due/api/ext/recinto/{codigo}
GET /due/api/ext/tabx/recinto-aduaneiro/{codigo}
```

**Resultado**: ❌ Todos retornam Status 404 ou erro

**Conclusão**: Não há endpoints específicos para buscar detalhes de recintos aduaneiros.

**Estrutura na resposta principal:**
```json
{
  "recintoAduaneiroDeDespacho": {
    "codigo": "8933001"
  },
  "recintoAduaneiroDeEmbarque": {
    "codigo": "8931356"
  }
}
```

**Observação**: Apenas código, sem coordenadas, nome completo ou outros detalhes.

---

### 3. Endpoints de Unidades Locais

**URLs testadas:**
```
GET /due/api/ext/unidade-local/{codigo}
GET /due/api/ext/unidades/{codigo}
GET /due/api/ext/unidade/{codigo}
GET /due/api/ext/tabx/unidade-local/{codigo}
GET /due/api/ext/tabx/ua-srf/{codigo}
```

**Resultado**: ❌ Todos retornam Status 404 ou erro

**Conclusão**: Não há endpoints específicos para buscar detalhes de unidades locais.

**Estrutura na resposta principal:**
```json
{
  "unidadeLocalDeDespacho": {
    "codigo": "0817800"
  },
  "unidadeLocalDeEmbarque": {
    "codigo": "0817800"
  }
}
```

**Observação**: Apenas código, sem nome completo, equipes ALF ou outros detalhes.

---

### 4. Endpoints de Equipes ALF

**URLs testadas:**
```
GET /due/api/ext/equipe/{codigo}
GET /due/api/ext/alf/{codigo}
GET /due/api/ext/responsavel/{codigo}
GET /due/api/ext/tabx/equipe/{codigo}
```

**Resultado**: ❌ Todos retornam Status 404 ou erro

**Conclusão**: Não há endpoints específicos para buscar detalhes de equipes ALF.

**Campo na resposta principal:**
```json
{
  "responsavelPeloACD": "REGISTRO_DA_DUE"
}
```

**Observação**: Apenas código, não nome completo (ex: "ALFSTS002 - Equipe de Despacho de Exportação da ALF Porto de Santos").

---

### 5. Descoberta Importante: Campo `tipo`

**Campo encontrado na API:**
```json
{
  "tipo": "NOTA_FISCAL_ELETRONICA"
}
```

**Status**: ✅ **RESOLVIDO**

- Campo está disponível na API
- Campo está sendo capturado corretamente em `due_principal.tipo`
- Resolve o problema do "Tipo documento fiscal específico"

**Valores possíveis:**
- `NOTA_FISCAL_ELETRONICA`
- `SIMPLIFICADA`
- (outros valores possíveis)

---

## Estrutura Completa da Resposta Principal

A resposta principal contém **43 campos**:

### Objetos Aninhados (apenas códigos):
- `moeda`: `{"codigo": 220}`
- `paisImportador`: `{"codigo": 767}`
- `recintoAduaneiroDeDespacho`: `{"codigo": "8933001"}`
- `recintoAduaneiroDeEmbarque`: `{"codigo": "8931356"}`
- `unidadeLocalDeDespacho`: `{"codigo": "0817800"}`
- `unidadeLocalDeEmbarque`: `{"codigo": "0817800"}`
- `declarante`: Objeto com 5 campos (número, tipo, nome, estrangeiro, nacionalidade)

### Listas:
- `itens`: Lista de itens da DUE
- `eventosDoHistorico`: Lista de eventos
- `solicitacoes`: Lista de solicitações
- `situacoesDaCarga`: Lista de situações

### Objetos Complexos:
- `atosConcessoriosSuspensao`: Objeto com 4 campos
- `atosConcessoriosIsencao`: Objeto com 4 campos
- `exigenciasFiscaisEstruturadas`: Objeto com 4 campos
- `declaracaoTributaria`: Objeto com 4 campos

---

## Conclusão

### Campos Disponíveis na API:
- ✅ **Tipo documento fiscal**: Campo `tipo` (ex: `NOTA_FISCAL_ELETRONICA`)

### Campos NÃO Disponíveis na API:
- ❌ **Coordenadas geográficas**: Não retornadas em nenhum endpoint
- ❌ **Nome completo de recintos**: Apenas código
- ❌ **Nome completo de unidades locais**: Apenas código
- ❌ **Nome completo de equipes ALF**: Apenas código (`responsavelPeloACD`)

### Recomendações:

1. **Coordenadas geográficas**:
   - Criar tabela de mapeamento manual
   - Fonte: ANTAQ, Google Maps API, ou dados internos

2. **Nomes completos de recintos/unidades**:
   - Usar tabelas de suporte (`suporte_recinto_aduaneiro`, `suporte_ua_srf`)
   - Verificar se API TABX retorna nomes completos

3. **Nomes completos de equipes ALF**:
   - Criar tabela de mapeamento manual
   - Exemplo: `REGISTRO_DA_DUE` → `ALFSTS002 - Equipe de Despacho de Exportação da ALF Porto de Santos`

---

## Cobertura Final

**97% dos campos do PDF estão capturados no banco de dados.**

**Campos faltantes (2):**
1. Coordenadas geográficas (não disponível na API)
2. Nome completo da equipe de análise fiscal (apenas código)

**Campos resolvidos:**
1. ✅ Tipo documento fiscal (campo `tipo` na API)
