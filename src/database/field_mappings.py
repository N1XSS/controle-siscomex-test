"""Mapeamentos centralizados de campos JSON → Database (camelCase → snake_case)."""

from __future__ import annotations

# Mapeamento para tabela due_principal
DUE_PRINCIPAL_MAPPING = {
    'numero': 'numero',
    'chaveDeAcesso': 'chave_de_acesso',
    'dataDeRegistro': 'data_de_registro',
    'bloqueio': 'bloqueio',
    'canal': 'canal',
    'embarqueEmRecintoAlfandegado': 'embarque_em_recinto_alfandegado',
    'despachoEmRecintoAlfandegado': 'despacho_em_recinto_alfandegado',
    'formaDeExportacao': 'forma_de_exportacao',
    'impedidoDeEmbarque': 'impedido_de_embarque',
    'informacoesComplementares': 'informacoes_complementares',
    'ruc': 'ruc',
    'situacao': 'situacao',
    'situacaoDoTratamentoAdministrativo': 'situacao_do_tratamento_administrativo',
    'tipo': 'tipo',
    'tratamentoPrioritario': 'tratamento_prioritario',
    'responsavelPeloACD': 'responsavel_pelo_acd',
    'despachoEmRecintoDomiciliar': 'despacho_em_recinto_domiciliar',
    'dataDeCriacao': 'data_de_criacao',
    'dataDoCCE': 'data_do_cce',
    'dataDoDesembaraco': 'data_do_desembaraco',
    'dataDoAcd': 'data_do_acd',
    'dataDaAverbacao': 'data_da_averbacao',
    'valorTotalMercadoria': 'valor_total_mercadoria',
    'inclusaoNotaFiscal': 'inclusao_nota_fiscal',
    'exigenciaAtiva': 'exigencia_ativa',
    'consorciada': 'consorciada',
    'dat': 'dat',
    'oea': 'oea',
}

# Mapeamento genérico para múltiplas tabelas (campos comuns)
COMMON_FIELD_MAPPING = {
    'numero': 'numero',
    'descricao': 'descricao',
    'codigo': 'codigo',
    'nome': 'nome',
    'valor': 'valor',
    'quantidade': 'quantidade',
    'unidadeDeMedida': 'unidade_de_medida',
    'dataInicio': 'data_inicio',
    'dataFim': 'data_fim',
}

# Lista de campos que devem ser convertidos para numérico
NUMERIC_FIELDS = [
    'valor',
    'quantidade',
    'peso',
    'valorUnitario',
    'valorTotal',
    'quantidadeEstatistica',
    'pesoLiquido',
    'pesoBruto',
]

# Lista de campos que devem ser convertidos para data
DATE_FIELDS = [
    'dataDeRegistro',
    'dataDeCriacao',
    'dataDoCCE',
    'dataDoDesembaraco',
    'dataDoAcd',
    'dataDaAverbacao',
    'dataInicio',
    'dataFim',
]
