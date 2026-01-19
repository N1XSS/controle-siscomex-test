# Schema PostgreSQL - Sistema DUE Siscomex

## Visão Geral

Este documento descreve a estrutura completa do banco de dados PostgreSQL para o sistema de controle de DUEs. O banco possui **37 tabelas** organizadas em dois grupos:

- **23 tabelas DUE**: Armazenam dados das Declarações Únicas de Exportação
- **14 tabelas de suporte**: Tabelas auxiliares (países, moedas, portos, etc.)

## Informações de Conexão

```
Host: 31.97.22.234
Porta: 5440
Database: siscomex_export_db
User: gestor_siscomex
```

## Estrutura das Tabelas

### Grupo 1: Tabelas de Suporte (14 tabelas)

#### 1. `suporte_pais`
Tabela de países com códigos ISO e nomes em múltiplos idiomas.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `codigo_numerico` | INTEGER | PK - Código numérico do país |
| `sigla_iso2` | VARCHAR(2) | Sigla ISO 2 letras |
| `sigla_iso3` | VARCHAR(3) | Sigla ISO 3 letras |
| `nome` | VARCHAR(100) | Nome do país |
| `nome_ingles` | VARCHAR(100) | Nome em inglês |
| `nome_frances` | VARCHAR(100) | Nome em francês |
| `data_inicio` | TIMESTAMP | Data de início da vigência |
| `data_fim` | TIMESTAMP | Data de fim da vigência |
| `interno_versao` | INTEGER | Versão interna |

#### 2. `suporte_moeda`
Tabela de moedas com códigos e símbolos.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `codigo` | VARCHAR(10) | PK - Código da moeda |
| `nome` | VARCHAR(100) | Nome da moeda |
| `simbolo` | VARCHAR(10) | Símbolo da moeda |
| `codigo_swift` | VARCHAR(5) | Código SWIFT |
| `sigla_iso2` | VARCHAR(5) | Sigla ISO 2 letras |
| `data_inicio` | TIMESTAMP | Data de início |
| `data_fim` | TIMESTAMP | Data de fim |
| `interno_versao` | INTEGER | Versão interna |

#### 3. `suporte_enquadramento`
Enquadramentos de exportação.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `codigo` | INTEGER | PK - Código do enquadramento |
| `descricao` | VARCHAR(500) | Descrição |
| `codigo_tipo_enquadramento` | VARCHAR(10) | Tipo de enquadramento |
| `codigo_grupo_enquadramento` | VARCHAR(10) | Grupo de enquadramento |
| `data_inicio` | TIMESTAMP | Data de início |
| `data_fim` | TIMESTAMP | Data de fim |
| `interno_versao` | INTEGER | Versão interna |

#### 4. `suporte_fundamento_legal_tt`
Fundamentos legais tributários.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `codigo` | INTEGER | PK - Código |
| `descricao` | VARCHAR(500) | Descrição |
| `codigo_beneficio_fiscal_sisen` | VARCHAR(50) | Código de benefício fiscal |
| `in_permite_registro_pessoa_fisica` | VARCHAR(10) | Permite registro PF |
| `data_inicio` | TIMESTAMP | Data de início |
| `data_fim` | TIMESTAMP | Data de fim |
| `interno_versao` | INTEGER | Versão interna |

#### 5. `suporte_orgao_anuente`
Órgãos anuentes (ANVISA, IBAMA, etc).

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `codigo` | VARCHAR(20) | PK - Código do órgão |
| `sigla` | VARCHAR(20) | Sigla do órgão |
| `descricao` | VARCHAR(200) | Descrição |
| `cnpj` | VARCHAR(20) | CNPJ do órgão |
| `data_inicio` | TIMESTAMP | Data de início |
| `data_fim` | TIMESTAMP | Data de fim |
| `interno_versao` | INTEGER | Versão interna |

#### 6. `suporte_porto`
Portos.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `codigo` | VARCHAR(20) | PK - Código do porto |
| `descricao` | VARCHAR(200) | Descrição |
| `data_inicio` | TIMESTAMP | Data de início |
| `data_fim` | TIMESTAMP | Data de fim |
| `interno_versao` | INTEGER | Versão interna |

#### 7. `suporte_recinto_aduaneiro`
Recintos aduaneiros.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `codigo` | VARCHAR(20) | PK - Código do recinto |
| `nome` | VARCHAR(300) | Nome do recinto |
| `data_inicio` | TIMESTAMP | Data de início |
| `data_fim` | TIMESTAMP | Data de fim |
| `interno_versao` | INTEGER | Versão interna |

#### 8. `suporte_solicitante`
Tipos de solicitantes.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `codigo` | VARCHAR(20) | PK - Código |
| `descricao` | VARCHAR(200) | Descrição |
| `data_inicio` | TIMESTAMP | Data de início |
| `data_fim` | TIMESTAMP | Data de fim |
| `interno_versao` | INTEGER | Versão interna |

#### 9. `suporte_tipo_area_equipamento`
Tipos de área/equipamento.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `codigo` | VARCHAR(10) | PK - Código |
| `descricao` | VARCHAR(200) | Descrição |
| `data_inicio` | TIMESTAMP | Data de início |
| `data_fim` | TIMESTAMP | Data de fim |
| `interno_versao` | INTEGER | Versão interna |

#### 10. `suporte_tipo_conhecimento`
Tipos de conhecimento de transporte.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `codigo` | VARCHAR(20) | PK - Código |
| `descricao` | VARCHAR(200) | Descrição |
| `indicador_tipo_basico` | VARCHAR(5) | Indicador tipo básico |
| `data_inicio` | TIMESTAMP | Data de início |
| `data_fim` | TIMESTAMP | Data de fim |
| `interno_versao` | INTEGER | Versão interna |

#### 11. `suporte_tipo_conteiner`
Tipos de contêiner.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `codigo` | VARCHAR(20) | PK - Código |
| `descricao` | VARCHAR(200) | Descrição |
| `comprimento` | NUMERIC(10,2) | Comprimento |
| `dimensoes` | VARCHAR(100) | Dimensões |
| `codigo_grupo_tipo_conteiner` | VARCHAR(10) | Grupo |
| `data_inicio` | TIMESTAMP | Data de início |
| `data_fim` | TIMESTAMP | Data de fim |
| `interno_versao` | INTEGER | Versão interna |

#### 12. `suporte_tipo_declaracao_aduaneira`
Tipos de declaração aduaneira.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `codigo` | VARCHAR(30) | PK - Código |
| `descricao` | VARCHAR(200) | Descrição |
| `data_inicio` | TIMESTAMP | Data de início |
| `data_fim` | TIMESTAMP | Data de fim |
| `interno_versao` | INTEGER | Versão interna |

#### 13. `suporte_ua_srf`
Unidades Aduaneiras da SRF.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `codigo` | VARCHAR(20) | PK - Código |
| `sigla` | VARCHAR(10) | Sigla |
| `nome` | VARCHAR(100) | Nome |
| `regiao_fiscal` | VARCHAR(10) | Região fiscal |
| `nome_curto` | VARCHAR(100) | Nome curto |
| `data_inicio` | TIMESTAMP | Data de início |
| `data_fim` | TIMESTAMP | Data de fim |
| `interno_versao` | INTEGER | Versão interna |

#### 14. `nfe_sap`
Chaves de Notas Fiscais importadas do SAP.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `chave_nf` | VARCHAR(44) | PK - Chave de acesso da NF (44 dígitos) |
| `data_importacao` | TIMESTAMP | Data/hora da importação (default: CURRENT_TIMESTAMP) |
| `ativo` | BOOLEAN | Indica se a NF está ativa (default: TRUE) |

**Índices:**
- `idx_nfe_sap_data` em `data_importacao`

---

### Grupo 2: Tabelas DUE (22 tabelas)

#### 1. `due_principal`
Tabela principal com dados gerais da DUE.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `numero` | VARCHAR(14) | **PK** - Número da DUE (formato: 25BR0004523642) |
| `chave_de_acesso` | VARCHAR(11) | Chave de acesso |
| `data_de_registro` | TIMESTAMP | Data/hora de registro |
| `bloqueio` | BOOLEAN | DUE bloqueada |
| `canal` | VARCHAR(20) | Canal de conferência (VERDE, LARANJA, VERMELHO) |
| `embarque_em_recinto_alfandegado` | BOOLEAN | Embarque em recinto alfandegado |
| `despacho_em_recinto_alfandegado` | BOOLEAN | Despacho em recinto alfandegado |
| `forma_de_exportacao` | VARCHAR(50) | Forma de exportação |
| `impedido_de_embarque` | BOOLEAN | Impedido de embarque |
| `informacoes_complementares` | TEXT | Informações complementares |
| `ruc` | VARCHAR(35) | Referência Única de Carga |
| `situacao` | VARCHAR(100) | Situação atual |
| `situacao_do_tratamento_administrativo` | VARCHAR(50) | Situação dos tratamentos |
| `tipo` | VARCHAR(50) | Tipo da DUE |
| `tratamento_prioritario` | BOOLEAN | Tratamento prioritário |
| `responsavel_pelo_acd` | VARCHAR(50) | Responsável pelo ACD |
| `despacho_em_recinto_domiciliar` | BOOLEAN | Despacho em recinto domiciliar |
| `data_de_criacao` | TIMESTAMP | Data/hora de criação |
| `data_do_cce` | TIMESTAMP | Data da Carga Completamente Exportada |
| `data_do_desembaraco` | TIMESTAMP | Data do desembaraço |
| `data_do_acd` | TIMESTAMP | Data da Apresentação para Despacho |
| `data_da_averbacao` | TIMESTAMP | Data da averbação |
| `valor_total_mercadoria` | NUMERIC(15,2) | Valor total das mercadorias |
| `inclusao_nota_fiscal` | BOOLEAN | Inclusão de nota fiscal |
| `exigencia_ativa` | BOOLEAN | Exigência ativa |
| `consorciada` | BOOLEAN | Operação consorciada |
| `dat` | BOOLEAN | DAT - Declaração de Armazenamento em Trânsito |
| `oea` | BOOLEAN | Operador Econômico Autorizado |
| `declarante_numero_do_documento` | VARCHAR(20) | Número do documento do declarante |
| `declarante_tipo_do_documento` | VARCHAR(20) | Tipo do documento (CPF/CNPJ) |
| `declarante_nome` | VARCHAR(150) | Nome do declarante |
| `declarante_estrangeiro` | BOOLEAN | Declarante é estrangeiro |
| `declarante_nacionalidade_codigo` | INTEGER | Código da nacionalidade |
| `declarante_nacionalidade_nome` | VARCHAR(50) | Nome da nacionalidade |
| `declarante_nacionalidade_nome_resumido` | VARCHAR(5) | Nome resumido da nacionalidade |
| `moeda_codigo` | INTEGER | Código da moeda |
| `pais_importador_codigo` | INTEGER | Código do país importador |
| `recinto_aduaneiro_de_despacho_codigo` | VARCHAR(7) | Código do recinto de despacho |
| `recinto_aduaneiro_de_embarque_codigo` | VARCHAR(7) | Código do recinto de embarque |
| `unidade_local_de_despacho_codigo` | VARCHAR(7) | Código da unidade local de despacho |
| `unidade_local_de_embarque_codigo` | VARCHAR(7) | Código da unidade local de embarque |
| `declaracao_tributaria_divergente` | BOOLEAN | Divergência na declaração tributária |
| `data_ultima_atualizacao` | TIMESTAMP | Data/hora da última atualização via API |

**Índices:**
- `idx_due_principal_canal` em `canal`
- `idx_due_principal_situacao` em `situacao`
- `idx_due_principal_data_criacao` em `data_de_criacao`
- `idx_due_principal_data_atualizacao` em `data_ultima_atualizacao`

#### 2. `nf_due_vinculo`
Vínculo entre Nota Fiscal e DUE.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `chave_nf` | VARCHAR(44) | **PK** - Chave de acesso da NF (44 dígitos) |
| `numero_due` | VARCHAR(14) | **FK** → `due_principal.numero` - Número da DUE |
| `data_vinculo` | TIMESTAMP | Data/hora de criação do vínculo (default: CURRENT_TIMESTAMP) |
| `origem` | VARCHAR(20) | Origem do vínculo (SISCOMEX, CACHE, etc) |

**Índices:**
- `idx_nf_due_vinculo_numero_due` em `numero_due`

#### 3. `due_eventos_historico`
Histórico de eventos da DUE.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | SERIAL | **PK** - ID único (auto-incremento) |
| `numero_due` | VARCHAR(14) | **FK** → `due_principal.numero` |
| `data_e_hora_do_evento` | TIMESTAMP | Data e hora do evento |
| `evento` | VARCHAR(150) | Descrição do evento |
| `responsavel` | VARCHAR(100) | Responsável pelo evento |
| `informacoes_adicionais` | TEXT | Informações adicionais |
| `detalhes` | VARCHAR(400) | Detalhes do evento |
| `motivo` | VARCHAR(150) | Motivo do evento |
| `tipo_evento` | VARCHAR(50) | Tipo do evento |
| `data` | TIMESTAMP | Data do evento |

**Índices:**
- `idx_due_eventos_numero_due` em `numero_due`
- `idx_due_eventos_data` em `data_e_hora_do_evento`

#### 4. `due_itens`
Itens da DUE.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | VARCHAR(30) | **PK** - ID único (formato: numero_due_numeroItem) |
| `numero_due` | VARCHAR(14) | **FK** → `due_principal.numero` |
| `numero_item` | INTEGER | Número sequencial do item |
| `quantidade_na_unidade_estatistica` | NUMERIC(14,5) | Quantidade na unidade estatística |
| `peso_liquido_total` | NUMERIC(14,5) | Peso líquido total |
| `valor_da_mercadoria_na_condicao_de_venda` | NUMERIC(15,2) | Valor na condição de venda |
| `valor_da_mercadoria_no_local_de_embarque` | NUMERIC(15,2) | Valor no local de embarque |
| `valor_da_mercadoria_no_local_de_embarque_em_reais` | NUMERIC(15,2) | Valor no local de embarque em reais |
| `valor_da_mercadoria_na_condicao_de_venda_em_reais` | NUMERIC(15,2) | Valor na condição de venda em reais |
| `data_de_conversao` | TIMESTAMP | Data de conversão da moeda |
| `descricao_da_mercadoria` | TEXT | Descrição da mercadoria |
| `unidade_comercializada` | VARCHAR(20) | Unidade comercializada |
| `nome_importador` | VARCHAR(60) | Nome do importador |
| `endereco_importador` | VARCHAR(380) | Endereço do importador |
| `valor_total_calculado_item` | NUMERIC(13,2) | Valor total calculado do item |
| `quantidade_na_unidade_comercializada` | NUMERIC(14,5) | Quantidade na unidade comercializada |
| `ncm_codigo` | VARCHAR(8) | Código NCM |
| `ncm_descricao` | VARCHAR(500) | Descrição do NCM |
| `ncm_unidade_medida_estatistica` | VARCHAR(20) | Unidade de medida estatística |
| `exportador_numero_do_documento` | VARCHAR(20) | Número do documento do exportador |
| `exportador_tipo_do_documento` | VARCHAR(20) | Tipo do documento |
| `exportador_nome` | VARCHAR(150) | Nome do exportador |
| `exportador_estrangeiro` | BOOLEAN | Exportador é estrangeiro |
| `exportador_nacionalidade_codigo` | INTEGER | Código da nacionalidade |
| `exportador_nacionalidade_nome` | VARCHAR(50) | Nome da nacionalidade |
| `exportador_nacionalidade_nome_resumido` | VARCHAR(5) | Nome resumido da nacionalidade |
| `codigo_condicao_venda` | VARCHAR(3) | Código da condição de venda (FOB, CIF, etc) |
| `exportacao_temporaria` | BOOLEAN | Exportação temporária |

**Índices:**
- `idx_due_itens_numero_due` em `numero_due`
- `idx_due_itens_ncm` em `ncm_codigo`

#### 5. `due_item_enquadramentos`
Enquadramentos dos itens.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | SERIAL | **PK** - ID único |
| `due_item_id` | VARCHAR(30) | **FK** → `due_itens.id` |
| `numero_due` | VARCHAR(14) | Número da DUE |
| `numero_item` | INTEGER | Número do item |
| `codigo` | INTEGER | Código do enquadramento |
| `data_registro` | TIMESTAMP | Data de registro |
| `descricao` | VARCHAR(500) | Descrição |
| `grupo` | INTEGER | Grupo do enquadramento |
| `tipo` | INTEGER | Tipo do enquadramento |

**Índices:**
- `idx_due_item_enq_numero_due` em `numero_due`
- `idx_due_item_enq_item_id` em `due_item_id`

#### 6. `due_item_paises_destino`
Países de destino dos itens.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | SERIAL | **PK** - ID único |
| `due_item_id` | VARCHAR(30) | **FK** → `due_itens.id` |
| `numero_due` | VARCHAR(14) | Número da DUE |
| `numero_item` | INTEGER | Número do item |
| `codigo_pais_destino` | INTEGER | Código do país de destino |

**Índices:**
- `idx_due_item_paises_numero_due` em `numero_due`

#### 7. `due_item_tratamentos_administrativos`
Tratamentos administrativos dos itens.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | VARCHAR(35) | **PK** - ID único (formato: numero_due_item_indice) |
| `due_item_id` | VARCHAR(30) | **FK** → `due_itens.id` |
| `numero_due` | VARCHAR(14) | Número da DUE |
| `numero_item` | INTEGER | Número do item |
| `mensagem` | TEXT | Mensagem do tratamento |
| `impeditivo_de_embarque` | BOOLEAN | É impeditivo de embarque |
| `codigo_lpco` | VARCHAR(20) | Código LPCO |
| `situacao` | VARCHAR(50) | Situação do tratamento |

**Índices:**
- `idx_due_item_trat_numero_due` em `numero_due`

#### 8. `due_item_tratamentos_administrativos_orgaos`
Órgãos dos tratamentos administrativos.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | SERIAL | **PK** - ID único |
| `tratamento_administrativo_id` | VARCHAR(35) | **FK** → `due_item_tratamentos_administrativos.id` |
| `due_item_id` | VARCHAR(30) | ID do item da DUE |
| `numero_due` | VARCHAR(14) | Número da DUE |
| `codigo_orgao` | VARCHAR(20) | Código do órgão (MAPA, IBAMA, etc) |

**Índices:**
- `idx_due_item_trat_orgaos_numero_due` em `numero_due`

#### 9. `due_item_notas_remessa`
Notas de remessa dos itens.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | SERIAL | **PK** - ID único |
| `due_item_id` | VARCHAR(30) | **FK** → `due_itens.id` |
| `numero_due` | VARCHAR(14) | Número da DUE |
| `numero_item` | INTEGER | Número do item |
| `numero_do_item` | INTEGER | Número do item na nota |
| `chave_de_acesso` | VARCHAR(44) | Chave de acesso da NF |
| `cfop` | INTEGER | Código Fiscal de Operações |
| `codigo_do_produto` | VARCHAR(60) | Código do produto |
| `descricao` | TEXT | Descrição do produto |
| `quantidade_estatistica` | NUMERIC(11,4) | Quantidade estatística |
| `unidade_comercial` | VARCHAR(6) | Unidade comercial |
| `valor_total_bruto` | NUMERIC(13,2) | Valor total bruto |
| `quantidade_consumida` | NUMERIC(14,5) | Quantidade consumida |
| `ncm_codigo` | VARCHAR(8) | Código NCM |
| `ncm_descricao` | VARCHAR(500) | Descrição do NCM |
| `ncm_unidade_medida_estatistica` | VARCHAR(20) | Unidade de medida estatística |
| `modelo` | VARCHAR(2) | Modelo da NF |
| `serie` | INTEGER | Série da NF |
| `numero_do_documento` | INTEGER | Número do documento fiscal |
| `uf_do_emissor` | VARCHAR(2) | UF do emissor |
| `identificacao_emitente` | VARCHAR(20) | Identificação do emitente |
| `apresentada_para_despacho` | BOOLEAN | NF apresentada para despacho |
| `finalidade` | VARCHAR(50) | Finalidade da NF |
| `quantidade_de_itens` | INTEGER | Quantidade de itens na NF |
| `nota_fiscal_eletronica` | BOOLEAN | Indica se é NF-e |
| `emitente_cnpj` | BOOLEAN | Emitente é CNPJ |
| `emitente_cpf` | BOOLEAN | Emitente é CPF |

**Índices:**
- `idx_due_item_notas_rem_numero_due` em `numero_due`
- `idx_due_item_notas_rem_chave` em `chave_de_acesso`

#### 10. `due_item_nota_fiscal_exportacao`
Nota fiscal de exportação do item (1:1 com item).

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `due_item_id` | VARCHAR(30) | **PK/FK** → `due_itens.id` |
| `numero_due` | VARCHAR(14) | Número da DUE |
| `numero_item` | INTEGER | Número do item |
| `numero_do_item` | INTEGER | Número do item na nota |
| `chave_de_acesso` | VARCHAR(44) | Chave de acesso da NF |
| `modelo` | VARCHAR(2) | Modelo da NF |
| `serie` | INTEGER | Série da NF |
| `numero_do_documento` | INTEGER | Número do documento fiscal |
| `uf_do_emissor` | VARCHAR(2) | UF do emissor |
| `identificacao_emitente` | VARCHAR(20) | Identificação do emitente |
| `emitente_cnpj` | BOOLEAN | Emitente é CNPJ |
| `emitente_cpf` | BOOLEAN | Emitente é CPF |
| `finalidade` | VARCHAR(50) | Finalidade da NF |
| `quantidade_de_itens` | INTEGER | Quantidade de itens na NF |
| `nota_fiscal_eletronica` | BOOLEAN | Indica se é NF-e |
| `cfop` | INTEGER | Código Fiscal de Operações |
| `codigo_do_produto` | VARCHAR(60) | Código do produto |
| `descricao` | TEXT | Descrição do produto |
| `quantidade_estatistica` | NUMERIC(11,4) | Quantidade estatística |
| `unidade_comercial` | VARCHAR(6) | Unidade comercial |
| `valor_total_calculado` | NUMERIC(13,2) | Valor total calculado |
| `ncm_codigo` | VARCHAR(8) | Código NCM |
| `ncm_descricao` | VARCHAR(500) | Descrição do NCM |
| `ncm_unidade_medida_estatistica` | VARCHAR(20) | Unidade de medida estatística |
| `apresentada_para_despacho` | BOOLEAN | NF apresentada para despacho |

**Índices:**
- `idx_due_item_nf_exp_numero_due` em `numero_due`
- `idx_due_item_nf_exp_chave` em `chave_de_acesso`

#### 11. `due_item_notas_complementares`
Notas complementares dos itens.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | SERIAL | **PK** - ID único |
| `due_item_id` | VARCHAR(30) | **FK** → `due_itens.id` |
| `numero_due` | VARCHAR(14) | Número da DUE |
| `numero_item` | INTEGER | Número do item |
| `indice` | INTEGER | Índice da nota complementar |
| `numero_do_item` | INTEGER | Número do item na nota |
| `chave_de_acesso` | VARCHAR(44) | Chave de acesso da NF |
| `modelo` | VARCHAR(2) | Modelo da NF |
| `serie` | INTEGER | Série da NF |
| `numero_do_documento` | INTEGER | Número do documento fiscal |
| `uf_do_emissor` | VARCHAR(2) | UF do emissor |
| `identificacao_emitente` | VARCHAR(20) | Identificação do emitente |
| `cfop` | INTEGER | Código Fiscal de Operações |
| `codigo_do_produto` | VARCHAR(60) | Código do produto |
| `descricao` | TEXT | Descrição do produto |
| `quantidade_estatistica` | NUMERIC(11,4) | Quantidade estatística |
| `unidade_comercial` | VARCHAR(6) | Unidade comercial |
| `valor_total_bruto` | NUMERIC(13,2) | Valor total bruto |
| `ncm_codigo` | VARCHAR(8) | Código NCM |

**Índices:**
- `idx_due_item_notas_comp_numero_due` em `numero_due`

#### 12. `due_item_atributos`
Atributos dos itens.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | SERIAL | **PK** - ID único |
| `due_item_id` | VARCHAR(30) | **FK** → `due_itens.id` |
| `numero_due` | VARCHAR(14) | Número da DUE |
| `numero_item` | INTEGER | Número do item |
| `indice` | INTEGER | Índice do atributo |
| `codigo` | VARCHAR(20) | Código do atributo |
| `valor` | VARCHAR(500) | Valor do atributo |
| `descricao` | VARCHAR(200) | Descrição do atributo |

**Índices:**
- `idx_due_item_atrib_numero_due` em `numero_due`

#### 13. `due_item_documentos_importacao`
Documentos de importação dos itens.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | SERIAL | **PK** - ID único |
| `due_item_id` | VARCHAR(30) | **FK** → `due_itens.id` |
| `numero_due` | VARCHAR(14) | Número da DUE |
| `numero_item` | INTEGER | Número do item |
| `indice` | INTEGER | Índice do documento |
| `tipo` | VARCHAR(30) | Tipo do documento |
| `numero` | VARCHAR(50) | Número do documento |
| `data_registro` | TIMESTAMP | Data de registro |
| `item_documento` | INTEGER | Item do documento |
| `quantidade_utilizada` | NUMERIC(14,5) | Quantidade utilizada |

**Índices:**
- `idx_due_item_docs_imp_numero_due` em `numero_due`

#### 14. `due_item_documentos_transformacao`
Documentos de transformação dos itens.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | SERIAL | **PK** - ID único |
| `due_item_id` | VARCHAR(30) | **FK** → `due_itens.id` |
| `numero_due` | VARCHAR(14) | Número da DUE |
| `numero_item` | INTEGER | Número do item |
| `indice` | INTEGER | Índice do documento |
| `tipo` | VARCHAR(30) | Tipo do documento |
| `numero` | VARCHAR(50) | Número do documento |
| `data_registro` | TIMESTAMP | Data de registro |

**Índices:**
- `idx_due_item_docs_transf_numero_due` em `numero_due`

#### 15. `due_item_calculo_tributario_tratamentos`
Tratamentos tributários dos itens.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | SERIAL | **PK** - ID único |
| `due_item_id` | VARCHAR(30) | **FK** → `due_itens.id` |
| `numero_due` | VARCHAR(14) | Número da DUE |
| `numero_item` | INTEGER | Número do item |
| `indice` | INTEGER | Índice do tratamento |
| `codigo` | VARCHAR(20) | Código do tratamento |
| `descricao` | VARCHAR(200) | Descrição do tratamento |
| `tipo` | VARCHAR(50) | Tipo do tratamento |
| `tributo` | VARCHAR(20) | Tributo relacionado |

**Índices:**
- `idx_due_item_calc_trat_numero_due` em `numero_due`

#### 16. `due_item_calculo_tributario_quadros`
Quadros de cálculo tributário dos itens.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | SERIAL | **PK** - ID único |
| `due_item_id` | VARCHAR(30) | **FK** → `due_itens.id` |
| `numero_due` | VARCHAR(14) | Número da DUE |
| `numero_item` | INTEGER | Número do item |
| `indice` | INTEGER | Índice do quadro |
| `tributo` | VARCHAR(20) | Tributo |
| `base_de_calculo` | NUMERIC(15,2) | Base de cálculo |
| `aliquota` | NUMERIC(7,4) | Alíquota |
| `valor_devido` | NUMERIC(15,2) | Valor devido |
| `valor_recolhido` | NUMERIC(15,2) | Valor recolhido |
| `valor_compensado` | NUMERIC(15,2) | Valor compensado |

**Índices:**
- `idx_due_item_calc_quadros_numero_due` em `numero_due`

#### 17. `due_situacoes_carga`
Situações da carga.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | SERIAL | **PK** - ID único |
| `numero_due` | VARCHAR(14) | **FK** → `due_principal.numero` |
| `sequencial` | INTEGER | Sequencial |
| `codigo` | INTEGER | Código da situação |
| `descricao` | VARCHAR(50) | Descrição da situação |
| `carga_operada` | BOOLEAN | Carga foi operada |

**Índices:**
- `idx_due_sit_carga_numero_due` em `numero_due`

#### 18. `due_solicitacoes`
Solicitações da DUE.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | SERIAL | **PK** - ID único |
| `numero_due` | VARCHAR(14) | **FK** → `due_principal.numero` |
| `tipo_solicitacao` | VARCHAR(50) | Tipo da solicitação |
| `data_da_solicitacao` | TIMESTAMP | Data da solicitação |
| `usuario_responsavel` | VARCHAR(20) | Usuário responsável |
| `codigo_do_status_da_solicitacao` | INTEGER | Código do status |
| `status_da_solicitacao` | VARCHAR(100) | Status da solicitação |
| `data_de_apreciacao` | TIMESTAMP | Data de apreciação |
| `motivo` | VARCHAR(600) | Motivo da solicitação |

**Índices:**
- `idx_due_solic_numero_due` em `numero_due`

#### 19. `due_declaracao_tributaria_compensacoes`
Compensações tributárias.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | SERIAL | **PK** - ID único |
| `numero_due` | VARCHAR(14) | **FK** → `due_principal.numero` |
| `codigo_receita` | VARCHAR(20) | Código da receita |
| `data_do_registro` | TIMESTAMP | Data do registro |
| `numero_da_declaracao` | VARCHAR(24) | Número da declaração |
| `valor_compensado` | NUMERIC(15,2) | Valor compensado |

**Índices:**
- `idx_due_decl_comp_numero_due` em `numero_due`

#### 20. `due_declaracao_tributaria_recolhimentos`
Recolhimentos tributários.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | SERIAL | **PK** - ID único |
| `numero_due` | VARCHAR(14) | **FK** → `due_principal.numero` |
| `codigo_receita` | VARCHAR(20) | Código da receita |
| `data_do_pagamento` | TIMESTAMP | Data do pagamento |
| `data_do_registro` | TIMESTAMP | Data do registro |
| `valor_da_multa` | NUMERIC(15,2) | Valor da multa |
| `valor_do_imposto_recolhido` | NUMERIC(15,2) | Valor do imposto recolhido |
| `valor_dos_juros_mora` | NUMERIC(15,2) | Valor dos juros de mora |

**Índices:**
- `idx_due_decl_recol_numero_due` em `numero_due`

#### 21. `due_declaracao_tributaria_contestacoes`
Contestações tributárias.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | SERIAL | **PK** - ID único |
| `numero_due` | VARCHAR(14) | **FK** → `due_principal.numero` |
| `indice` | INTEGER | Índice da contestação |
| `data_do_registro` | TIMESTAMP | Data do registro |
| `motivo` | VARCHAR(600) | Motivo da contestação |
| `status` | VARCHAR(50) | Status da contestação |
| `data_de_apreciacao` | TIMESTAMP | Data de apreciação |
| `observacao` | TEXT | Observação |

**Índices:**
- `idx_due_decl_cont_numero_due` em `numero_due`

#### 22. `due_atos_concessorios_suspensao`
Atos concessórios de suspensão.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | SERIAL | **PK** - ID único |
| `numero_due` | VARCHAR(14) | **FK** → `due_principal.numero` |
| `ato_numero` | VARCHAR(20) | Número do ato concessório |
| `tipo_codigo` | INTEGER | Código do tipo |
| `tipo_descricao` | VARCHAR(100) | Descrição do tipo |
| `item_numero` | VARCHAR(10) | Número do item |
| `item_ncm` | VARCHAR(8) | NCM do item |
| `beneficiario_cnpj` | VARCHAR(14) | CNPJ do beneficiário |
| `quantidade_exportada` | NUMERIC(14,5) | Quantidade exportada |
| `valor_com_cobertura_cambial` | NUMERIC(15,2) | Valor com cobertura cambial |
| `valor_sem_cobertura_cambial` | NUMERIC(15,2) | Valor sem cobertura cambial |
| `item_de_due_numero` | VARCHAR(10) | Número do item na DUE |

**Índices:**
- `idx_due_atos_conc_numero_due` em `numero_due`

#### 23. `due_atos_concessorios_isencao`
Atos concessórios de isenção (drawback isenção).

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | SERIAL | **PK** - ID único |
| `numero_due` | VARCHAR(14) | **FK** → `due_principal.numero` |
| `ato_numero` | VARCHAR(20) | Número do ato concessório |
| `tipo_codigo` | INTEGER | Código do tipo |
| `tipo_descricao` | VARCHAR(100) | Descrição do tipo |
| `item_numero` | VARCHAR(10) | Número do item |
| `item_ncm` | VARCHAR(8) | NCM do item |
| `beneficiario_cnpj` | VARCHAR(14) | CNPJ do beneficiário |
| `quantidade_exportada` | NUMERIC(14,5) | Quantidade exportada |
| `valor_com_cobertura_cambial` | NUMERIC(15,2) | Valor com cobertura cambial |
| `valor_sem_cobertura_cambial` | NUMERIC(15,2) | Valor sem cobertura cambial |
| `item_de_due_numero` | VARCHAR(10) | Número do item na DUE |

**Índices:**
- `idx_due_atos_isencao_numero_due` em `numero_due`

#### 24. `due_exigencias_fiscais`
Exigências fiscais estruturadas.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | SERIAL | **PK** - ID único |
| `numero_due` | VARCHAR(14) | **FK** → `due_principal.numero` |
| `numero_exigencia` | VARCHAR(20) | Número da exigência |
| `tipo_exigencia` | VARCHAR(50) | Tipo da exigência |
| `data_criacao` | TIMESTAMP | Data de criação |
| `data_limite` | TIMESTAMP | Data limite |
| `status` | VARCHAR(50) | Status da exigência |
| `orgao_responsavel` | VARCHAR(100) | Órgão responsável |
| `descricao` | TEXT | Descrição da exigência |
| `valor_exigido` | NUMERIC(15,2) | Valor exigido |
| `valor_pago` | NUMERIC(15,2) | Valor pago |
| `observacoes` | TEXT | Observações |

**Índices:**
- `idx_due_exigencias_numero_due` em `numero_due`
- `idx_due_exigencias_status` em `status`

---

## Diagrama de Relacionamentos

```
due_principal (1) ──┬── (N) due_eventos_historico
                    ├── (N) due_itens ──┬── (N) due_item_enquadramentos
                    │                   ├── (N) due_item_paises_destino  
                    │                   ├── (N) due_item_tratamentos_administrativos ── (N) due_item_tratamentos_administrativos_orgaos
                    │                   ├── (N) due_item_notas_remessa
                    │                   ├── (1) due_item_nota_fiscal_exportacao
                    │                   ├── (N) due_item_notas_complementares
                    │                   ├── (N) due_item_atributos
                    │                   ├── (N) due_item_documentos_importacao
                    │                   ├── (N) due_item_documentos_transformacao
                    │                   ├── (N) due_item_calculo_tributario_tratamentos
                    │                   └── (N) due_item_calculo_tributario_quadros
                    ├── (N) due_situacoes_carga
                    ├── (N) due_solicitacoes
                    ├── (N) due_declaracao_tributaria_compensacoes
                    ├── (N) due_declaracao_tributaria_recolhimentos
                    ├── (N) due_declaracao_tributaria_contestacoes
                    ├── (N) due_atos_concessorios_suspensao
                    ├── (N) due_atos_concessorios_isencao
                    └── (N) due_exigencias_fiscais

nf_due_vinculo (N) ── (1) due_principal
nfe_sap (N) ── (N) nf_due_vinculo
```

---

## Scripts de Criação

### Criação Manual das Tabelas

Para criar as tabelas manualmente, execute:

```python
from src.database.manager import db_manager

if db_manager.conectar():
    db_manager.criar_tabelas(drop_existing=False)  # False para não dropar existentes
    db_manager.desconectar()
```

Ou use o arquivo `src/database/schema.py` diretamente para obter os DDLs SQL.

### Migração de Tabelas de Suporte

Para migrar as tabelas de suporte dos CSVs:

```bash
python db_migrate_support.py
```

---

## Notas para Migração

### Para Migrar para Outro Banco de Dados:

1. **Extrair DDLs**: Use `src/database/schema.py` que contém todos os CREATE TABLE statements
2. **Adaptar Tipos**: 
   - PostgreSQL `SERIAL` → `AUTO_INCREMENT` (MySQL) ou `IDENTITY` (SQL Server)
   - PostgreSQL `VARCHAR(n)` → `NVARCHAR(n)` (SQL Server com Unicode)
   - PostgreSQL `NUMERIC(p,s)` → `DECIMAL(p,s)` (padrão)
   - PostgreSQL `BOOLEAN` → `BIT` (SQL Server) ou `TINYINT(1)` (MySQL)
   - PostgreSQL `TEXT` → `TEXT` ou `VARCHAR(MAX)` (SQL Server)
   - PostgreSQL `TIMESTAMP` → `DATETIME` ou `TIMESTAMP` (depende do banco)

3. **Índices**: Todos os índices estão definidos nos CREATE TABLE statements
4. **Chaves Estrangeiras**: As FKs estão implícitas nas descrições, mas não foram criadas explicitamente no schema atual (podem ser adicionadas se necessário)

### Exportação de Dados

Para exportar dados para migração:

```sql
-- Exemplo PostgreSQL para CSV
COPY (SELECT * FROM due_principal) TO '/tmp/due_principal.csv' WITH CSV HEADER;
```

Ou use ferramentas como `pg_dump` para backup completo.

---

## Manutenção

- **Backup**: Execute backups regulares das tabelas principais
- **Índices**: Os índices foram criados para otimizar consultas por `numero_due`, `chave_nf`, `canal`, `situacao`
- **Particionamento**: Considere particionar `due_eventos_historico` por data se o volume crescer muito
- **Arquivo**: Considere arquivar DUEs antigas (> 2 anos) em tabelas separadas
