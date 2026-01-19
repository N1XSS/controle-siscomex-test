"""
Schema do banco de dados PostgreSQL para o Sistema DUE - Siscomex
37 tabelas: 23 tabelas DUE + 14 tabelas de suporte

Tabelas DUE:
- due_principal: Dados principais da DUE
- nf_due_vinculo: Vinculo entre NF e DUE
- due_eventos_historico: Historico de eventos
- due_itens: Itens da DUE
- due_item_enquadramentos: Enquadramentos de itens
- due_item_paises_destino: Paises de destino por item
- due_item_tratamentos_administrativos: Tratamentos administrativos
- due_item_tratamentos_administrativos_orgaos: Orgaos dos tratamentos
- due_item_notas_remessa: Notas de remessa
- due_item_nota_fiscal_exportacao: Nota fiscal de exportacao
- due_item_notas_complementares: Notas complementares
- due_item_atributos: Atributos dos itens
- due_item_documentos_importacao: Documentos de importacao
- due_item_documentos_transformacao: Documentos de transformacao
- due_item_calculo_tributario_tratamentos: Tratamentos tributarios
- due_item_calculo_tributario_quadros: Quadros tributarios
- due_situacoes_carga: Situacoes de carga
- due_solicitacoes: Solicitacoes (retificacoes, cancelamentos, etc)
- due_declaracao_tributaria_compensacoes: Compensacoes tributarias
- due_declaracao_tributaria_recolhimentos: Recolhimentos tributarios
- due_declaracao_tributaria_contestacoes: Contestacoes tributarias
- due_atos_concessorios_suspensao: Drawback suspensao
- due_atos_concessorios_isencao: Drawback isencao
- due_exigencias_fiscais: Exigencias fiscais estruturadas

Tabelas Suporte:
- nfe_sap: NFs importadas do SAP
- suporte_pais, suporte_moeda, suporte_enquadramento, etc.
"""

from src.core.logger import logger


# =============================================================================
# TABELAS DE SUPORTE (14 tabelas)
# =============================================================================

CREATE_SUPORTE_PAIS = """
CREATE TABLE IF NOT EXISTS suporte_pais (
    codigo_numerico INTEGER PRIMARY KEY,
    sigla_iso2 VARCHAR(2),
    sigla_iso3 VARCHAR(3),
    nome VARCHAR(100),
    nome_ingles VARCHAR(100),
    nome_frances VARCHAR(100),
    data_inicio TIMESTAMP,
    data_fim TIMESTAMP,
    interno_versao INTEGER
);
"""

CREATE_SUPORTE_MOEDA = """
CREATE TABLE IF NOT EXISTS suporte_moeda (
    codigo VARCHAR(10) PRIMARY KEY,
    nome VARCHAR(100),
    simbolo VARCHAR(10),
    codigo_swift VARCHAR(5),
    sigla_iso2 VARCHAR(5),
    data_inicio TIMESTAMP,
    data_fim TIMESTAMP,
    interno_versao INTEGER
);
"""

CREATE_SUPORTE_ENQUADRAMENTO = """
CREATE TABLE IF NOT EXISTS suporte_enquadramento (
    codigo INTEGER PRIMARY KEY,
    descricao VARCHAR(500),
    codigo_tipo_enquadramento VARCHAR(10),
    codigo_grupo_enquadramento VARCHAR(10),
    data_inicio TIMESTAMP,
    data_fim TIMESTAMP,
    interno_versao INTEGER
);
"""

CREATE_SUPORTE_FUNDAMENTO_LEGAL_TT = """
CREATE TABLE IF NOT EXISTS suporte_fundamento_legal_tt (
    codigo INTEGER PRIMARY KEY,
    descricao VARCHAR(500),
    codigo_beneficio_fiscal_sisen VARCHAR(50),
    in_permite_registro_pessoa_fisica VARCHAR(10),
    data_inicio TIMESTAMP,
    data_fim TIMESTAMP,
    interno_versao INTEGER
);
"""

CREATE_SUPORTE_ORGAO_ANUENTE = """
CREATE TABLE IF NOT EXISTS suporte_orgao_anuente (
    codigo VARCHAR(20) PRIMARY KEY,
    sigla VARCHAR(20),
    descricao VARCHAR(200),
    cnpj VARCHAR(20),
    data_inicio TIMESTAMP,
    data_fim TIMESTAMP,
    interno_versao INTEGER
);
"""

CREATE_SUPORTE_PORTO = """
CREATE TABLE IF NOT EXISTS suporte_porto (
    codigo VARCHAR(20) PRIMARY KEY,
    descricao VARCHAR(200),
    data_inicio TIMESTAMP,
    data_fim TIMESTAMP,
    interno_versao INTEGER
);
"""

CREATE_SUPORTE_RECINTO_ADUANEIRO = """
CREATE TABLE IF NOT EXISTS suporte_recinto_aduaneiro (
    codigo VARCHAR(20) PRIMARY KEY,
    nome VARCHAR(300),
    data_inicio TIMESTAMP,
    data_fim TIMESTAMP,
    interno_versao INTEGER
);
"""

CREATE_SUPORTE_SOLICITANTE = """
CREATE TABLE IF NOT EXISTS suporte_solicitante (
    codigo VARCHAR(20) PRIMARY KEY,
    descricao VARCHAR(200),
    data_inicio TIMESTAMP,
    data_fim TIMESTAMP,
    interno_versao INTEGER
);
"""

CREATE_SUPORTE_TIPO_AREA_EQUIPAMENTO = """
CREATE TABLE IF NOT EXISTS suporte_tipo_area_equipamento (
    codigo VARCHAR(10) PRIMARY KEY,
    descricao VARCHAR(200),
    data_inicio TIMESTAMP,
    data_fim TIMESTAMP,
    interno_versao INTEGER
);
"""

CREATE_SUPORTE_TIPO_CONHECIMENTO = """
CREATE TABLE IF NOT EXISTS suporte_tipo_conhecimento (
    codigo VARCHAR(20) PRIMARY KEY,
    descricao VARCHAR(200),
    indicador_tipo_basico VARCHAR(5),
    data_inicio TIMESTAMP,
    data_fim TIMESTAMP,
    interno_versao INTEGER
);
"""

CREATE_SUPORTE_TIPO_CONTEINER = """
CREATE TABLE IF NOT EXISTS suporte_tipo_conteiner (
    codigo VARCHAR(20) PRIMARY KEY,
    descricao VARCHAR(200),
    comprimento NUMERIC(10,2),
    dimensoes VARCHAR(100),
    codigo_grupo_tipo_conteiner VARCHAR(10),
    data_inicio TIMESTAMP,
    data_fim TIMESTAMP,
    interno_versao INTEGER
);
"""

CREATE_SUPORTE_TIPO_DECLARACAO_ADUANEIRA = """
CREATE TABLE IF NOT EXISTS suporte_tipo_declaracao_aduaneira (
    codigo VARCHAR(30) PRIMARY KEY,
    descricao VARCHAR(200),
    data_inicio TIMESTAMP,
    data_fim TIMESTAMP,
    interno_versao INTEGER
);
"""

CREATE_SUPORTE_UA_SRF = """
CREATE TABLE IF NOT EXISTS suporte_ua_srf (
    codigo VARCHAR(20) PRIMARY KEY,
    sigla VARCHAR(10),
    nome VARCHAR(100),
    regiao_fiscal VARCHAR(10),
    nome_curto VARCHAR(100),
    data_inicio TIMESTAMP,
    data_fim TIMESTAMP,
    interno_versao INTEGER
);
"""

CREATE_NFE_SAP = """
CREATE TABLE IF NOT EXISTS nfe_sap (
    chave_nf VARCHAR(44) PRIMARY KEY,
    data_importacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ativo BOOLEAN DEFAULT TRUE
);
CREATE INDEX IF NOT EXISTS idx_nfe_sap_data ON nfe_sap(data_importacao);
"""

# =============================================================================
# TABELAS DUE (22 tabelas)
# =============================================================================

CREATE_DUE_PRINCIPAL = """
CREATE TABLE IF NOT EXISTS due_principal (
    numero VARCHAR(14) PRIMARY KEY,
    chave_de_acesso VARCHAR(50),
    data_de_registro TIMESTAMP,
    bloqueio BOOLEAN,
    canal VARCHAR(20),
    embarque_em_recinto_alfandegado BOOLEAN,
    despacho_em_recinto_alfandegado BOOLEAN,
    forma_de_exportacao VARCHAR(50),
    impedido_de_embarque BOOLEAN,
    informacoes_complementares TEXT,
    ruc VARCHAR(35),
    situacao VARCHAR(100),
    situacao_do_tratamento_administrativo VARCHAR(50),
    tipo VARCHAR(50),
    tratamento_prioritario BOOLEAN,
    responsavel_pelo_acd VARCHAR(50),
    despacho_em_recinto_domiciliar BOOLEAN,
    data_de_criacao TIMESTAMP,
    data_do_cce TIMESTAMP,
    data_do_desembaraco TIMESTAMP,
    data_do_acd TIMESTAMP,
    data_da_averbacao TIMESTAMP,
    valor_total_mercadoria NUMERIC(15,2),
    inclusao_nota_fiscal BOOLEAN,
    exigencia_ativa BOOLEAN,
    consorciada BOOLEAN,
    dat BOOLEAN,
    oea BOOLEAN,
    declarante_numero_do_documento VARCHAR(20),
    declarante_tipo_do_documento VARCHAR(20),
    declarante_nome VARCHAR(150),
    declarante_estrangeiro BOOLEAN,
    declarante_nacionalidade_codigo INTEGER,
    declarante_nacionalidade_nome VARCHAR(50),
    declarante_nacionalidade_nome_resumido VARCHAR(5),
    moeda_codigo INTEGER,
    pais_importador_codigo INTEGER,
    recinto_aduaneiro_de_despacho_codigo VARCHAR(7),
    recinto_aduaneiro_de_embarque_codigo VARCHAR(7),
    unidade_local_de_despacho_codigo VARCHAR(7),
    unidade_local_de_embarque_codigo VARCHAR(7),
    declaracao_tributaria_divergente BOOLEAN,
    data_ultima_atualizacao TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_due_principal_canal ON due_principal(canal);
CREATE INDEX IF NOT EXISTS idx_due_principal_situacao ON due_principal(situacao);
CREATE INDEX IF NOT EXISTS idx_due_principal_data_criacao ON due_principal(data_de_criacao);
CREATE INDEX IF NOT EXISTS idx_due_principal_data_atualizacao ON due_principal(data_ultima_atualizacao);
"""

CREATE_NF_DUE_VINCULO = """
CREATE TABLE IF NOT EXISTS nf_due_vinculo (
    chave_nf VARCHAR(44) PRIMARY KEY,
    numero_due VARCHAR(14) NOT NULL,
    data_vinculo TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    origem VARCHAR(20) NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_nf_due_vinculo_numero_due ON nf_due_vinculo(numero_due);
"""

CREATE_DUE_EVENTOS_HISTORICO = """
CREATE TABLE IF NOT EXISTS due_eventos_historico (
    id SERIAL PRIMARY KEY,
    numero_due VARCHAR(14) NOT NULL,
    data_e_hora_do_evento TIMESTAMP,
    evento VARCHAR(150),
    responsavel VARCHAR(100),
    informacoes_adicionais TEXT,
    detalhes VARCHAR(400),
    motivo VARCHAR(150),
    tipo_evento VARCHAR(50),
    data TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_due_eventos_numero_due ON due_eventos_historico(numero_due);
CREATE INDEX IF NOT EXISTS idx_due_eventos_data ON due_eventos_historico(data_e_hora_do_evento);
"""

CREATE_DUE_ITENS = """
CREATE TABLE IF NOT EXISTS due_itens (
    id VARCHAR(30) PRIMARY KEY,
    numero_due VARCHAR(14) NOT NULL,
    numero_item INTEGER NOT NULL,
    quantidade_na_unidade_estatistica NUMERIC(14,5),
    peso_liquido_total NUMERIC(14,5),
    valor_da_mercadoria_na_condicao_de_venda NUMERIC(15,2),
    valor_da_mercadoria_no_local_de_embarque NUMERIC(15,2),
    valor_da_mercadoria_no_local_de_embarque_em_reais NUMERIC(15,2),
    valor_da_mercadoria_na_condicao_de_venda_em_reais NUMERIC(15,2),
    data_de_conversao TIMESTAMP,
    descricao_da_mercadoria TEXT,
    unidade_comercializada VARCHAR(20),
    nome_importador VARCHAR(60),
    endereco_importador VARCHAR(380),
    valor_total_calculado_item NUMERIC(13,2),
    quantidade_na_unidade_comercializada NUMERIC(14,5),
    ncm_codigo VARCHAR(8),
    ncm_descricao VARCHAR(500),
    ncm_unidade_medida_estatistica VARCHAR(20),
    exportador_numero_do_documento VARCHAR(20),
    exportador_tipo_do_documento VARCHAR(20),
    exportador_nome VARCHAR(150),
    exportador_estrangeiro BOOLEAN,
    exportador_nacionalidade_codigo INTEGER,
    exportador_nacionalidade_nome VARCHAR(50),
    exportador_nacionalidade_nome_resumido VARCHAR(5),
    codigo_condicao_venda VARCHAR(3),
    exportacao_temporaria BOOLEAN
);
CREATE INDEX IF NOT EXISTS idx_due_itens_numero_due ON due_itens(numero_due);
CREATE INDEX IF NOT EXISTS idx_due_itens_ncm ON due_itens(ncm_codigo);
"""

CREATE_DUE_ITEM_ENQUADRAMENTOS = """
CREATE TABLE IF NOT EXISTS due_item_enquadramentos (
    id SERIAL PRIMARY KEY,
    due_item_id VARCHAR(30) NOT NULL,
    numero_due VARCHAR(14) NOT NULL,
    numero_item INTEGER NOT NULL,
    codigo INTEGER,
    data_registro TIMESTAMP,
    descricao VARCHAR(500),
    grupo INTEGER,
    tipo INTEGER
);
CREATE INDEX IF NOT EXISTS idx_due_item_enq_numero_due ON due_item_enquadramentos(numero_due);
CREATE INDEX IF NOT EXISTS idx_due_item_enq_item_id ON due_item_enquadramentos(due_item_id);
"""

CREATE_DUE_ITEM_PAISES_DESTINO = """
CREATE TABLE IF NOT EXISTS due_item_paises_destino (
    id SERIAL PRIMARY KEY,
    due_item_id VARCHAR(30) NOT NULL,
    numero_due VARCHAR(14) NOT NULL,
    numero_item INTEGER NOT NULL,
    codigo_pais_destino INTEGER
);
CREATE INDEX IF NOT EXISTS idx_due_item_paises_numero_due ON due_item_paises_destino(numero_due);
"""

CREATE_DUE_ITEM_TRATAMENTOS_ADMINISTRATIVOS = """
CREATE TABLE IF NOT EXISTS due_item_tratamentos_administrativos (
    id VARCHAR(35) PRIMARY KEY,
    due_item_id VARCHAR(30) NOT NULL,
    numero_due VARCHAR(14) NOT NULL,
    numero_item INTEGER NOT NULL,
    mensagem TEXT,
    impeditivo_de_embarque BOOLEAN,
    codigo_lpco VARCHAR(20),
    situacao VARCHAR(50)
);
CREATE INDEX IF NOT EXISTS idx_due_item_trat_numero_due ON due_item_tratamentos_administrativos(numero_due);
"""

CREATE_DUE_ITEM_TRATAMENTOS_ADMINISTRATIVOS_ORGAOS = """
CREATE TABLE IF NOT EXISTS due_item_tratamentos_administrativos_orgaos (
    id SERIAL PRIMARY KEY,
    tratamento_administrativo_id VARCHAR(35) NOT NULL,
    due_item_id VARCHAR(30) NOT NULL,
    numero_due VARCHAR(14) NOT NULL,
    codigo_orgao VARCHAR(20)
);
CREATE INDEX IF NOT EXISTS idx_due_item_trat_orgaos_numero_due ON due_item_tratamentos_administrativos_orgaos(numero_due);
"""

CREATE_DUE_ITEM_NOTAS_REMESSA = """
CREATE TABLE IF NOT EXISTS due_item_notas_remessa (
    id SERIAL PRIMARY KEY,
    due_item_id VARCHAR(30) NOT NULL,
    numero_due VARCHAR(14) NOT NULL,
    numero_item INTEGER NOT NULL,
    numero_do_item INTEGER,
    chave_de_acesso VARCHAR(44),
    cfop INTEGER,
    codigo_do_produto VARCHAR(60),
    descricao TEXT,
    quantidade_estatistica NUMERIC(11,4),
    unidade_comercial VARCHAR(6),
    valor_total_bruto NUMERIC(13,2),
    quantidade_consumida NUMERIC(14,5),
    ncm_codigo VARCHAR(8),
    ncm_descricao VARCHAR(500),
    ncm_unidade_medida_estatistica VARCHAR(20),
    modelo VARCHAR(2),
    serie INTEGER,
    numero_do_documento INTEGER,
    uf_do_emissor VARCHAR(2),
    identificacao_emitente VARCHAR(20),
    apresentada_para_despacho BOOLEAN,
    finalidade VARCHAR(50),
    quantidade_de_itens INTEGER,
    nota_fiscal_eletronica BOOLEAN,
    emitente_cnpj BOOLEAN,
    emitente_cpf BOOLEAN
);
CREATE INDEX IF NOT EXISTS idx_due_item_notas_rem_numero_due ON due_item_notas_remessa(numero_due);
CREATE INDEX IF NOT EXISTS idx_due_item_notas_rem_chave ON due_item_notas_remessa(chave_de_acesso);
"""

CREATE_DUE_ITEM_NOTA_FISCAL_EXPORTACAO = """
CREATE TABLE IF NOT EXISTS due_item_nota_fiscal_exportacao (
    due_item_id VARCHAR(30) PRIMARY KEY,
    numero_due VARCHAR(14) NOT NULL,
    numero_item INTEGER NOT NULL,
    numero_do_item INTEGER,
    chave_de_acesso VARCHAR(44),
    modelo VARCHAR(2),
    serie INTEGER,
    numero_do_documento INTEGER,
    uf_do_emissor VARCHAR(2),
    identificacao_emitente VARCHAR(20),
    emitente_cnpj BOOLEAN,
    emitente_cpf BOOLEAN,
    finalidade VARCHAR(50),
    quantidade_de_itens INTEGER,
    nota_fiscal_eletronica BOOLEAN,
    cfop INTEGER,
    codigo_do_produto VARCHAR(60),
    descricao TEXT,
    quantidade_estatistica NUMERIC(11,4),
    unidade_comercial VARCHAR(6),
    valor_total_calculado NUMERIC(13,2),
    ncm_codigo VARCHAR(8),
    ncm_descricao VARCHAR(500),
    ncm_unidade_medida_estatistica VARCHAR(20),
    apresentada_para_despacho BOOLEAN
);
CREATE INDEX IF NOT EXISTS idx_due_item_nf_exp_numero_due ON due_item_nota_fiscal_exportacao(numero_due);
CREATE INDEX IF NOT EXISTS idx_due_item_nf_exp_chave ON due_item_nota_fiscal_exportacao(chave_de_acesso);
"""

CREATE_DUE_ITEM_NOTAS_COMPLEMENTARES = """
CREATE TABLE IF NOT EXISTS due_item_notas_complementares (
    id SERIAL PRIMARY KEY,
    due_item_id VARCHAR(30) NOT NULL,
    numero_due VARCHAR(14) NOT NULL,
    numero_item INTEGER NOT NULL,
    indice INTEGER NOT NULL,
    numero_do_item INTEGER,
    chave_de_acesso VARCHAR(44),
    modelo VARCHAR(2),
    serie INTEGER,
    numero_do_documento INTEGER,
    uf_do_emissor VARCHAR(2),
    identificacao_emitente VARCHAR(20),
    cfop INTEGER,
    codigo_do_produto VARCHAR(60),
    descricao TEXT,
    quantidade_estatistica NUMERIC(11,4),
    unidade_comercial VARCHAR(6),
    valor_total_bruto NUMERIC(13,2),
    ncm_codigo VARCHAR(8)
);
CREATE INDEX IF NOT EXISTS idx_due_item_notas_comp_numero_due ON due_item_notas_complementares(numero_due);
"""

CREATE_DUE_ITEM_ATRIBUTOS = """
CREATE TABLE IF NOT EXISTS due_item_atributos (
    id SERIAL PRIMARY KEY,
    due_item_id VARCHAR(30) NOT NULL,
    numero_due VARCHAR(14) NOT NULL,
    numero_item INTEGER NOT NULL,
    indice INTEGER NOT NULL,
    codigo VARCHAR(20),
    valor VARCHAR(500),
    descricao VARCHAR(200)
);
CREATE INDEX IF NOT EXISTS idx_due_item_atrib_numero_due ON due_item_atributos(numero_due);
"""

CREATE_DUE_ITEM_DOCUMENTOS_IMPORTACAO = """
CREATE TABLE IF NOT EXISTS due_item_documentos_importacao (
    id SERIAL PRIMARY KEY,
    due_item_id VARCHAR(30) NOT NULL,
    numero_due VARCHAR(14) NOT NULL,
    numero_item INTEGER NOT NULL,
    indice INTEGER NOT NULL,
    tipo VARCHAR(30),
    numero VARCHAR(50),
    data_registro TIMESTAMP,
    item_documento INTEGER,
    quantidade_utilizada NUMERIC(14,5)
);
CREATE INDEX IF NOT EXISTS idx_due_item_docs_imp_numero_due ON due_item_documentos_importacao(numero_due);
"""

CREATE_DUE_ITEM_DOCUMENTOS_TRANSFORMACAO = """
CREATE TABLE IF NOT EXISTS due_item_documentos_transformacao (
    id SERIAL PRIMARY KEY,
    due_item_id VARCHAR(30) NOT NULL,
    numero_due VARCHAR(14) NOT NULL,
    numero_item INTEGER NOT NULL,
    indice INTEGER NOT NULL,
    tipo VARCHAR(30),
    numero VARCHAR(50),
    data_registro TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_due_item_docs_transf_numero_due ON due_item_documentos_transformacao(numero_due);
"""

CREATE_DUE_ITEM_CALCULO_TRIBUTARIO_TRATAMENTOS = """
CREATE TABLE IF NOT EXISTS due_item_calculo_tributario_tratamentos (
    id SERIAL PRIMARY KEY,
    due_item_id VARCHAR(30) NOT NULL,
    numero_due VARCHAR(14) NOT NULL,
    numero_item INTEGER NOT NULL,
    indice INTEGER NOT NULL,
    codigo VARCHAR(20),
    descricao VARCHAR(200),
    tipo VARCHAR(50),
    tributo VARCHAR(20)
);
CREATE INDEX IF NOT EXISTS idx_due_item_calc_trat_numero_due ON due_item_calculo_tributario_tratamentos(numero_due);
"""

CREATE_DUE_ITEM_CALCULO_TRIBUTARIO_QUADROS = """
CREATE TABLE IF NOT EXISTS due_item_calculo_tributario_quadros (
    id SERIAL PRIMARY KEY,
    due_item_id VARCHAR(30) NOT NULL,
    numero_due VARCHAR(14) NOT NULL,
    numero_item INTEGER NOT NULL,
    indice INTEGER NOT NULL,
    tributo VARCHAR(20),
    base_de_calculo NUMERIC(15,2),
    aliquota NUMERIC(7,4),
    valor_devido NUMERIC(15,2),
    valor_recolhido NUMERIC(15,2),
    valor_compensado NUMERIC(15,2)
);
CREATE INDEX IF NOT EXISTS idx_due_item_calc_quadros_numero_due ON due_item_calculo_tributario_quadros(numero_due);
"""

CREATE_DUE_SITUACOES_CARGA = """
CREATE TABLE IF NOT EXISTS due_situacoes_carga (
    id SERIAL PRIMARY KEY,
    numero_due VARCHAR(14) NOT NULL,
    sequencial INTEGER,
    codigo INTEGER,
    descricao VARCHAR(50),
    carga_operada BOOLEAN
);
CREATE INDEX IF NOT EXISTS idx_due_sit_carga_numero_due ON due_situacoes_carga(numero_due);
"""

CREATE_DUE_SOLICITACOES = """
CREATE TABLE IF NOT EXISTS due_solicitacoes (
    id SERIAL PRIMARY KEY,
    numero_due VARCHAR(14) NOT NULL,
    tipo_solicitacao VARCHAR(50),
    data_da_solicitacao TIMESTAMP,
    usuario_responsavel VARCHAR(20),
    codigo_do_status_da_solicitacao INTEGER,
    status_da_solicitacao VARCHAR(100),
    data_de_apreciacao TIMESTAMP,
    motivo VARCHAR(600)
);
CREATE INDEX IF NOT EXISTS idx_due_solic_numero_due ON due_solicitacoes(numero_due);
"""

CREATE_DUE_DECLARACAO_TRIBUTARIA_COMPENSACOES = """
CREATE TABLE IF NOT EXISTS due_declaracao_tributaria_compensacoes (
    id SERIAL PRIMARY KEY,
    numero_due VARCHAR(14) NOT NULL,
    codigo_receita VARCHAR(20),
    data_do_registro TIMESTAMP,
    numero_da_declaracao VARCHAR(24),
    valor_compensado NUMERIC(15,2)
);
CREATE INDEX IF NOT EXISTS idx_due_decl_comp_numero_due ON due_declaracao_tributaria_compensacoes(numero_due);
"""

CREATE_DUE_DECLARACAO_TRIBUTARIA_RECOLHIMENTOS = """
CREATE TABLE IF NOT EXISTS due_declaracao_tributaria_recolhimentos (
    id SERIAL PRIMARY KEY,
    numero_due VARCHAR(14) NOT NULL,
    codigo_receita VARCHAR(20),
    data_do_pagamento TIMESTAMP,
    data_do_registro TIMESTAMP,
    valor_da_multa NUMERIC(15,2),
    valor_do_imposto_recolhido NUMERIC(15,2),
    valor_dos_juros_mora NUMERIC(15,2)
);
CREATE INDEX IF NOT EXISTS idx_due_decl_recol_numero_due ON due_declaracao_tributaria_recolhimentos(numero_due);
"""

CREATE_DUE_DECLARACAO_TRIBUTARIA_CONTESTACOES = """
CREATE TABLE IF NOT EXISTS due_declaracao_tributaria_contestacoes (
    id SERIAL PRIMARY KEY,
    numero_due VARCHAR(14) NOT NULL,
    indice INTEGER NOT NULL,
    data_do_registro TIMESTAMP,
    motivo VARCHAR(600),
    status VARCHAR(50),
    data_de_apreciacao TIMESTAMP,
    observacao TEXT
);
CREATE INDEX IF NOT EXISTS idx_due_decl_cont_numero_due ON due_declaracao_tributaria_contestacoes(numero_due);
"""

CREATE_DUE_ATOS_CONCESSORIOS_SUSPENSAO = """
CREATE TABLE IF NOT EXISTS due_atos_concessorios_suspensao (
    id SERIAL PRIMARY KEY,
    numero_due VARCHAR(14) NOT NULL,
    ato_numero VARCHAR(20),
    tipo_codigo INTEGER,
    tipo_descricao VARCHAR(100),
    item_numero VARCHAR(10),
    item_ncm VARCHAR(8),
    beneficiario_cnpj VARCHAR(14),
    quantidade_exportada NUMERIC(14,5),
    valor_com_cobertura_cambial NUMERIC(15,2),
    valor_sem_cobertura_cambial NUMERIC(15,2),
    item_de_due_numero VARCHAR(10)
);
CREATE INDEX IF NOT EXISTS idx_due_atos_conc_numero_due ON due_atos_concessorios_suspensao(numero_due);
"""

CREATE_DUE_ATOS_CONCESSORIOS_ISENCAO = """
CREATE TABLE IF NOT EXISTS due_atos_concessorios_isencao (
    id SERIAL PRIMARY KEY,
    numero_due VARCHAR(14) NOT NULL,
    ato_numero VARCHAR(20),
    tipo_codigo INTEGER,
    tipo_descricao VARCHAR(100),
    item_numero VARCHAR(10),
    item_ncm VARCHAR(8),
    beneficiario_cnpj VARCHAR(14),
    quantidade_exportada NUMERIC(14,5),
    valor_com_cobertura_cambial NUMERIC(15,2),
    valor_sem_cobertura_cambial NUMERIC(15,2),
    item_de_due_numero VARCHAR(10)
);
CREATE INDEX IF NOT EXISTS idx_due_atos_isencao_numero_due ON due_atos_concessorios_isencao(numero_due);
"""

CREATE_DUE_EXIGENCIAS_FISCAIS = """
CREATE TABLE IF NOT EXISTS due_exigencias_fiscais (
    id SERIAL PRIMARY KEY,
    numero_due VARCHAR(14) NOT NULL,
    numero_exigencia VARCHAR(20),
    tipo_exigencia VARCHAR(50),
    data_criacao TIMESTAMP,
    data_limite TIMESTAMP,
    status VARCHAR(50),
    orgao_responsavel VARCHAR(100),
    descricao TEXT,
    valor_exigido NUMERIC(15,2),
    valor_pago NUMERIC(15,2),
    observacoes TEXT
);
CREATE INDEX IF NOT EXISTS idx_due_exigencias_numero_due ON due_exigencias_fiscais(numero_due);
CREATE INDEX IF NOT EXISTS idx_due_exigencias_status ON due_exigencias_fiscais(status);
"""

# =============================================================================
# Lista de todas as tabelas em ordem de criacao
# =============================================================================

ALL_TABLES = [
    # Tabelas de suporte
    ("suporte_pais", CREATE_SUPORTE_PAIS),
    ("suporte_moeda", CREATE_SUPORTE_MOEDA),
    ("suporte_enquadramento", CREATE_SUPORTE_ENQUADRAMENTO),
    ("suporte_fundamento_legal_tt", CREATE_SUPORTE_FUNDAMENTO_LEGAL_TT),
    ("suporte_orgao_anuente", CREATE_SUPORTE_ORGAO_ANUENTE),
    ("suporte_porto", CREATE_SUPORTE_PORTO),
    ("suporte_recinto_aduaneiro", CREATE_SUPORTE_RECINTO_ADUANEIRO),
    ("suporte_solicitante", CREATE_SUPORTE_SOLICITANTE),
    ("suporte_tipo_area_equipamento", CREATE_SUPORTE_TIPO_AREA_EQUIPAMENTO),
    ("suporte_tipo_conhecimento", CREATE_SUPORTE_TIPO_CONHECIMENTO),
    ("suporte_tipo_conteiner", CREATE_SUPORTE_TIPO_CONTEINER),
    ("suporte_tipo_declaracao_aduaneira", CREATE_SUPORTE_TIPO_DECLARACAO_ADUANEIRA),
    ("suporte_ua_srf", CREATE_SUPORTE_UA_SRF),
    ("nfe_sap", CREATE_NFE_SAP),
    # Tabelas DUE
    ("due_principal", CREATE_DUE_PRINCIPAL),
    ("nf_due_vinculo", CREATE_NF_DUE_VINCULO),
    ("due_eventos_historico", CREATE_DUE_EVENTOS_HISTORICO),
    ("due_itens", CREATE_DUE_ITENS),
    ("due_item_enquadramentos", CREATE_DUE_ITEM_ENQUADRAMENTOS),
    ("due_item_paises_destino", CREATE_DUE_ITEM_PAISES_DESTINO),
    ("due_item_tratamentos_administrativos", CREATE_DUE_ITEM_TRATAMENTOS_ADMINISTRATIVOS),
    ("due_item_tratamentos_administrativos_orgaos", CREATE_DUE_ITEM_TRATAMENTOS_ADMINISTRATIVOS_ORGAOS),
    ("due_item_notas_remessa", CREATE_DUE_ITEM_NOTAS_REMESSA),
    ("due_item_nota_fiscal_exportacao", CREATE_DUE_ITEM_NOTA_FISCAL_EXPORTACAO),
    ("due_item_notas_complementares", CREATE_DUE_ITEM_NOTAS_COMPLEMENTARES),
    ("due_item_atributos", CREATE_DUE_ITEM_ATRIBUTOS),
    ("due_item_documentos_importacao", CREATE_DUE_ITEM_DOCUMENTOS_IMPORTACAO),
    ("due_item_documentos_transformacao", CREATE_DUE_ITEM_DOCUMENTOS_TRANSFORMACAO),
    ("due_item_calculo_tributario_tratamentos", CREATE_DUE_ITEM_CALCULO_TRIBUTARIO_TRATAMENTOS),
    ("due_item_calculo_tributario_quadros", CREATE_DUE_ITEM_CALCULO_TRIBUTARIO_QUADROS),
    ("due_situacoes_carga", CREATE_DUE_SITUACOES_CARGA),
    ("due_solicitacoes", CREATE_DUE_SOLICITACOES),
    ("due_declaracao_tributaria_compensacoes", CREATE_DUE_DECLARACAO_TRIBUTARIA_COMPENSACOES),
    ("due_declaracao_tributaria_recolhimentos", CREATE_DUE_DECLARACAO_TRIBUTARIA_RECOLHIMENTOS),
    ("due_declaracao_tributaria_contestacoes", CREATE_DUE_DECLARACAO_TRIBUTARIA_CONTESTACOES),
    ("due_atos_concessorios_suspensao", CREATE_DUE_ATOS_CONCESSORIOS_SUSPENSAO),
    ("due_atos_concessorios_isencao", CREATE_DUE_ATOS_CONCESSORIOS_ISENCAO),
    ("due_exigencias_fiscais", CREATE_DUE_EXIGENCIAS_FISCAIS),
]

# DDL para dropar todas as tabelas (ordem reversa por causa das FKs)
DROP_ALL_TABLES = """
DROP TABLE IF EXISTS due_exigencias_fiscais CASCADE;
DROP TABLE IF EXISTS due_atos_concessorios_isencao CASCADE;
DROP TABLE IF EXISTS due_atos_concessorios_suspensao CASCADE;
DROP TABLE IF EXISTS due_declaracao_tributaria_contestacoes CASCADE;
DROP TABLE IF EXISTS due_declaracao_tributaria_recolhimentos CASCADE;
DROP TABLE IF EXISTS due_declaracao_tributaria_compensacoes CASCADE;
DROP TABLE IF EXISTS due_solicitacoes CASCADE;
DROP TABLE IF EXISTS due_situacoes_carga CASCADE;
DROP TABLE IF EXISTS due_item_calculo_tributario_quadros CASCADE;
DROP TABLE IF EXISTS due_item_calculo_tributario_tratamentos CASCADE;
DROP TABLE IF EXISTS due_item_documentos_transformacao CASCADE;
DROP TABLE IF EXISTS due_item_documentos_importacao CASCADE;
DROP TABLE IF EXISTS due_item_atributos CASCADE;
DROP TABLE IF EXISTS due_item_notas_complementares CASCADE;
DROP TABLE IF EXISTS due_item_nota_fiscal_exportacao CASCADE;
DROP TABLE IF EXISTS due_item_notas_remessa CASCADE;
DROP TABLE IF EXISTS due_item_tratamentos_administrativos_orgaos CASCADE;
DROP TABLE IF EXISTS due_item_tratamentos_administrativos CASCADE;
DROP TABLE IF EXISTS due_item_paises_destino CASCADE;
DROP TABLE IF EXISTS due_item_enquadramentos CASCADE;
DROP TABLE IF EXISTS due_itens CASCADE;
DROP TABLE IF EXISTS due_eventos_historico CASCADE;
DROP TABLE IF EXISTS nf_due_vinculo CASCADE;
DROP TABLE IF EXISTS due_principal CASCADE;
DROP TABLE IF EXISTS nfe_sap CASCADE;
DROP TABLE IF EXISTS suporte_ua_srf CASCADE;
DROP TABLE IF EXISTS suporte_tipo_declaracao_aduaneira CASCADE;
DROP TABLE IF EXISTS suporte_tipo_conteiner CASCADE;
DROP TABLE IF EXISTS suporte_tipo_conhecimento CASCADE;
DROP TABLE IF EXISTS suporte_tipo_area_equipamento CASCADE;
DROP TABLE IF EXISTS suporte_solicitante CASCADE;
DROP TABLE IF EXISTS suporte_recinto_aduaneiro CASCADE;
DROP TABLE IF EXISTS suporte_porto CASCADE;
DROP TABLE IF EXISTS suporte_orgao_anuente CASCADE;
DROP TABLE IF EXISTS suporte_fundamento_legal_tt CASCADE;
DROP TABLE IF EXISTS suporte_enquadramento CASCADE;
DROP TABLE IF EXISTS suporte_moeda CASCADE;
DROP TABLE IF EXISTS suporte_pais CASCADE;
"""

if __name__ == "__main__":
    logger.info(f"Schema definido com {len(ALL_TABLES)} tabelas")
    for nome, _ in ALL_TABLES:
        logger.info(f"  - {nome}")
