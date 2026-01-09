# Estrutura das Tabelas CSV - Sistema DUE Normalizado

## Visão Geral da Arquitetura

O sistema foi projetado para normalizar os dados JSON complexos da DUE (Declaração Única de Exportação) em 22 tabelas relacionais (21 de dados + 1 de vínculo NF->DUE), seguindo princípios de normalização de banco de dados para evitar redundância e facilitar análises.

## Fluxo de Dados

```
Chave NF → API Siscomex (2 requisições) → JSON DUE Completo → Processamento → 21 CSVs Normalizados
```

---

## 1. TABELA PRINCIPAL: due_principal.csv

**Relacionamento**: 1:1 com DUE  
**Chave Primária**: `numero`  
**Fonte**: Campos diretos do JSON raiz

| Coluna | Tipo | Tamanho | Nulo | Descrição |
|--------|------|---------|------|-----------|
| numero | STRING | 14 | NOT NULL | Número da DUE (formato: 25BR0004523642) |
| chaveDeAcesso | STRING | 11 | NULL | Chave de acesso da DUE |
| dataDeRegistro | DATETIME | - | NULL | Data/hora de registro da DUE |
| bloqueio | BOOLEAN | - | NULL | Indica se DUE está bloqueada |
| canal | STRING | 20 | NULL | Canal de conferência (VERDE, LARANJA, VERMELHO) |
| embarqueEmRecintoAlfandegado | BOOLEAN | - | NULL | Embarque em recinto alfandegado |
| despachoEmRecintoAlfandegado | BOOLEAN | - | NULL | Despacho em recinto alfandegado |
| formaDeExportacao | STRING | 50 | NULL | Forma de exportação |
| impedidoDeEmbarque | BOOLEAN | - | NULL | Indica se está impedido de embarque |
| informacoesComplementares | STRING | 2000 | NULL | Informações complementares |
| ruc | STRING | 35 | NULL | Referência Única de Carga |
| situacao | STRING | 100 | NULL | Situação atual da DUE |
| situacaoDoTratamentoAdministrativo | STRING | 50 | NULL | Situação dos tratamentos administrativos |
| tipo | STRING | 50 | NULL | Tipo da DUE |
| tratamentoPrioritario | BOOLEAN | - | NULL | Indica tratamento prioritário |
| responsavelPeloACD | STRING | 50 | NULL | Responsável pelo ACD |
| despachoEmRecintoDomiciliar | BOOLEAN | - | NULL | Despacho em recinto domiciliar |
| dataDeCriacao | DATETIME | - | NULL | Data/hora de criação |
| dataDoCCE | DATETIME | - | NULL | Data da Carga Completamente Exportada |
| dataDoDesembaraco | DATETIME | - | NULL | Data do desembaraço |
| dataDoAcd | DATETIME | - | NULL | Data da Apresentação para Despacho |
| dataDaAverbacao | DATETIME | - | NULL | Data da averbação |
| valorTotalMercadoria | DECIMAL | 15,2 | NULL | Valor total das mercadorias |
| inclusaoNotaFiscal | BOOLEAN | - | NULL | Inclusão de nota fiscal |
| exigenciaAtiva | BOOLEAN | - | NULL | Indica se há exigência ativa |
| consorciada | BOOLEAN | - | NULL | Operação consorciada |
| dat | BOOLEAN | - | NULL | DAT - Declaração de Armazenamento em Trânsito |
| oea | BOOLEAN | - | NULL | Operador Econômico Autorizado |
| declarante_numeroDoDocumento | STRING | 20 | NULL | Número do documento do declarante |
| declarante_tipoDoDocumento | STRING | 20 | NULL | Tipo do documento (CPF/CNPJ) |
| declarante_nome | STRING | 150 | NULL | Nome do declarante |
| declarante_estrangeiro | BOOLEAN | - | NULL | Declarante é estrangeiro |
| declarante_nacionalidade_codigo | INTEGER | - | NULL | Código da nacionalidade do declarante |
| declarante_nacionalidade_nome | STRING | 50 | NULL | Nome da nacionalidade do declarante |
| declarante_nacionalidade_nomeResumido | STRING | 5 | NULL | Nome resumido da nacionalidade |
| moeda_codigo | INTEGER | - | NULL | Código da moeda |
| paisImportador_codigo | INTEGER | - | NULL | Código do país importador |
| recintoAduaneiroDeDespacho_codigo | STRING | 7 | NULL | Código do recinto de despacho |
| recintoAduaneiroDeEmbarque_codigo | STRING | 7 | NULL | Código do recinto de embarque |
| unidadeLocalDeDespacho_codigo | STRING | 7 | NULL | Código da unidade local de despacho |
| unidadeLocalDeEmbarque_codigo | STRING | 7 | NULL | Código da unidade local de embarque |
| declaracaoTributaria_divergente | BOOLEAN | - | NULL | Indica se há divergência na declaração tributária |
| data_ultima_atualizacao | DATETIME | - | NULL | Data/hora da última atualização via API |

---

## 2. TABELA DE VÍNCULO NF->DUE: nf_due_vinculo.csv

**Relacionamento**: Cache de vínculo entre NF e DUE  
**Chave Primária**: `chave_nf`  
**Fonte**: Gerado pelos serviços de sincronização  
**Localização**: `dados/nf_due_vinculo.csv`

| Coluna | Tipo | Tamanho | Nulo | Descrição |
|--------|------|---------|------|-----------|
| chave_nf | STRING | 44 | NOT NULL | Chave de acesso da NF (44 dígitos) |
| numero_due | STRING | 14 | NOT NULL | Número da DUE vinculada |
| data_vinculo | DATETIME | - | NOT NULL | Data/hora de criação do vínculo |
| origem | STRING | 20 | NOT NULL | Origem do vínculo (SISCOMEX/CACHE) |

**Uso**: Esta tabela é usada como cache para evitar consultas desnecessárias ao Siscomex. Antes de consultar a API, o sistema verifica se a NF já possui DUE vinculada.

---

## 3. HISTÓRICO E EVENTOS: due_eventos_historico.csv

**Relacionamento**: 1:N com DUE  
**Chave Estrangeira**: `numero_due` → `due_principal.numero`  
**Fonte**: `eventosDoHistorico[]`

| Coluna | Tipo | Tamanho | Nulo | Descrição |
|--------|------|---------|------|-----------|
| id | INTEGER | - | NOT NULL | ID único do evento (auto-incremento) |
| numero_due | STRING | 14 | NOT NULL | Número da DUE (FK) |
| dataEHoraDoEvento | DATETIME | - | NULL | Data e hora do evento |
| evento | STRING | 150 | NULL | Descrição do evento |
| responsavel | STRING | 100 | NULL | Responsável pelo evento |
| informacoesAdicionais | STRING | 4000 | NULL | Informações adicionais |
| detalhes | STRING | 400 | NULL | Detalhes do evento |
| motivo | STRING | 150 | NULL | Motivo do evento |

---

## 4. ITENS DA DUE: due_itens.csv

**Relacionamento**: 1:N com DUE  
**Chave Primária**: `id`  
**Chave Estrangeira**: `numero_due` → `due_principal.numero`  
**Fonte**: `itens[]`

| Coluna | Tipo | Tamanho | Nulo | Descrição |
|--------|------|---------|------|-----------|
| id | STRING | 20 | NOT NULL | ID único do item (formato: 25BR0004523642_1) |
| numero_due | STRING | 14 | NOT NULL | Número da DUE (FK) |
| numero | INTEGER | - | NOT NULL | Número sequencial do item |
| quantidadeNaUnidadeEstatistica | DECIMAL | 14,5 | NULL | Quantidade na unidade estatística |
| pesoLiquidoTotal | DECIMAL | 14,5 | NULL | Peso líquido total |
| valorDaMercadoriaNaCondicaoDeVenda | DECIMAL | 15,2 | NULL | Valor na condição de venda |
| valorDaMercadoriaNoLocalDeEmbarque | DECIMAL | 15,2 | NULL | Valor no local de embarque |
| valorDaMercadoriaNoLocalDeEmbarqueEmReais | DECIMAL | 15,2 | NULL | Valor no local de embarque em reais |
| valorDaMercadoriaNaCondicaoDeVendaEmReais | DECIMAL | 15,2 | NULL | Valor na condição de venda em reais |
| dataDeConversao | DATETIME | - | NULL | Data de conversão da moeda |
| descricaoDaMercadoria | STRING | 2000 | NULL | Descrição da mercadoria |
| unidadeComercializada | STRING | 20 | NULL | Unidade comercializada |
| nomeImportador | STRING | 60 | NULL | Nome do importador |
| enderecoImportador | STRING | 380 | NULL | Endereço do importador |
| valorTotalCalculadoItem | DECIMAL | 13,2 | NULL | Valor total calculado do item |
| quantidadeNaUnidadeComercializada | DECIMAL | 14,5 | NULL | Quantidade na unidade comercializada |
| ncm_codigo | STRING | 8 | NULL | Código NCM |
| ncm_descricao | STRING | 50 | NULL | Descrição do NCM |
| ncm_unidadeMedidaEstatistica | STRING | 20 | NULL | Unidade de medida estatística |
| exportador_numeroDoDocumento | STRING | 20 | NULL | Número do documento do exportador |
| exportador_tipoDoDocumento | STRING | 20 | NULL | Tipo do documento do exportador |
| exportador_nome | STRING | 150 | NULL | Nome do exportador |
| exportador_estrangeiro | BOOLEAN | - | NULL | Exportador é estrangeiro |
| exportador_nacionalidade_codigo | INTEGER | - | NULL | Código da nacionalidade do exportador |
| exportador_nacionalidade_nome | STRING | 50 | NULL | Nome da nacionalidade do exportador |
| exportador_nacionalidade_nomeResumido | STRING | 5 | NULL | Nome resumido da nacionalidade |
| codigoCondicaoVenda | STRING | 3 | NULL | Código da condição de venda (FOB, CIF, etc.) |
| exportacaoTemporaria | BOOLEAN | - | NULL | Indica se é exportação temporária |

---

## 5. ENQUADRAMENTOS: due_item_enquadramentos.csv

**Relacionamento**: 1:N com Item  
**Chave Estrangeira**: `due_item_id` → `due_itens.id`  
**Fonte**: `itens[].listaDeEnquadramentos[]`

| Coluna | Tipo | Tamanho | Nulo | Descrição |
|--------|------|---------|------|-----------|
| id | INTEGER | - | NOT NULL | ID único do enquadramento (auto-incremento) |
| due_item_id | STRING | 20 | NOT NULL | ID do item da DUE (FK) |
| numero_due | STRING | 14 | NOT NULL | Número da DUE |
| item_numero | INTEGER | - | NOT NULL | Número do item |
| codigo | INTEGER | - | NULL | Código do enquadramento |
| dataRegistro | DATETIME | - | NULL | Data de registro do enquadramento |
| descricao | STRING | 50 | NULL | Descrição do enquadramento |
| grupo | INTEGER | - | NULL | Grupo do enquadramento |
| tipo | INTEGER | - | NULL | Tipo do enquadramento |

---

## 6. PAÍSES DE DESTINO: due_item_paises_destino.csv

**Relacionamento**: 1:N com Item  
**Chave Estrangeira**: `due_item_id` → `due_itens.id`  
**Fonte**: `itens[].listaPaisDestino[]`

| Coluna | Tipo | Tamanho | Nulo | Descrição |
|--------|------|---------|------|-----------|
| id | INTEGER | - | NOT NULL | ID único (auto-incremento) |
| due_item_id | STRING | 20 | NOT NULL | ID do item da DUE (FK) |
| numero_due | STRING | 14 | NOT NULL | Número da DUE |
| item_numero | INTEGER | - | NOT NULL | Número do item |
| codigo_pais | INTEGER | - | NULL | Código do país de destino |

---

## 7. TRATAMENTOS ADMINISTRATIVOS: due_item_tratamentos_administrativos.csv

**Relacionamento**: 1:N com Item  
**Chave Primária**: `id`  
**Chave Estrangeira**: `due_item_id` → `due_itens.id`  
**Fonte**: `itens[].tratamentosAdministrativos[]`

| Coluna | Tipo | Tamanho | Nulo | Descrição |
|--------|------|---------|------|-----------|
| id | STRING | 25 | NOT NULL | ID único (formato: 25BR0004523642_1_0) |
| due_item_id | STRING | 20 | NOT NULL | ID do item da DUE (FK) |
| numero_due | STRING | 14 | NOT NULL | Número da DUE |
| item_numero | INTEGER | - | NOT NULL | Número do item |
| mensagem | STRING | 2000 | NULL | Mensagem do tratamento |
| impeditivoDeEmbarque | BOOLEAN | - | NULL | É impeditivo de embarque |
| codigoLPCO | STRING | 11 | NULL | Código LPCO |
| situacao | STRING | 50 | NULL | Situação do tratamento |

---

## 8. ÓRGÃOS DOS TRATAMENTOS: due_item_tratamentos_administrativos_orgaos.csv

**Relacionamento**: 1:N com Tratamento Administrativo  
**Chave Estrangeira**: `tratamento_administrativo_id` → `due_item_tratamentos_administrativos.id`  
**Fonte**: `itens[].tratamentosAdministrativos[].orgaos[]`

| Coluna | Tipo | Tamanho | Nulo | Descrição |
|--------|------|---------|------|-----------|
| id | INTEGER | - | NOT NULL | ID único (auto-incremento) |
| tratamento_administrativo_id | STRING | 25 | NOT NULL | ID do tratamento (FK) |
| due_item_id | STRING | 20 | NOT NULL | ID do item da DUE |
| numero_due | STRING | 14 | NOT NULL | Número da DUE |
| orgao | STRING | 15 | NULL | Código do órgão (MAPA, IBAMA, etc.) |

---

## 9. NOTAS DE REMESSA: due_item_notas_remessa.csv

**Relacionamento**: 1:N com Item  
**Chave Estrangeira**: `due_item_id` → `due_itens.id`  
**Fonte**: `itens[].itensDaNotaDeRemessa[]`

| Coluna | Tipo | Tamanho | Nulo | Descrição |
|--------|------|---------|------|-----------|
| id | INTEGER | - | NOT NULL | ID único (auto-incremento) |
| due_item_id | STRING | 20 | NOT NULL | ID do item da DUE (FK) |
| numero_due | STRING | 14 | NOT NULL | Número da DUE |
| item_numero | INTEGER | - | NOT NULL | Número do item da DUE |
| numeroDoItem | INTEGER | - | NULL | Número do item na nota |
| chaveDeAcesso | STRING | 44 | NULL | Chave de acesso da NF |
| cfop | INTEGER | - | NULL | Código Fiscal de Operações |
| codigoDoProduto | STRING | 60 | NULL | Código do produto |
| descricao | STRING | 2000 | NULL | Descrição do produto |
| quantidadeEstatistica | DECIMAL | 11,4 | NULL | Quantidade estatística |
| unidadeComercial | STRING | 6 | NULL | Unidade comercial |
| valorTotalBruto | DECIMAL | 13,2 | NULL | Valor total bruto |
| quantidadeConsumida | DECIMAL | 14,5 | NULL | Quantidade consumida |
| ncm_codigo | STRING | 8 | NULL | Código NCM |
| ncm_descricao | STRING | 50 | NULL | Descrição do NCM |
| ncm_unidadeMedidaEstatistica | STRING | 20 | NULL | Unidade de medida estatística |
| modelo | STRING | 2 | NULL | Modelo da NF |
| serie | INTEGER | - | NULL | Série da NF |
| numeroDoDocumento | INTEGER | - | NULL | Número do documento fiscal |
| ufDoEmissor | STRING | 2 | NULL | UF do emissor |
| identificacao_emitente | STRING | 20 | NULL | Identificação do emitente |
| apresentadaParaDespacho | BOOLEAN | - | NULL | NF apresentada para despacho |
| finalidade | STRING | 50 | NULL | Finalidade da NF |
| quantidadeDeItens | INTEGER | - | NULL | Quantidade de itens na NF |
| notaFiscalEletronica | BOOLEAN | - | NULL | Indica se é NF-e |
| emitente_cnpj | BOOLEAN | - | NULL | Emitente é CNPJ |
| emitente_cpf | BOOLEAN | - | NULL | Emitente é CPF |

---

## 10. NOTA FISCAL DE EXPORTAÇÃO: due_item_nota_fiscal_exportacao.csv

**Relacionamento**: 1:1 com Item  
**Chave Estrangeira**: `due_item_id` → `due_itens.id`  
**Fonte**: `itens[].itemDaNotaFiscalDeExportacao`

| Coluna | Tipo | Tamanho | Nulo | Descrição |
|--------|------|---------|------|-----------|
| due_item_id | STRING | 20 | NOT NULL | ID do item da DUE (FK/PK) |
| numero_due | STRING | 14 | NOT NULL | Número da DUE |
| item_numero | INTEGER | - | NOT NULL | Número do item da DUE |
| numeroDoItem | INTEGER | - | NULL | Número do item na nota |
| chaveDeAcesso | STRING | 44 | NULL | Chave de acesso da NF |
| modelo | STRING | 2 | NULL | Modelo da NF |
| serie | INTEGER | - | NULL | Série da NF |
| numeroDoDocumento | INTEGER | - | NULL | Número do documento fiscal |
| ufDoEmissor | STRING | 2 | NULL | UF do emissor |
| identificacao_emitente | STRING | 20 | NULL | Identificação do emitente |
| emitente_cnpj | BOOLEAN | - | NULL | Emitente é CNPJ |
| emitente_cpf | BOOLEAN | - | NULL | Emitente é CPF |
| finalidade | STRING | 50 | NULL | Finalidade da NF |
| quantidadeDeItens | INTEGER | - | NULL | Quantidade de itens na NF |
| notaFiscalEletronica | BOOLEAN | - | NULL | Indica se é NF-e |
| cfop | INTEGER | - | NULL | Código Fiscal de Operações |
| codigoDoProduto | STRING | 60 | NULL | Código do produto |
| descricao | STRING | 2000 | NULL | Descrição do produto |
| quantidadeEstatistica | DECIMAL | 11,4 | NULL | Quantidade estatística |
| unidadeComercial | STRING | 6 | NULL | Unidade comercial |
| valorTotalCalculado | DECIMAL | 13,2 | NULL | Valor total calculado |
| ncm_codigo | STRING | 8 | NULL | Código NCM |
| ncm_descricao | STRING | 50 | NULL | Descrição do NCM |
| ncm_unidadeMedidaEstatistica | STRING | 20 | NULL | Unidade de medida estatística |
| apresentadaParaDespacho | BOOLEAN | - | NULL | NF apresentada para despacho |

---

## 11. NOTAS COMPLEMENTARES: due_item_notas_complementares.csv

**Relacionamento**: 1:N com Item  
**Chave Estrangeira**: `due_item_id` → `due_itens.id`  
**Fonte**: `itens[].itensDeNotaComplementar[]`

| Coluna | Tipo | Tamanho | Nulo | Descrição |
|--------|------|---------|------|-----------|
| due_item_id | STRING | 20 | NOT NULL | ID do item da DUE (FK) |
| numero_due | STRING | 14 | NOT NULL | Número da DUE |
| item_numero | INTEGER | - | NOT NULL | Número do item da DUE |
| indice | INTEGER | - | NOT NULL | Índice da nota complementar |
| numeroDoItem | INTEGER | - | NULL | Número do item na nota |
| chaveDeAcesso | STRING | 44 | NULL | Chave de acesso da NF |
| modelo | STRING | 2 | NULL | Modelo da NF |
| serie | INTEGER | - | NULL | Série da NF |
| numeroDoDocumento | INTEGER | - | NULL | Número do documento fiscal |
| ufDoEmissor | STRING | 2 | NULL | UF do emissor |
| identificacao_emitente | STRING | 20 | NULL | Identificação do emitente |
| cfop | INTEGER | - | NULL | Código Fiscal de Operações |
| codigoDoProduto | STRING | 60 | NULL | Código do produto |
| descricao | STRING | 2000 | NULL | Descrição do produto |
| quantidadeEstatistica | DECIMAL | 11,4 | NULL | Quantidade estatística |
| unidadeComercial | STRING | 6 | NULL | Unidade comercial |
| valorTotalBruto | DECIMAL | 13,2 | NULL | Valor total bruto |
| ncm_codigo | STRING | 8 | NULL | Código NCM |

---

## 12. ATRIBUTOS DO ITEM: due_item_atributos.csv

**Relacionamento**: 1:N com Item  
**Chave Estrangeira**: `due_item_id` → `due_itens.id`  
**Fonte**: `itens[].atributos[]`

| Coluna | Tipo | Tamanho | Nulo | Descrição |
|--------|------|---------|------|-----------|
| due_item_id | STRING | 20 | NOT NULL | ID do item da DUE (FK) |
| numero_due | STRING | 14 | NOT NULL | Número da DUE |
| item_numero | INTEGER | - | NOT NULL | Número do item da DUE |
| indice | INTEGER | - | NOT NULL | Índice do atributo |
| codigo | STRING | 20 | NULL | Código do atributo |
| valor | STRING | 500 | NULL | Valor do atributo |
| descricao | STRING | 200 | NULL | Descrição do atributo |

---

## 13. DOCUMENTOS DE IMPORTAÇÃO: due_item_documentos_importacao.csv

**Relacionamento**: 1:N com Item  
**Chave Estrangeira**: `due_item_id` → `due_itens.id`  
**Fonte**: `itens[].documentosImportacao[]`

| Coluna | Tipo | Tamanho | Nulo | Descrição |
|--------|------|---------|------|-----------|
| due_item_id | STRING | 20 | NOT NULL | ID do item da DUE (FK) |
| numero_due | STRING | 14 | NOT NULL | Número da DUE |
| item_numero | INTEGER | - | NOT NULL | Número do item da DUE |
| indice | INTEGER | - | NOT NULL | Índice do documento |
| tipo | STRING | 30 | NULL | Tipo do documento |
| numero | STRING | 50 | NULL | Número do documento |
| dataRegistro | DATETIME | - | NULL | Data de registro |
| itemDocumento | INTEGER | - | NULL | Item do documento |
| quantidadeUtilizada | DECIMAL | 14,5 | NULL | Quantidade utilizada |

---

## 14. DOCUMENTOS DE TRANSFORMAÇÃO: due_item_documentos_transformacao.csv

**Relacionamento**: 1:N com Item  
**Chave Estrangeira**: `due_item_id` → `due_itens.id`  
**Fonte**: `itens[].documentosDeTransformacao[]`

| Coluna | Tipo | Tamanho | Nulo | Descrição |
|--------|------|---------|------|-----------|
| due_item_id | STRING | 20 | NOT NULL | ID do item da DUE (FK) |
| numero_due | STRING | 14 | NOT NULL | Número da DUE |
| item_numero | INTEGER | - | NOT NULL | Número do item da DUE |
| indice | INTEGER | - | NOT NULL | Índice do documento |
| tipo | STRING | 30 | NULL | Tipo do documento |
| numero | STRING | 50 | NULL | Número do documento |
| dataRegistro | DATETIME | - | NULL | Data de registro |

---

## 15. CÁLCULO TRIBUTÁRIO - TRATAMENTOS: due_item_calculo_tributario_tratamentos.csv

**Relacionamento**: 1:N com Item  
**Chave Estrangeira**: `due_item_id` → `due_itens.id`  
**Fonte**: `itens[].calculoTributario.tratamentosTributarios[]`

| Coluna | Tipo | Tamanho | Nulo | Descrição |
|--------|------|---------|------|-----------|
| due_item_id | STRING | 20 | NOT NULL | ID do item da DUE (FK) |
| numero_due | STRING | 14 | NOT NULL | Número da DUE |
| item_numero | INTEGER | - | NOT NULL | Número do item da DUE |
| indice | INTEGER | - | NOT NULL | Índice do tratamento |
| codigo | STRING | 20 | NULL | Código do tratamento |
| descricao | STRING | 200 | NULL | Descrição do tratamento |
| tipo | STRING | 50 | NULL | Tipo do tratamento |
| tributo | STRING | 20 | NULL | Tributo relacionado |

---

## 16. CÁLCULO TRIBUTÁRIO - QUADROS: due_item_calculo_tributario_quadros.csv

**Relacionamento**: 1:N com Item  
**Chave Estrangeira**: `due_item_id` → `due_itens.id`  
**Fonte**: `itens[].calculoTributario.quadroDeCalculos[]`

| Coluna | Tipo | Tamanho | Nulo | Descrição |
|--------|------|---------|------|-----------|
| due_item_id | STRING | 20 | NOT NULL | ID do item da DUE (FK) |
| numero_due | STRING | 14 | NOT NULL | Número da DUE |
| item_numero | INTEGER | - | NOT NULL | Número do item da DUE |
| indice | INTEGER | - | NOT NULL | Índice do quadro |
| tributo | STRING | 20 | NULL | Tributo |
| baseDeCalculo | DECIMAL | 15,2 | NULL | Base de cálculo |
| aliquota | DECIMAL | 7,4 | NULL | Alíquota |
| valorDevido | DECIMAL | 15,2 | NULL | Valor devido |
| valorRecolhido | DECIMAL | 15,2 | NULL | Valor recolhido |
| valorCompensado | DECIMAL | 15,2 | NULL | Valor compensado |

---

## 17. SITUAÇÕES DA CARGA: due_situacoes_carga.csv

**Relacionamento**: 1:N com DUE  
**Chave Estrangeira**: `numero_due` → `due_principal.numero`  
**Fonte**: `situacoesDaCarga[]`

| Coluna | Tipo | Tamanho | Nulo | Descrição |
|--------|------|---------|------|-----------|
| id | INTEGER | - | NOT NULL | ID único (auto-incremento) |
| numero_due | STRING | 14 | NOT NULL | Número da DUE (FK) |
| codigo | INTEGER | - | NULL | Código da situação |
| descricao | STRING | 50 | NULL | Descrição da situação |
| cargaOperada | BOOLEAN | - | NULL | Carga foi operada |

---

## 18. SOLICITAÇÕES: due_solicitacoes.csv

**Relacionamento**: 1:N com DUE  
**Chave Estrangeira**: `numero_due` → `due_principal.numero`  
**Fonte**: `solicitacoes[]`

| Coluna | Tipo | Tamanho | Nulo | Descrição |
|--------|------|---------|------|-----------|
| id | INTEGER | - | NOT NULL | ID único (auto-incremento) |
| numero_due | STRING | 14 | NOT NULL | Número da DUE (FK) |
| tipoSolicitacao | STRING | 50 | NULL | Tipo da solicitação |
| dataDaSolicitacao | DATETIME | - | NULL | Data da solicitação |
| usuarioResponsavel | STRING | 11 | NULL | Usuário responsável |
| codigoDoStatusDaSolicitacao | INTEGER | - | NULL | Código do status |
| statusDaSolicitacao | STRING | 100 | NULL | Status da solicitação |
| dataDeApreciacao | DATETIME | - | NULL | Data de apreciação |
| motivo | STRING | 600 | NULL | Motivo da solicitação |

---

## 19. COMPENSAÇÕES TRIBUTÁRIAS: due_declaracao_tributaria_compensacoes.csv

**Relacionamento**: 1:N com DUE  
**Chave Estrangeira**: `numero_due` → `due_principal.numero`  
**Fonte**: `declaracaoTributaria.compensacoes[]`

| Coluna | Tipo | Tamanho | Nulo | Descrição |
|--------|------|---------|------|-----------|
| id | INTEGER | - | NOT NULL | ID único (auto-incremento) |
| numero_due | STRING | 14 | NOT NULL | Número da DUE (FK) |
| dataDoRegistro | DATETIME | - | NULL | Data do registro |
| numeroDaDeclaracao | STRING | 24 | NULL | Número da declaração |
| valorCompensado | DECIMAL | 15,2 | NULL | Valor compensado |

---

## 20. RECOLHIMENTOS TRIBUTÁRIOS: due_declaracao_tributaria_recolhimentos.csv

**Relacionamento**: 1:N com DUE  
**Chave Estrangeira**: `numero_due` → `due_principal.numero`  
**Fonte**: `declaracaoTributaria.recolhimentos[]`

| Coluna | Tipo | Tamanho | Nulo | Descrição |
|--------|------|---------|------|-----------|
| id | INTEGER | - | NOT NULL | ID único (auto-incremento) |
| numero_due | STRING | 14 | NOT NULL | Número da DUE (FK) |
| dataDoPagamento | DATETIME | - | NULL | Data do pagamento |
| dataDoRegistro | DATETIME | - | NULL | Data do registro |
| valorDaMulta | DECIMAL | 7,2 | NULL | Valor da multa |
| valorDoImpostoRecolhido | DECIMAL | 15,2 | NULL | Valor do imposto recolhido |
| valorDoJurosMora | DECIMAL | 7,2 | NULL | Valor dos juros de mora |

---

## 21. CONTESTAÇÕES TRIBUTÁRIAS: due_declaracao_tributaria_contestacoes.csv

**Relacionamento**: 1:N com DUE  
**Chave Estrangeira**: `numero_due` → `due_principal.numero`  
**Fonte**: `declaracaoTributaria.contestacoes[]`

| Coluna | Tipo | Tamanho | Nulo | Descrição |
|--------|------|---------|------|-----------|
| id | INTEGER | - | NOT NULL | ID único (auto-incremento) |
| numero_due | STRING | 14 | NOT NULL | Número da DUE (FK) |
| indice | INTEGER | - | NOT NULL | Índice da contestação |
| dataDoRegistro | DATETIME | - | NULL | Data do registro |
| motivo | STRING | 600 | NULL | Motivo da contestação |
| status | STRING | 50 | NULL | Status da contestação |
| dataDeApreciacao | DATETIME | - | NULL | Data de apreciação |
| observacao | STRING | 2000 | NULL | Observação |

---

## 22. ATOS CONCESSÓRIOS DE SUSPENSÃO: due_atos_concessorios_suspensao.csv

**Relacionamento**: 1:N com DUE  
**Chave Estrangeira**: `numero_due` → `due_principal.numero`  
**Fonte**: API adicional de atos concessórios

| Coluna | Tipo | Tamanho | Nulo | Descrição |
|--------|------|---------|------|-----------|
| id | INTEGER | - | NOT NULL | ID único (auto-incremento) |
| numero_due | STRING | 14 | NOT NULL | Número da DUE (FK) |
| ato_numero | STRING | 20 | NULL | Número do ato concessório |
| tipo_codigo | INTEGER | - | NULL | Código do tipo |
| tipo_descricao | STRING | 100 | NULL | Descrição do tipo |
| item_numero | STRING | 10 | NULL | Número do item |
| item_ncm | STRING | 8 | NULL | NCM do item |
| beneficiario_cnpj | STRING | 14 | NULL | CNPJ do beneficiário |
| quantidadeExportada | DECIMAL | 14,5 | NULL | Quantidade exportada |
| valorComCoberturaCambial | DECIMAL | 15,2 | NULL | Valor com cobertura cambial |
| valorSemCoberturaCambial | DECIMAL | 15,2 | NULL | Valor sem cobertura cambial |
| itemDeDUE_numero | STRING | 10 | NULL | Número do item na DUE |

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
                    └── (N) due_atos_concessorios_suspensao
```

---

## Índices Recomendados

### Para Performance em Consultas:
- `due_principal.numero` (PK)
- `due_principal.canal`
- `due_principal.situacao`
- `due_principal.dataDeCriacao`
- `due_itens.numero_due` (FK)
- `due_itens.ncm_codigo`
- `due_eventos_historico.numero_due` (FK)
- `due_eventos_historico.dataEHoraDoEvento`
- `due_item_nota_fiscal_exportacao.chaveDeAcesso`
- `due_item_notas_remessa.chaveDeAcesso`

---

## Considerações Técnicas

### Encoding:
- **CSV**: UTF-8 com BOM (utf-8-sig)
- **Separador**: Ponto e vírgula (;)
- **Decimal**: Ponto como separador

### Tratamento de Nulos:
- **Strings vazias**: Convertidas para NULL
- **Zeros**: Mantidos quando semanticamente válidos
- **Datas inválidas**: Convertidas para NULL

### Validações:
- **Chaves primárias**: Não podem ser NULL ou duplicadas
- **Chaves estrangeiras**: Devem existir na tabela referenciada
- **Tipos numéricos**: Validação de formato e range
- **Datas**: Formato ISO com timezone

### Performance:
- **Estimativa**: ~500 DU-Es = ~60MB total de dados CSV
- **Processamento**: ~2-3 minutos para 500 chaves NF
- **Paralelização**: 10 threads simultâneas
- **Tabelas**: 21 arquivos CSV gerados
