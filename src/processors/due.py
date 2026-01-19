import json
import os
import threading
import time
import warnings
from typing import Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.core.constants import DEFAULT_HTTP_TIMEOUT_SEC, ENV_CONFIG_FILE, HTTP_REQUEST_TIMEOUT_SEC
from src.database.manager import db_manager
from src.core.logger import logger
from src.api.siscomex.token import token_manager
warnings.filterwarnings('ignore')

# Flag para usar PostgreSQL ou CSV
USAR_POSTGRESQL = True

# Carregar variáveis de ambiente do arquivo .env
load_dotenv(ENV_CONFIG_FILE)

# Configurações da API Siscomex
URL_DUE_BASE = "https://portalunico.siscomex.gov.br/due/api/ext/due"

def ler_chaves_nf(arquivo_csv: str = 'dados/nfe-sap.csv') -> list[str]:
    """Lê as chaves de NF do CSV gerado pelo SAP"""
    try:
        if not os.path.exists(arquivo_csv):
            logger.info(f"❌ Arquivo {arquivo_csv} não encontrado")
            logger.info("Execute primeiro o código de consulta SAP HANA (sap-nf.py)")
            return []
        
        df = pd.read_csv(arquivo_csv, sep=';', encoding='utf-8-sig')
        
        if 'Chave NF' not in df.columns:
            logger.info("❌ Coluna 'Chave NF' não encontrada no CSV")
            return []
        
        # Filtrar apenas chaves válidas (não vazias e não nulas)
        chaves = df['Chave NF'].dropna().astype(str)
        chaves = chaves[chaves.str.len() > 40]  # Chaves NF têm 44 dígitos
        chaves = chaves.unique().tolist()
        
        logger.info(f"📋 {len(chaves)} chaves de NF únicas encontradas")
        return chaves
        
    except Exception as e:
        logger.info(f"❌ Erro ao ler CSV: {e}")
        return []

def processar_dados_due(
    dados_due: dict[str, Any],
    atos_concessorios: list[dict[str, Any]] | None = None,
    atos_isencao: list[dict[str, Any]] | None = None,
    exigencias_fiscais: list[dict[str, Any]] | None = None,
    debug_mode: bool = False,
) -> dict[str, list[dict[str, Any]]] | None:
    """Processa e normaliza os dados da DUE.

    Args:
        dados_due: Payload completo da DUE.
        atos_concessorios: Lista de atos concessorios de suspensao.
        atos_isencao: Lista de atos concessorios de isencao.
        exigencias_fiscais: Lista de exigencias fiscais.
        debug_mode: Quando True, loga detalhes adicionais.

    Returns:
        Estrutura normalizada por tabela ou None em caso de erro.
    """
    
    # Verificação inicial dos dados
    if not dados_due or not isinstance(dados_due, dict):
        if debug_mode:
            logger.info(f"⚠️  Dados DUE inválidos ou vazios: {type(dados_due)}")
        return None
    
    numero_due = dados_due.get('numero', '')
    if not numero_due:
        if debug_mode:
            logger.info(f"⚠️  Número da DUE não encontrado nos dados")
        return None
    
    # Debug: mostrar estrutura dos dados recebidos
    if debug_mode:
        logger.info(f"🔍 Processando DUE {numero_due}:")
        logger.info(f"   • Campos principais: {list(dados_due.keys())}")
        logger.info(f"   • Eventos histórico: {len(dados_due.get('eventosDoHistorico', []))}")
        logger.info(f"   • Itens: {len(dados_due.get('itens', []))}")
        logger.info(f"   • Situações carga: {len(dados_due.get('situacoesDaCarga', []))}")
        logger.info(f"   • Solicitações: {len(dados_due.get('solicitacoes', []))}")
        logger.info(f"   • Declaração tributária: {'declaracaoTributaria' in dados_due}")
        if 'declaracaoTributaria' in dados_due:
            declaracao = dados_due.get('declaracaoTributaria', {})
            logger.info(f"   • Compensações: {len(declaracao.get('compensacoes', []))}")
            logger.info(f"   • Recolhimentos: {len(declaracao.get('recolhimentos', []))}")
        if atos_concessorios:
            logger.info(f"   • Atos concessórios suspensão: {len(atos_concessorios) if isinstance(atos_concessorios, list) else 0}")
        if atos_isencao:
            logger.info(f"   • Atos concessórios isenção: {len(atos_isencao) if isinstance(atos_isencao, list) else 0}")
        if exigencias_fiscais:
            logger.info(f"   • Exigências fiscais: {len(exigencias_fiscais) if isinstance(exigencias_fiscais, list) else 0}")
    
    # Estruturas para armazenar os dados normalizados
    dados_normalizados = {
        'due_principal': [],
        'due_eventos_historico': [],
        'due_itens': [],
        'due_item_enquadramentos': [],
        'due_item_paises_destino': [],
        'due_item_tratamentos_administrativos': [],
        'due_item_tratamentos_administrativos_orgaos': [],
        'due_item_notas_remessa': [],
        'due_item_nota_fiscal_exportacao': [],
        'due_item_notas_complementares': [],
        'due_item_atributos': [],
        'due_item_documentos_importacao': [],
        'due_item_documentos_transformacao': [],
        'due_item_calculo_tributario_tratamentos': [],
        'due_item_calculo_tributario_quadros': [],
        'due_situacoes_carga': [],
        'due_solicitacoes': [],
        'due_declaracao_tributaria_compensacoes': [],
        'due_declaracao_tributaria_recolhimentos': [],
        'due_declaracao_tributaria_contestacoes': [],
        'due_atos_concessorios_suspensao': []
    }
    
    # 1. Dados principais da DUE (1:1)
    due_principal = {
        'numero': numero_due,
        'chaveDeAcesso': dados_due.get('chaveDeAcesso', ''),
        'dataDeRegistro': dados_due.get('dataDeRegistro', ''),
        'bloqueio': dados_due.get('bloqueio', False),
        'canal': dados_due.get('canal', ''),
        'embarqueEmRecintoAlfandegado': dados_due.get('embarqueEmRecintoAlfandegado', False),
        'despachoEmRecintoAlfandegado': dados_due.get('despachoEmRecintoAlfandegado', False),
        'formaDeExportacao': dados_due.get('formaDeExportacao', ''),
        'impedidoDeEmbarque': dados_due.get('impedidoDeEmbarque', False),
        'informacoesComplementares': dados_due.get('informacoesComplementares', ''),
        'ruc': dados_due.get('ruc', ''),
        'situacao': dados_due.get('situacao', ''),
        'situacaoDoTratamentoAdministrativo': dados_due.get('situacaoDoTratamentoAdministrativo', ''),
        'tipo': dados_due.get('tipo', ''),
        'tratamentoPrioritario': dados_due.get('tratamentoPrioritario', False),
        'responsavelPeloACD': dados_due.get('responsavelPeloACD', ''),
        'despachoEmRecintoDomiciliar': dados_due.get('despachoEmRecintoDomiciliar', False),
        'dataDeCriacao': dados_due.get('dataDeCriacao', ''),
        'dataDoCCE': dados_due.get('dataDoCCE', ''),
        'dataDoDesembaraco': dados_due.get('dataDoDesembaraco', ''),
        'dataDoAcd': dados_due.get('dataDoAcd', ''),
        'dataDaAverbacao': dados_due.get('dataDaAverbacao', ''),
        'valorTotalMercadoria': dados_due.get('valorTotalMercadoria', 0),
        'inclusaoNotaFiscal': dados_due.get('inclusaoNotaFiscal', False),
        'exigenciaAtiva': dados_due.get('exigenciaAtiva', False),
        'consorciada': dados_due.get('consorciada', False),
        'dat': dados_due.get('dat', False),
        'oea': dados_due.get('oea', False),
        # Dados do declarante
        'declarante_numeroDoDocumento': dados_due.get('declarante', {}).get('numeroDoDocumento', ''),
        'declarante_tipoDoDocumento': dados_due.get('declarante', {}).get('tipoDoDocumento', ''),
        'declarante_nome': dados_due.get('declarante', {}).get('nome', ''),
        'declarante_estrangeiro': dados_due.get('declarante', {}).get('estrangeiro', False),
        'declarante_nacionalidade_codigo': dados_due.get('declarante', {}).get('nacionalidade', {}).get('codigo', 0),
        'declarante_nacionalidade_nome': dados_due.get('declarante', {}).get('nacionalidade', {}).get('nome', ''),
        'declarante_nacionalidade_nomeResumido': dados_due.get('declarante', {}).get('nacionalidade', {}).get('nomeResumido', ''),
        # Moeda
        'moeda_codigo': dados_due.get('moeda', {}).get('codigo', 0),
        # País importador
        'paisImportador_codigo': dados_due.get('paisImportador', {}).get('codigo', 0),
        # Recintos
        'recintoAduaneiroDeDespacho_codigo': dados_due.get('recintoAduaneiroDeDespacho', {}).get('codigo', ''),
        'recintoAduaneiroDeEmbarque_codigo': dados_due.get('recintoAduaneiroDeEmbarque', {}).get('codigo', ''),
        # Unidades locais
        'unidadeLocalDeDespacho_codigo': dados_due.get('unidadeLocalDeDespacho', {}).get('codigo', ''),
        'unidadeLocalDeEmbarque_codigo': dados_due.get('unidadeLocalDeEmbarque', {}).get('codigo', ''),
        # Declaracao tributaria - divergente
        'declaracaoTributaria_divergente': dados_due.get('declaracaoTributaria', {}).get('divergente', False),
        # Data da ultima atualizacao via API
        'data_ultima_atualizacao': datetime.now(timezone.utc).isoformat(),
    }
    dados_normalizados['due_principal'].append(due_principal)
    
    # 2. Eventos do histórico
    for evento in dados_due.get('eventosDoHistorico', []):
        evento_row = {
            'numero_due': numero_due,
            'dataEHoraDoEvento': evento.get('dataEHoraDoEvento', ''),
            'evento': evento.get('evento', ''),
            'responsavel': evento.get('responsavel', ''),
            'informacoesAdicionais': evento.get('informacoesAdicionais', ''),
            'detalhes': evento.get('detalhes', ''),
            'motivo': evento.get('motivo', '')
        }
        dados_normalizados['due_eventos_historico'].append(evento_row)
    
    # 3. Itens da DUE
    for item in dados_due.get('itens', []):
        item_id = f"{numero_due}_{item.get('numero', 0)}"
        
        item_row = {
            'id': item_id,
            'numero_due': numero_due,
            'numero': item.get('numero', 0),
            'quantidadeNaUnidadeEstatistica': item.get('quantidadeNaUnidadeEstatistica', 0),
            'pesoLiquidoTotal': item.get('pesoLiquidoTotal', 0),
            'valorDaMercadoriaNaCondicaoDeVenda': item.get('valorDaMercadoriaNaCondicaoDeVenda', 0),
            'valorDaMercadoriaNoLocalDeEmbarque': item.get('valorDaMercadoriaNoLocalDeEmbarque', 0),
            'valorDaMercadoriaNoLocalDeEmbarqueEmReais': item.get('valorDaMercadoriaNoLocalDeEmbarqueEmReais', 0),
            'valorDaMercadoriaNaCondicaoDeVendaEmReais': item.get('valorDaMercadoriaNaCondicaoDeVendaEmReais', 0),
            'dataDeConversao': item.get('dataDeConversao', ''),
            'descricaoDaMercadoria': item.get('descricaoDaMercadoria', ''),
            'unidadeComercializada': item.get('unidadeComercializada', ''),
            'nomeImportador': item.get('nomeImportador', ''),
            'enderecoImportador': item.get('enderecoImportador', ''),
            'valorTotalCalculadoItem': item.get('valorTotalCalculadoItem', 0),
            'quantidadeNaUnidadeComercializada': item.get('quantidadeNaUnidadeComercializada', 0),
            # NCM
            'ncm_codigo': item.get('ncm', {}).get('codigo', ''),
            'ncm_descricao': item.get('ncm', {}).get('descricao', ''),
            'ncm_unidadeMedidaEstatistica': item.get('ncm', {}).get('unidadeMedidaEstatistica', ''),
            # Exportador
            'exportador_numeroDoDocumento': item.get('exportador', {}).get('numeroDoDocumento', ''),
            'exportador_tipoDoDocumento': item.get('exportador', {}).get('tipoDoDocumento', ''),
            'exportador_nome': item.get('exportador', {}).get('nome', ''),
            'exportador_estrangeiro': item.get('exportador', {}).get('estrangeiro', False),
            'exportador_nacionalidade_codigo': item.get('exportador', {}).get('nacionalidade', {}).get('codigo', 0),
            'exportador_nacionalidade_nome': item.get('exportador', {}).get('nacionalidade', {}).get('nome', ''),
            'exportador_nacionalidade_nomeResumido': item.get('exportador', {}).get('nacionalidade', {}).get('nomeResumido', ''),
            # Condição de venda
            'codigoCondicaoVenda': item.get('codigoCondicaoVenda', {}).get('codigo', ''),
            # Exportação temporária
            'exportacaoTemporaria': item.get('exportacaoTemporaria', {}).get('temporaria', False),
        }
        dados_normalizados['due_itens'].append(item_row)
        
        # 4. Enquadramentos do item
        for enquadramento in item.get('listaDeEnquadramentos', []):
            enq_row = {
                'due_item_id': item_id,
                'numero_due': numero_due,
                'item_numero': item.get('numero', 0),
                'codigo': enquadramento.get('codigo', 0),
                'dataRegistro': enquadramento.get('dataRegistro', ''),
                'descricao': enquadramento.get('descricao', ''),
                'grupo': enquadramento.get('grupo', 0),
                'tipo': enquadramento.get('tipo', 0)
            }
            dados_normalizados['due_item_enquadramentos'].append(enq_row)
        
        # 5. Países de destino do item
        for pais in item.get('listaPaisDestino', []):
            pais_row = {
                'due_item_id': item_id,
                'numero_due': numero_due,
                'item_numero': item.get('numero', 0),
                'codigo_pais': pais.get('codigo', 0)
            }
            dados_normalizados['due_item_paises_destino'].append(pais_row)
        
        # 6. Tratamentos administrativos do item
        for idx, tratamento in enumerate(item.get('tratamentosAdministrativos', [])):
            trat_id = f"{item_id}_{idx}"
            
            trat_row = {
                'id': trat_id,
                'due_item_id': item_id,
                'numero_due': numero_due,
                'item_numero': item.get('numero', 0),
                'mensagem': tratamento.get('mensagem', ''),
                'impeditivoDeEmbarque': tratamento.get('impeditivoDeEmbarque', False),
                'codigoLPCO': tratamento.get('codigoLPCO', ''),
                'situacao': tratamento.get('situacao', '')
            }
            dados_normalizados['due_item_tratamentos_administrativos'].append(trat_row)
            
            # 7. Órgãos dos tratamentos administrativos
            for orgao in tratamento.get('orgaos', []):
                orgao_row = {
                    'tratamento_administrativo_id': trat_id,
                    'due_item_id': item_id,
                    'numero_due': numero_due,
                    'orgao': orgao
                }
                dados_normalizados['due_item_tratamentos_administrativos_orgaos'].append(orgao_row)
        
        # 8. Notas de remessa do item
        for nota_remessa in item.get('itensDaNotaDeRemessa', []):
            nota_row = {
                'due_item_id': item_id,
                'numero_due': numero_due,
                'item_numero': item.get('numero', 0),
                'numeroDoItem': nota_remessa.get('numeroDoItem', 0),
                'chaveDeAcesso': nota_remessa.get('notaFiscal', {}).get('chaveDeAcesso', ''),
                'cfop': nota_remessa.get('cfop', 0),
                'codigoDoProduto': nota_remessa.get('codigoDoProduto', ''),
                'descricao': nota_remessa.get('descricao', ''),
                'quantidadeEstatistica': nota_remessa.get('quantidadeEstatistica', 0),
                'unidadeComercial': nota_remessa.get('unidadeComercial', ''),
                'valorTotalBruto': nota_remessa.get('valorTotalBruto', 0),
                'quantidadeConsumida': nota_remessa.get('quantidadeConsumida', 0),
                'ncm_codigo': nota_remessa.get('ncm', {}).get('codigo', ''),
                'modelo': nota_remessa.get('notaFiscal', {}).get('modelo', ''),
                'serie': nota_remessa.get('notaFiscal', {}).get('serie', 0),
                'numeroDoDocumento': nota_remessa.get('notaFiscal', {}).get('numeroDoDocumento', 0),
                'ufDoEmissor': nota_remessa.get('notaFiscal', {}).get('ufDoEmissor', ''),
                'identificacao_emitente': nota_remessa.get('notaFiscal', {}).get('identificacaoDoEmitente', {}).get('numero', ''),
                'apresentadaParaDespacho': nota_remessa.get('apresentadaParaDespacho', False),
                # Campos adicionais da nota de remessa
                'finalidade': nota_remessa.get('notaFiscal', {}).get('finalidade', ''),
                'quantidadeDeItens': nota_remessa.get('notaFiscal', {}).get('quantidadeDeItens', 0),
                'notaFiscalEletronica': nota_remessa.get('notaFiscal', {}).get('notaFicalEletronica', False),
                'emitente_cnpj': nota_remessa.get('notaFiscal', {}).get('identificacaoDoEmitente', {}).get('cnpj', False),
                'emitente_cpf': nota_remessa.get('notaFiscal', {}).get('identificacaoDoEmitente', {}).get('cpf', False),
                'ncm_descricao': nota_remessa.get('ncm', {}).get('descricao', ''),
                'ncm_unidadeMedidaEstatistica': nota_remessa.get('ncm', {}).get('unidadeMedidaEstatistica', '')
            }
            dados_normalizados['due_item_notas_remessa'].append(nota_row)
    
        # 9. Nota Fiscal de Exportação do item (1:1)
        nf_exportacao = item.get('itemDaNotaFiscalDeExportacao', {})
        if nf_exportacao:
            nf_exp_row = {
                'due_item_id': item_id,
                'numero_due': numero_due,
                'item_numero': item.get('numero', 0),
                'numeroDoItem': nf_exportacao.get('numeroDoItem', 0),
                'chaveDeAcesso': nf_exportacao.get('notaFiscal', {}).get('chaveDeAcesso', ''),
                'modelo': nf_exportacao.get('notaFiscal', {}).get('modelo', ''),
                'serie': nf_exportacao.get('notaFiscal', {}).get('serie', 0),
                'numeroDoDocumento': nf_exportacao.get('notaFiscal', {}).get('numeroDoDocumento', 0),
                'ufDoEmissor': nf_exportacao.get('notaFiscal', {}).get('ufDoEmissor', ''),
                'identificacao_emitente': nf_exportacao.get('notaFiscal', {}).get('identificacaoDoEmitente', {}).get('numero', ''),
                'emitente_cnpj': nf_exportacao.get('notaFiscal', {}).get('identificacaoDoEmitente', {}).get('cnpj', False),
                'emitente_cpf': nf_exportacao.get('notaFiscal', {}).get('identificacaoDoEmitente', {}).get('cpf', False),
                'finalidade': nf_exportacao.get('notaFiscal', {}).get('finalidade', ''),
                'quantidadeDeItens': nf_exportacao.get('notaFiscal', {}).get('quantidadeDeItens', 0),
                'notaFiscalEletronica': nf_exportacao.get('notaFiscal', {}).get('notaFicalEletronica', False),
                'cfop': nf_exportacao.get('cfop', 0),
                'codigoDoProduto': nf_exportacao.get('codigoDoProduto', ''),
                'descricao': nf_exportacao.get('descricao', ''),
                'quantidadeEstatistica': nf_exportacao.get('quantidadeEstatistica', 0),
                'unidadeComercial': nf_exportacao.get('unidadeComercial', ''),
                'valorTotalCalculado': nf_exportacao.get('valorTotalCalculado', 0),
                'ncm_codigo': nf_exportacao.get('ncm', {}).get('codigo', ''),
                'ncm_descricao': nf_exportacao.get('ncm', {}).get('descricao', ''),
                'ncm_unidadeMedidaEstatistica': nf_exportacao.get('ncm', {}).get('unidadeMedidaEstatistica', ''),
                'apresentadaParaDespacho': nf_exportacao.get('apresentadaParaDespacho', False)
            }
            dados_normalizados['due_item_nota_fiscal_exportacao'].append(nf_exp_row)
        
        # 10. Notas Complementares do item
        for idx_nc, nota_compl in enumerate(item.get('itensDeNotaComplementar', [])):
            nc_row = {
                'due_item_id': item_id,
                'numero_due': numero_due,
                'item_numero': item.get('numero', 0),
                'indice': idx_nc,
                'numeroDoItem': nota_compl.get('numeroDoItem', 0),
                'chaveDeAcesso': nota_compl.get('notaFiscal', {}).get('chaveDeAcesso', ''),
                'modelo': nota_compl.get('notaFiscal', {}).get('modelo', ''),
                'serie': nota_compl.get('notaFiscal', {}).get('serie', 0),
                'numeroDoDocumento': nota_compl.get('notaFiscal', {}).get('numeroDoDocumento', 0),
                'ufDoEmissor': nota_compl.get('notaFiscal', {}).get('ufDoEmissor', ''),
                'identificacao_emitente': nota_compl.get('notaFiscal', {}).get('identificacaoDoEmitente', {}).get('numero', ''),
                'cfop': nota_compl.get('cfop', 0),
                'codigoDoProduto': nota_compl.get('codigoDoProduto', ''),
                'descricao': nota_compl.get('descricao', ''),
                'quantidadeEstatistica': nota_compl.get('quantidadeEstatistica', 0),
                'unidadeComercial': nota_compl.get('unidadeComercial', ''),
                'valorTotalBruto': nota_compl.get('valorTotalBruto', 0),
                'ncm_codigo': nota_compl.get('ncm', {}).get('codigo', '')
            }
            dados_normalizados['due_item_notas_complementares'].append(nc_row)
        
        # 11. Atributos do item
        for idx_atr, atributo in enumerate(item.get('atributos', [])):
            atr_row = {
                'due_item_id': item_id,
                'numero_due': numero_due,
                'item_numero': item.get('numero', 0),
                'indice': idx_atr,
                'codigo': atributo.get('codigo', ''),
                'valor': atributo.get('valor', ''),
                'descricao': atributo.get('descricao', '')
            }
            dados_normalizados['due_item_atributos'].append(atr_row)
        
        # 12. Documentos de Importação do item
        for idx_di, doc_imp in enumerate(item.get('documentosImportacao', [])):
            di_row = {
                'due_item_id': item_id,
                'numero_due': numero_due,
                'item_numero': item.get('numero', 0),
                'indice': idx_di,
                'tipo': doc_imp.get('tipo', ''),
                'numero': doc_imp.get('numero', ''),
                'dataRegistro': doc_imp.get('dataRegistro', ''),
                'itemDocumento': doc_imp.get('itemDocumento', 0),
                'quantidadeUtilizada': doc_imp.get('quantidadeUtilizada', 0)
            }
            dados_normalizados['due_item_documentos_importacao'].append(di_row)
        
        # 13. Documentos de Transformação do item
        for idx_dt, doc_transf in enumerate(item.get('documentosDeTransformacao', [])):
            dt_row = {
                'due_item_id': item_id,
                'numero_due': numero_due,
                'item_numero': item.get('numero', 0),
                'indice': idx_dt,
                'tipo': doc_transf.get('tipo', ''),
                'numero': doc_transf.get('numero', ''),
                'dataRegistro': doc_transf.get('dataRegistro', '')
            }
            dados_normalizados['due_item_documentos_transformacao'].append(dt_row)
        
        # 14. Cálculo Tributário - Tratamentos
        calculo_tributario = item.get('calculoTributario', {})
        for idx_tt, trat_trib in enumerate(calculo_tributario.get('tratamentosTributarios', [])):
            tt_row = {
                'due_item_id': item_id,
                'numero_due': numero_due,
                'item_numero': item.get('numero', 0),
                'indice': idx_tt,
                'codigo': trat_trib.get('codigo', ''),
                'descricao': trat_trib.get('descricao', ''),
                'tipo': trat_trib.get('tipo', ''),
                'tributo': trat_trib.get('tributo', '')
            }
            dados_normalizados['due_item_calculo_tributario_tratamentos'].append(tt_row)
        
        # 15. Cálculo Tributário - Quadros de Cálculos
        for idx_qc, quadro in enumerate(calculo_tributario.get('quadroDeCalculos', [])):
            qc_row = {
                'due_item_id': item_id,
                'numero_due': numero_due,
                'item_numero': item.get('numero', 0),
                'indice': idx_qc,
                'tributo': quadro.get('tributo', ''),
                'baseDeCalculo': quadro.get('baseDeCalculo', 0),
                'aliquota': quadro.get('aliquota', 0),
                'valorDevido': quadro.get('valorDevido', 0),
                'valorRecolhido': quadro.get('valorRecolhido', 0),
                'valorCompensado': quadro.get('valorCompensado', 0)
            }
            dados_normalizados['due_item_calculo_tributario_quadros'].append(qc_row)
    
    # 16. Situações da carga
    for situacao in dados_due.get('situacoesDaCarga', []):
        sit_row = {
            'numero_due': numero_due,
            'codigo': situacao.get('codigo', 0),
            'descricao': situacao.get('descricao', ''),
            'cargaOperada': situacao.get('cargaOperada', False)
        }
        dados_normalizados['due_situacoes_carga'].append(sit_row)
    
    # 17. Solicitações
    for solicitacao in dados_due.get('solicitacoes', []):
        sol_row = {
            'numero_due': numero_due,
            'tipoSolicitacao': solicitacao.get('tipoSolicitacao', ''),
            'dataDaSolicitacao': solicitacao.get('dataDaSolicitacao', ''),
            'usuarioResponsavel': solicitacao.get('usuarioResponsavel', ''),
            'codigoDoStatusDaSolicitacao': solicitacao.get('codigoDoStatusDaSolicitacao', 0),
            'statusDaSolicitacao': solicitacao.get('statusDaSolicitacao', ''),
            'dataDeApreciacao': solicitacao.get('dataDeApreciacao', ''),
            'motivo': solicitacao.get('motivo', '')
        }
        dados_normalizados['due_solicitacoes'].append(sol_row)
    
    # 18. Compensações da declaração tributária
    declaracao_tributaria = dados_due.get('declaracaoTributaria', {})
    if debug_mode:
        logger.info(f"   🔍 Processando declaração tributária:")
        logger.info(f"      • Compensações: {len(declaracao_tributaria.get('compensacoes', []))}")
        logger.info(f"      • Recolhimentos: {len(declaracao_tributaria.get('recolhimentos', []))}")
    
    for compensacao in declaracao_tributaria.get('compensacoes', []):
        comp_row = {
            'numero_due': numero_due,
            'dataDoRegistro': compensacao.get('dataDoRegistro', ''),
            'numeroDaDeclaracao': compensacao.get('numeroDaDeclaracao', ''),
            'valorCompensado': compensacao.get('valorCompensado', 0)
        }
        dados_normalizados['due_declaracao_tributaria_compensacoes'].append(comp_row)
        if debug_mode:
            logger.info(f"      ✅ Compensação adicionada: {compensacao.get('numeroDaDeclaracao', 'N/A')}")
    
    # 19. Recolhimentos da declaração tributária
    for recolhimento in declaracao_tributaria.get('recolhimentos', []):
        rec_row = {
            'numero_due': numero_due,
            'dataDoPagamento': recolhimento.get('dataDoPagamento', ''),
            'dataDoRegistro': recolhimento.get('dataDoRegistro', ''),
            'valorDaMulta': recolhimento.get('valorDaMulta', 0),
            'valorDoImpostoRecolhido': recolhimento.get('valorDoImpostoRecolhido', 0),
            'valorDoJurosMora': recolhimento.get('valorDoJurosMora', 0)
        }
        dados_normalizados['due_declaracao_tributaria_recolhimentos'].append(rec_row)
        if debug_mode:
            logger.info(f"      ✅ Recolhimento adicionado: {recolhimento.get('valorDoImpostoRecolhido', 0)}")
    
    # 20. Contestações da declaração tributária
    for idx_cont, contestacao in enumerate(declaracao_tributaria.get('contestacoes', [])):
        cont_row = {
            'numero_due': numero_due,
            'indice': idx_cont,
            'dataDoRegistro': contestacao.get('dataDoRegistro', ''),
            'motivo': contestacao.get('motivo', ''),
            'status': contestacao.get('status', ''),
            'dataDeApreciacao': contestacao.get('dataDeApreciacao', ''),
            'observacao': contestacao.get('observacao', '')
        }
        dados_normalizados['due_declaracao_tributaria_contestacoes'].append(cont_row)
        if debug_mode:
            logger.info(f"      ✅ Contestação adicionada: {contestacao.get('motivo', 'N/A')}")
    
    # 21. Atos Concessórios de Suspensão (Drawback)
    if atos_concessorios and isinstance(atos_concessorios, list):
        if debug_mode:
            logger.info(f"   🔍 Processando atos concessórios de suspensão: {len(atos_concessorios)} registros")
        
        for idx, ato in enumerate(atos_concessorios):
            ato_row = {
                'numero_due': numero_due,
                'ato_numero': ato.get('numero', ''),
                'tipo_codigo': ato.get('tipo', {}).get('codigo', 0),
                'tipo_descricao': ato.get('tipo', {}).get('descricao', ''),
                'item_numero': ato.get('item', {}).get('numero', ''),
                'item_ncm': ato.get('item', {}).get('ncm', ''),
                'beneficiario_cnpj': ato.get('beneficiario', {}).get('cnpj', ''),
                'quantidadeExportada': ato.get('quantidadeExportada', 0),
                'valorComCoberturaCambial': ato.get('valorComCoberturaCambial', 0),
                'valorSemCoberturaCambial': ato.get('valorSemCoberturaCambial', 0),
                'itemDeDUE_numero': ato.get('itemDeDUE', {}).get('numero', ''),
            }
            dados_normalizados['due_atos_concessorios_suspensao'].append(ato_row)
            if debug_mode:
                logger.info(f"      ✅ Ato concessório suspensão adicionado: {ato.get('numero', 'N/A')}")
    elif debug_mode:
        logger.info(f"   ⚠️  Nenhum ato concessório de suspensão encontrado")
    
    # 22. Atos Concessórios de Isenção (Drawback)
    if atos_isencao and isinstance(atos_isencao, list):
        if debug_mode:
            logger.info(f"   🔍 Processando atos concessórios de isenção: {len(atos_isencao)} registros")
        
        for idx, ato in enumerate(atos_isencao):
            ato_row = {
                'numero_due': numero_due,
                'ato_numero': ato.get('numero', ''),
                'tipo_codigo': ato.get('tipo', {}).get('codigo', 0),
                'tipo_descricao': ato.get('tipo', {}).get('descricao', ''),
                'item_numero': ato.get('item', {}).get('numero', ''),
                'item_ncm': ato.get('item', {}).get('ncm', ''),
                'beneficiario_cnpj': ato.get('beneficiario', {}).get('cnpj', ''),
                'quantidadeExportada': ato.get('quantidadeExportada', 0),
                'valorComCoberturaCambial': ato.get('valorComCoberturaCambial', 0),
                'valorSemCoberturaCambial': ato.get('valorSemCoberturaCambial', 0),
                'itemDeDUE_numero': ato.get('itemDeDUE', {}).get('numero', ''),
            }
            dados_normalizados['due_atos_concessorios_isencao'].append(ato_row)
            if debug_mode:
                logger.info(f"      ✅ Ato concessório isenção adicionado: {ato.get('numero', 'N/A')}")
    elif debug_mode:
        logger.info(f"   ⚠️  Nenhum ato concessório de isenção encontrado")
    
    # 23. Exigências Fiscais
    if exigencias_fiscais and isinstance(exigencias_fiscais, list):
        if debug_mode:
            logger.info(f"   🔍 Processando exigências fiscais: {len(exigencias_fiscais)} registros")
        
        for idx, exigencia in enumerate(exigencias_fiscais):
            exigencia_row = {
                'numero_due': numero_due,
                'numero_exigencia': exigencia.get('numero', '') or exigencia.get('numeroExigencia', ''),
                'tipo_exigencia': exigencia.get('tipo', '') or exigencia.get('tipoExigencia', ''),
                'data_criacao': exigencia.get('dataCriacao', '') or exigencia.get('data_criacao', ''),
                'data_limite': exigencia.get('dataLimite', '') or exigencia.get('data_limite', ''),
                'status': exigencia.get('status', ''),
                'orgao_responsavel': exigencia.get('orgaoResponsavel', '') or exigencia.get('orgao_responsavel', ''),
                'descricao': exigencia.get('descricao', ''),
                'valor_exigido': exigencia.get('valorExigido', 0) or exigencia.get('valor_exigido', 0),
                'valor_pago': exigencia.get('valorPago', 0) or exigencia.get('valor_pago', 0),
                'observacoes': exigencia.get('observacoes', '') or exigencia.get('observacao', ''),
            }
            dados_normalizados['due_exigencias_fiscais'].append(exigencia_row)
            if debug_mode:
                logger.info(f"      ✅ Exigência fiscal adicionada: {exigencia.get('numero', 'N/A')}")
    elif debug_mode:
        logger.info(f"   ⚠️  Nenhuma exigência fiscal encontrada")
    
    return dados_normalizados

def consultar_due_completa(numero_due: str, debug_mode: bool = False) -> dict[str, Any] | None:
    """Consulta os dados completos de uma DUE específica"""
    try:
        # Token já deve estar válido - não verificar aqui para evitar autenticações desnecessárias
        # A verificação e renovação é feita apenas centralmente
        
        # URLs alternativas para tentar
        urls_alternativas = [
            f"{URL_DUE_BASE}/numero-da-due/{numero_due}",  # URL correta
            f"{URL_DUE_BASE}/{numero_due}",  # URL alternativa
            f"{URL_DUE_BASE}/detalhes/{numero_due}",  # URL com detalhes
        ]
        
        for i, url_detalhes in enumerate(urls_alternativas):
            try:
                if debug_mode:
                    logger.info(f"🔍 Tentativa {i + 1}: {url_detalhes}")
                
                response = token_manager.request("GET", url_detalhes, headers=token_manager.obter_headers(), timeout=DEFAULT_HTTP_TIMEOUT_SEC)
                
                if response.status_code == 401:
                    if debug_mode:
                        logger.info(f"🔑 Token expirado ao consultar DUE completa: {numero_due}")
                    return {"error": "token_expirado", "numero_due": numero_due}
                
                if response.status_code == 200:
                    dados_completos = response.json()
                    
                    # Debug: verificar estrutura dos dados retornados
                    if dados_completos:
                        if debug_mode:
                            logger.info(f"✅ Dados completos obtidos para DUE {numero_due} (URL {i + 1})")
                            logger.info(f"   • Tipo: {type(dados_completos)}")
                            if isinstance(dados_completos, dict):
                                logger.info(f"   • Campos: {list(dados_completos.keys())}")
                                logger.info(f"   • Tem itens: {'itens' in dados_completos}")
                                logger.info(f"   • Tem eventos: {'eventosDoHistorico' in dados_completos}")
                        return dados_completos
                    else:
                        if debug_mode:
                            logger.info(f"⚠️  Dados completos vazios para DUE {numero_due} (URL {i + 1})")
                else:
                    if debug_mode:
                        logger.info(f"❌ Status {response.status_code} para URL {i + 1}")
                        
            except requests.exceptions.HTTPError as e:
                if debug_mode:
                    logger.info(f"❌ Erro HTTP {e.response.status_code} para URL {i + 1}")
                continue
            except Exception as e:
                if debug_mode:
                    logger.info(f"❌ Erro para URL {i + 1}: {str(e)[:50]}")
                continue
        
        # Se todas as URLs falharam
        if debug_mode:
            logger.info(f"❌ Todas as URLs falharam para DUE {numero_due}")
        return None
        
    except Exception as e:
        if debug_mode:
            logger.info(f"❌ Erro inesperado ao consultar DUE {numero_due}: {str(e)}")
        return None

def consultar_due_por_nf(chave_nf: str, debug_mode: bool = False) -> dict[str, Any] | None:
    """
    Consulta DU-E pela chave da NF e obtém dados completos
    
    OTIMIZAÇÕES IMPLEMENTADAS:
    • Removidas verificações desnecessárias de token_valido() 
    • Token gerenciado centralmente com cache persistente
    • Evita terceira consulta quando dados da segunda são suficientes
    • Reduz de 3 para 2 requisições HTTP na maioria dos casos (33% menos calls)
    """
    try:
        
        # Token já deve estar válido - não verificar aqui para evitar autenticações desnecessárias
        # A verificação e renovação é feita apenas centralmente
        
        # Primeira consulta: obter link da DU-E
        url_primeira = f"{URL_DUE_BASE}?nota-fiscal={chave_nf}"
        
        response1 = token_manager.request("GET", url_primeira, headers=token_manager.obter_headers(), timeout=DEFAULT_HTTP_TIMEOUT_SEC)
        
        if response1.status_code == 401:
            if debug_mode:
                logger.info(f"🔑 Token expirado na primeira consulta")
            return {"error": "token_expirado", "chave": chave_nf}
        
        if response1.status_code == 422:
            if debug_mode:
                logger.info(f"⚠️  Erro 422 - Possível rate limiting")
            return None
        
        response1.raise_for_status()
        dados1 = response1.json()
        
        if debug_mode:
            logger.info(f"   Response type: {type(dados1)}")
            logger.info(f"   Response length: {len(dados1) if isinstance(dados1, list) else 'Not a list'}")
        
        if not dados1 or len(dados1) == 0:
            if debug_mode:
                logger.info(f"⚠️  Primeira consulta retornou dados vazios")
            return None  # Sem DU-E encontrada
        
        # Extrair dados da primeira resposta
        primeiro_item = dados1[0]
        numero_due = primeiro_item.get('rel', '')
        href_due = primeiro_item.get('href', '')
        
        if debug_mode:
            logger.info(f"   Número DUE: {numero_due}")
            logger.info(f"   HREF DUE: {href_due}")
        
        if not href_due:
            if debug_mode:
                logger.info(f"⚠️  HREF não encontrado no primeiro item")
            return None  # Link não encontrado
        
        # Segunda consulta: obter detalhes básicos da DU-E
        response2 = token_manager.request("GET", href_due, headers=token_manager.obter_headers(), timeout=DEFAULT_HTTP_TIMEOUT_SEC)
        
        if response2.status_code == 401:
            return {"error": "token_expirado", "chave": chave_nf}
        
        response2.raise_for_status()
        dados2 = response2.json()
        
        # Verificar se já temos dados suficientes na segunda consulta
        if debug_mode:
            logger.info(f"📋 Dados da segunda consulta:")
            logger.info(f"   • Campos: {list(dados2.keys()) if isinstance(dados2, dict) else 'Não é dict'}")
            logger.info(f"   • Tem itens: {'itens' in dados2 if isinstance(dados2, dict) else 'N/A'}")
            logger.info(f"   • Tem eventos: {'eventosDoHistorico' in dados2 if isinstance(dados2, dict) else 'N/A'}")
            if isinstance(dados2, dict) and 'itens' in dados2:
                logger.info(f"   • Quantidade de itens: {len(dados2['itens'])}")
        
        # OTIMIZAÇÃO: Usar dados da segunda consulta como completos - evitar terceira consulta
        dados_completos = dados2
        
        # Consultar atos concessórios de suspensão se disponível
        # OTIMIZAÇÃO: Esta consulta adicional é mantida pois é específica para drawback
        atos_concessorios = None
        link_atos_suspensao = dados_completos.get('atosConcessoriosSuspensao', {})
        if isinstance(link_atos_suspensao, dict) and link_atos_suspensao.get('href'):
            url_atos = link_atos_suspensao['href']
            if debug_mode:
                logger.info(f"🔍 Link para atos concessórios encontrado: {url_atos}")
            
            try:
                atos_response = token_manager.request("GET", url_atos, headers=token_manager.obter_headers(), timeout=DEFAULT_HTTP_TIMEOUT_SEC)
                if atos_response.status_code == 200:
                    atos_concessorios = atos_response.json()
                    if debug_mode and atos_concessorios and isinstance(atos_concessorios, list):
                        logger.info(f"✅ {len(atos_concessorios)} atos concessórios obtidos")
            except Exception as e:
                if debug_mode:
                    logger.info(f"⚠️  Erro ao consultar atos concessórios: {e}")
        elif debug_mode:
            logger.info(f"⚠️  Nenhum link para atos concessórios de suspensão encontrado")
        
        # OTIMIZAÇÃO: Reduzir terceiras consultas desnecessárias
        # A segunda consulta já contém todos os dados necessários na maioria dos casos
        # Só fazer terceira consulta em casos MUITO específicos de dados incompletos
        
        consulta_adicional_necessaria = False
        if not dados_completos or not isinstance(dados_completos, dict):
            consulta_adicional_necessaria = True
            motivo = "dados_completos inválidos"
        elif len(dados_completos.get('itens', [])) == 0 and dados_completos.get('tipo', '') != 'SIMPLIFICADA':
            # Só consultar novamente se não tem itens E não é DUE simplificada
            consulta_adicional_necessaria = True
            motivo = "sem itens em DUE não-simplificada"
        
        if consulta_adicional_necessaria:
            if debug_mode:
                logger.info(f"🔄 Terceira consulta necessária: {motivo}")
            
            try:
                dados_terceira_consulta = consultar_due_completa(numero_due, debug_mode)
                
                if dados_terceira_consulta and isinstance(dados_terceira_consulta, dict):
                    if debug_mode:
                        logger.info(f"✅ Dados da terceira consulta obtidos com sucesso")
                    dados_completos = dados_terceira_consulta
                elif debug_mode:
                    logger.info(f"⚠️  Terceira consulta falhou - mantendo dados da segunda")
            except Exception as e:
                if debug_mode:
                    logger.info(f"⚠️  Erro na terceira consulta: {e}")
        elif debug_mode:
            logger.info(f"✅ Segunda consulta suficiente - POUPANDO uma requisição HTTP!")
        
        # Resultado básico para CSV principal (usando dados_completos ao invés de dados2)
        resultado_basico = {
            'Chave NF': chave_nf,
            'DU-E': numero_due,
            'canal': dados_completos.get('canal', ''),
            'chaveDeAcesso': dados_completos.get('chaveDeAcesso', ''),
            'situacao': dados_completos.get('situacao', ''),
            'valorTotalMercadoria': dados_completos.get('valorTotalMercadoria', 0)
        }
        
        # Processar dados completos para normalização
        if dados_completos and isinstance(dados_completos, dict):
            if debug_mode:
                qtd_itens = len(dados_completos.get('itens', []))
                qtd_eventos = len(dados_completos.get('eventosDoHistorico', []))
                logger.info(f"📊 Processando dados completos - DUE: {numero_due} ({qtd_itens} itens, {qtd_eventos} eventos)")
            
            dados_normalizados = processar_dados_due(dados_completos, atos_concessorios, debug_mode)
            if dados_normalizados:
                resultado_basico['dados_completos'] = dados_normalizados
                if debug_mode:
                    total_registros = sum(len(dados) for dados in dados_normalizados.values())
                    logger.info(f"✅ Dados normalizados: {total_registros} registros totais para DUE: {numero_due}")
            else:
                if debug_mode:
                    logger.info(f"⚠️  Falha ao processar dados normalizados para DUE: {numero_due}")
        else:
            if debug_mode:
                logger.info(f"⚠️  Dados completos inválidos ou ausentes para DUE: {numero_due}")
        
        return resultado_basico
        
    except requests.exceptions.Timeout:
        return None  # Timeout silencioso para não poluir logs
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return None  # DU-E não encontrada
        else:
            return None  # Outros erros HTTP
    except Exception:
        return None  # Erro genérico

def consultar_due_por_numero(
    chave_nf: str,
    numero_due: str,
    debug_mode: bool = False,
) -> dict[str, Any] | None:
    """
    Consulta DU-E diretamente pelo número quando já conhecemos a DUE
    
    OTIMIZAÇÃO: Pula a primeira consulta (/due/api/ext/due?nota-fiscal=)
    e vai direto para a segunda (/due/api/ext/due/numero-da-due/)
    """
    try:
        if debug_mode:
            logger.info(f"🚀 [OTIMIZAÇÃO] Consultando DUE {numero_due} diretamente (pulando primeira consulta)")
        
        # Ir direto para a segunda consulta - dados completos da DUE
        url_due = f"{URL_DUE_BASE}/numero-da-due/{numero_due}"
        response = token_manager.request("GET", url_due, headers=token_manager.obter_headers(), timeout=DEFAULT_HTTP_TIMEOUT_SEC)
        
        if response.status_code == 401:
            return {"error": "token_expirado", "chave": chave_nf}
        
        if response.status_code == 422:
            if debug_mode:
                logger.info(f"⚠️  Rate limiting (422) na consulta direta da DUE {numero_due}")
            return None
        
        response.raise_for_status()
        dados_due = response.json()
        
        if not dados_due or not isinstance(dados_due, dict):
            if debug_mode:
                logger.info(f"⚠️  Dados da DUE {numero_due} inválidos ou vazios")
            return None
        
        # Verificar se temos dados suficientes
        if debug_mode:
            logger.info(f"📋 Dados da consulta direta:")
            logger.info(f"   • Campos: {list(dados_due.keys()) if isinstance(dados_due, dict) else 'Não é dict'}")
            logger.info(f"   • Tem itens: {'itens' in dados_due if isinstance(dados_due, dict) else 'N/A'}")
            logger.info(f"   • Tem eventos: {'eventosDoHistorico' in dados_due if isinstance(dados_due, dict) else 'N/A'}")
            if isinstance(dados_due, dict) and 'itens' in dados_due:
                logger.info(f"   • Quantidade de itens: {len(dados_due['itens'])}")
        
        # Consultar atos concessórios de suspensão se disponível
        atos_concessorios = None
        if numero_due:
            link_atos_suspensao = f"{URL_DUE_BASE}/{numero_due}/drawback/suspensao/atos-concessorios"
            try:
                if debug_mode:
                    logger.info(f"🔍 Link para atos concessórios encontrado: {link_atos_suspensao}")
                
                response_atos = token_manager.request("GET", link_atos_suspensao, headers=token_manager.obter_headers(), timeout=DEFAULT_HTTP_TIMEOUT_SEC)
                if response_atos.status_code == 200:
                    atos_concessorios = response_atos.json()
                    if atos_concessorios and len(atos_concessorios) > 0:
                        if debug_mode:
                            logger.info(f"✅ {len(atos_concessorios)} atos concessórios obtidos")
                    else:
                        if debug_mode:
                            logger.info(f"⚠️  Nenhum ato concessório de suspensão encontrado")
                        atos_concessorios = None
                else:
                    if debug_mode:
                        logger.info(f"⚠️  Erro {response_atos.status_code} ao consultar atos concessórios")
                    atos_concessorios = None
            except Exception as e:
                if debug_mode:
                    logger.info(f"⚠️  Erro ao consultar atos concessórios: {str(e)[:50]}")
                atos_concessorios = None
        
        # Usar dados da consulta direta como completos
        dados_completos = dados_due
        
        # OTIMIZAÇÃO: Consulta otimizada - apenas 1 requisição ao invés de 2 (ou 3)
        if debug_mode:
            logger.info(f"✅ Consulta direta suficiente - ECONOMIA de 1 requisição HTTP!")
        
        # Resultado básico para due-siscomex.csv
        resultado_basico = {
            'Chave NF': chave_nf,
            'DU-E': numero_due,
            'canal': dados_completos.get('canal', ''),
            'chaveDeAcesso': dados_completos.get('chaveDeAcesso', ''),
            'situacao': dados_completos.get('situacao', ''),
            'valorTotalMercadoria': dados_completos.get('valorTotalMercadoria', '')
        }
        
        # Processar dados completos para normalização
        if dados_completos and isinstance(dados_completos, dict):
            if debug_mode:
                qtd_itens = len(dados_completos.get('itens', []))
                qtd_eventos = len(dados_completos.get('eventosDoHistorico', []))
                logger.info(f"📊 Processando dados completos - DUE: {numero_due} ({qtd_itens} itens, {qtd_eventos} eventos)")
            
            dados_normalizados = processar_dados_due(dados_completos, atos_concessorios, debug_mode)
            if dados_normalizados:
                resultado_basico['dados_completos'] = dados_normalizados
                if debug_mode:
                    total_registros = sum(len(dados) for dados in dados_normalizados.values())
                    logger.info(f"✅ Dados normalizados: {total_registros} registros totais para DUE: {numero_due}")
            else:
                if debug_mode:
                    logger.info(f"⚠️  Falha ao processar dados normalizados para DUE: {numero_due}")
        else:
            if debug_mode:
                logger.info(f"⚠️  Dados completos inválidos ou ausentes para DUE: {numero_due}")
        
        return resultado_basico
        
    except requests.exceptions.Timeout:
        return None  # Timeout silencioso para não poluir logs
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return None  # DU-E não encontrada
        else:
            return None  # Outros erros HTTP
    except Exception:
        return None  # Erro genérico

def processar_chave_individual(args: tuple) -> dict[str, Any] | None:
    """Processa uma única chave NF - função para ThreadPoolExecutor COM CACHE TRIPLO"""
    chave_nf, debug_mode, cache_nf_due, cache_chaves_nf, cache_dues, cache_lock = args
    
    if debug_mode:
        logger.info(f"🔍 [THREAD] Iniciando processamento da chave {chave_nf[:20]}...")
    
    # CACHE PERSISTENTE: Verificar se já conhecemos a DUE desta chave NF
    numero_due = None
    with cache_lock:
        if chave_nf in cache_nf_due:
            numero_due = cache_nf_due[chave_nf]
            if debug_mode:
                logger.info(f"💾 [CACHE-PERSISTENTE] Chave {chave_nf[:20]} → DUE {numero_due} (arquivo existente)")
    
    # Se não conhecemos a DUE, fazer primeira consulta para descobrir
    if not numero_due:
        try:
            # Fazer apenas a primeira consulta para obter o número da DUE
            url_primeira = f"{URL_DUE_BASE}?nota-fiscal={chave_nf}"
            response1 = token_manager.request("GET", url_primeira, headers=token_manager.obter_headers(), timeout=DEFAULT_HTTP_TIMEOUT_SEC)
            
            if response1.status_code == 401:
                return {"error": "token_expirado", "chave": chave_nf}
            
            if response1.status_code != 200:
                if response1.status_code == 422:
                    # Rate limiting - não é erro de token
                    if debug_mode:
                        logger.info(f"⚠️  [THREAD] Rate limiting (422) na consulta da chave {chave_nf[:20]}")
                    return None  # Retornar None para rate limiting, não erro de token
                elif response1.status_code == 401:
                    # Token expirado
                    return {"error": "token_expirado", "chave": chave_nf}
                else:
                    if debug_mode:
                        logger.info(f"⚠️  [THREAD] Erro {response1.status_code} na consulta da chave {chave_nf[:20]}")
                    return None
            
            dados1 = response1.json()
            if not dados1 or len(dados1) == 0:
                if debug_mode:
                    logger.info(f"⚠️  [THREAD] Sem DUE encontrada para chave {chave_nf[:20]}")
                return None
            
            # Extrair número da DUE da primeira consulta
            numero_due = dados1[0].get('rel', '')
            if not numero_due:
                if debug_mode:
                    logger.info(f"⚠️  [THREAD] Número da DUE não encontrado na resposta para {chave_nf[:20]}")
                return None
            
            # Salvar no cache persistente para futuras execuções
            with cache_lock:
                cache_nf_due[chave_nf] = numero_due
                if debug_mode:
                    logger.info(f"💾 [CACHE-PERSISTENTE] Nova relação salva: {chave_nf[:20]} → {numero_due}")
                    
        except Exception as e:
            if debug_mode:
                logger.info(f"❌ [THREAD] Erro na primeira consulta para {chave_nf[:20]}: {str(e)[:50]}")
            return None
    # Agora temos o numero_due (do cache ou da consulta)
    # CACHE 1: Verificar se a chave NF já foi processada
    with cache_lock:
        if chave_nf in cache_chaves_nf:
            if debug_mode:
                logger.info(f"✅ [CACHE-NF] Chave {chave_nf[:20]} já processada - reutilizando dados")
            
            return cache_chaves_nf[chave_nf].copy()
    
    # CACHE 2: Verificar se a DUE já foi consultada (de outra chave NF)
    with cache_lock:
        if numero_due in cache_dues:
            if debug_mode:
                logger.info(f"✅ [CACHE-DUE] DUE {numero_due} já consultada - reutilizando dados")
            
            # Reutilizar dados da DUE, mas ajustar a chave NF
            resultado_due = cache_dues[numero_due].copy()
            resultado_due['Chave NF'] = chave_nf  # Atualizar chave NF
            
            # Salvar no cache de chaves também
            cache_chaves_nf[chave_nf] = resultado_due.copy()
            
            return resultado_due
        
    # Se não está no cache, fazer consulta completa
    try:
        # OTIMIZAÇÃO: Se já conhecemos o número da DUE, pular primeira consulta
        if numero_due:
            resultado = consultar_due_por_numero(chave_nf, numero_due, debug_mode)
        else:
            resultado = consultar_due_por_nf(chave_nf, debug_mode)
        
        # Se token expirado, retornar marcador especial para reautenticação central
        if isinstance(resultado, dict) and resultado.get("error") == "token_expirado":
            return {"error": "token_expirado", "chave": chave_nf}
        
        # Se sucesso, adicionar aos dois caches
        if resultado and isinstance(resultado, dict) and 'DU-E' in resultado:
            with cache_lock:
                # Cache por chave NF
                cache_chaves_nf[chave_nf] = resultado.copy()
                # Cache por número DUE
                cache_dues[numero_due] = resultado.copy()
                if debug_mode:
                    logger.info(f"📦 [CACHE] Chave {chave_nf[:20]} e DUE {numero_due} adicionadas ao cache")
        
        return resultado
        
    except Exception as e:
        if debug_mode:
            logger.info(f"❌ [THREAD] Erro no processamento da chave {chave_nf[:20]}: {str(e)[:50]}")
        return None

def carregar_cache_due_siscomex(arquivo: str = 'dados/due-siscomex.csv') -> dict[str, str]:
    """Carrega cache de chaves NF -> DUE do arquivo due-siscomex.csv existente"""
    cache_nf_due = {}
    
    if not os.path.exists(arquivo):
        logger.info("📄 Arquivo due-siscomex.csv não encontrado - processamento completo será necessário")
        return cache_nf_due
    
    try:
        df = pd.read_csv(arquivo, sep=';', encoding='utf-8-sig')
        
        if 'Chave NF' in df.columns and 'DU-E' in df.columns:
            for _, row in df.iterrows():
                chave_nf = str(row['Chave NF']).strip()
                numero_due = str(row['DU-E']).strip()
                if chave_nf and numero_due:
                    cache_nf_due[chave_nf] = numero_due
            
            logger.info(f"📋 Cache carregado: {len(cache_nf_due)} relações Chave NF → DUE do arquivo existente")
        else:
            logger.info("⚠️  Arquivo due-siscomex.csv existe mas não tem as colunas esperadas")
            
    except Exception as e:
        logger.info(f"⚠️  Erro ao carregar cache do due-siscomex.csv: {e}")
    
    return cache_nf_due

def processar_chaves_nf(
    chaves_nf: list[str],
    client_id: str,
    client_secret: str,
) -> list[dict[str, Any]]:
    """
    Processa todas as chaves de NF com paralelização otimizada - OTIMIZADO PARA 1 TOKEN APENAS
    
    OTIMIZAÇÕES IMPLEMENTADAS:
    • Uma única autenticação no início (evita múltiplas calls para /autenticar)
    • Token compartilhado entre todas as threads via SharedTokenManager singleton  
    • Cache persistente de token (60min padrão Siscomex, margem 5min)
    • Cache persistente de chaves NF → DUE (do arquivo due-siscomex.csv)
    • Cache de DUEs consultadas para evitar duplicações na mesma execução
    • Pular primeira consulta quando DUE já é conhecida (50% menos requests)
    • Remoção de verificações token_valido() nas funções individuais
    • Processamento paralelo mais agressivo (até 10 workers)
    • Tratamento centralizado de tokens expirados (renovação única)
    • Rate limiting inteligente e timeouts otimizados
    """
    
    logger.info("🔧 Iniciando processamento das chaves...")
    
    # Cache triplo para máxima eficiência
    cache_nf_due = carregar_cache_due_siscomex()  # Cache persistente: chave NF → número DUE
    cache_chaves_nf = {}  # Cache por chave NF (evita duplicatas da mesma chave)
    cache_dues = {}       # Cache por número DUE (evita consultas da mesma DUE)
    lock_cache = threading.Lock()
    
    # Configurar credenciais no token manager compartilhado
    logger.info("🔧 Configurando credenciais...")
    token_manager.configurar_credenciais(client_id, client_secret)
    
    # AUTENTICAÇÃO ÚNICA E INICIAL COM CACHE PERSISTENTE
    logger.info("🔧 Verificando autenticação (cache + nova se necessário)...")
    try:
        # Tentar usar cache primeiro, depois autenticar se necessário
        auth_success = token_manager.autenticar()
        
        if not auth_success:
            logger.info("❌ Falha na autenticação inicial")
            return [], {}
        
        logger.info(f"✅ Autenticação pronta! {token_manager.status_token()}")
        logger.info(f"🚀 Otimização ativa: 2 consultas por DUE (ao invés de 3)")
        
    except Exception as e:
        logger.info(f"❌ Erro na autenticação: {e}")
        return [], {}
    
    resultados = []
    dados_normalizados_consolidados = {
        'due_principal': [],
        'due_eventos_historico': [],
        'due_itens': [],
        'due_item_enquadramentos': [],
        'due_item_paises_destino': [],
        'due_item_tratamentos_administrativos': [],
        'due_item_tratamentos_administrativos_orgaos': [],
        'due_item_notas_remessa': [],
        'due_item_nota_fiscal_exportacao': [],
        'due_item_notas_complementares': [],
        'due_item_atributos': [],
        'due_item_documentos_importacao': [],
        'due_item_documentos_transformacao': [],
        'due_item_calculo_tributario_tratamentos': [],
        'due_item_calculo_tributario_quadros': [],
        'due_situacoes_carga': [],
        'due_solicitacoes': [],
        'due_declaracao_tributaria_compensacoes': [],
        'due_declaracao_tributaria_recolhimentos': [],
        'due_declaracao_tributaria_contestacoes': [],
        'due_atos_concessorios_suspensao': []
    }
    
    # Cache para evitar normalizar a mesma DUE múltiplas vezes
    dues_normalizadas = set()
    
    total_chaves = len(chaves_nf)
    processados = 0
    sucessos = 0
    tokens_expirados = []
    
    logger.info(f"\n🚀 Processando {total_chaves} chaves de NF em paralelo...")
    logger.info("=" * 60)
    
    # Configurar número de workers (otimizado para performance máxima)
    max_workers = min(10, max(3, total_chaves // 30))  # Performance máxima
    logger.info(f"🔧 Configurando {max_workers} workers para processamento paralelo...")
    
    # Preparar argumentos (debug apenas para as primeiras 3) + caches compartilhados
    args_list = [(chave, i < 3, cache_nf_due, cache_chaves_nf, cache_dues, lock_cache) for i, chave in enumerate(chaves_nf)]
    
    # Processar em lotes paralelos
    logger.info("🔧 Iniciando ThreadPoolExecutor...")
    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            logger.info("✅ ThreadPoolExecutor iniciado!")
            
            # Submeter tarefas
            future_to_chave = {
                executor.submit(processar_chave_individual, args): args[0] 
                for args in args_list
            }
            logger.info(f"✅ {len(future_to_chave)} tarefas submetidas!")
            
            # Processar resultados
            for future in as_completed(future_to_chave, timeout=600):  # 10 minutos timeout total
                chave = future_to_chave[future]
                processados += 1
                
                try:
                    resultado = future.result(timeout=60)  # 1 minuto por tarefa
                    
                    # Verificar se token expirou (raro com token único bem gerenciado)
                    if isinstance(resultado, dict) and resultado.get("error") == "token_expirado":
                        tokens_expirados.append(chave)
                        logger.info(f"[{processados:3d}/{total_chaves}] 🔄 {chave[:20]}... → Token expirado (inesperado!)")
                    elif resultado and isinstance(resultado, dict) and 'DU-E' in resultado:
                        # Adicionar resultado básico
                        resultado_basico = {k: v for k, v in resultado.items() if k != 'dados_completos'}
                        resultados.append(resultado_basico)
                        
                        # Consolidar dados normalizados (evitar duplicação por DUE)
                        dados_completos = resultado.get('dados_completos')
                        numero_due = resultado.get('DU-E')
                        
                        if dados_completos and numero_due and numero_due not in dues_normalizadas:
                            # Primeira vez que processamos esta DUE - adicionar dados normalizados
                            for tabela, dados in dados_completos.items():
                                dados_normalizados_consolidados[tabela].extend(dados)
                            
                            # Marcar DUE como já normalizada
                            dues_normalizadas.add(numero_due)
                        
                        sucessos += 1
                        logger.info(f"[{processados:3d}/{total_chaves}] ✅ {chave[:20]}... → DU-E: {resultado['DU-E']} | Canal: {resultado['canal']}")
                    else:
                        logger.info(f"[{processados:3d}/{total_chaves}] ⚠️  {chave[:20]}... → Sem DU-E")
                        
                except Exception as e:
                    logger.info(f"[{processados:3d}/{total_chaves}] ❌ {chave[:20]}... → Erro: {str(e)[:30]}")
                
                # Progress a cada 50 (menos frequente)
                if processados % 50 == 0:
                    percentual = (processados / total_chaves) * 100
                    logger.info(f"    💫 {percentual:.1f}% ({sucessos}/{processados}) - {token_manager.status_token()}")
                    
                    # Só mostrar se há problemas
                    if len(tokens_expirados) > 0:
                        logger.info(f"         ⚠️  Tokens expirados: {len(tokens_expirados)}")
                    
    except Exception as e:
        logger.info(f"❌ Erro no ThreadPoolExecutor: {e}")
        logger.info("🔄 Mudando para processamento sequencial com o mesmo token...")
        # Fallback sequencial simplificado com mesmo token
        return processar_sequencial_simples(chaves_nf, dados_normalizados_consolidados)
    
    # Reprocessar tokens expirados se houver (COM AUTENTICAÇÃO ÚNCIA)
    if tokens_expirados:
        logger.info(f"\n🔄 Reprocessando {len(tokens_expirados)} chaves com token expirado...")
        logger.info("🔑 Realizando nova autenticação para tokens expirados...")
        
        # APENAS UMA autenticação para todos os tokens expirados
        if token_manager.autenticar():
            logger.info(f"✅ Token renovado! Processando {len(tokens_expirados)} chaves...")
            
            for chave in tokens_expirados:
                resultado = consultar_due_por_nf(chave, False)
                if resultado and isinstance(resultado, dict) and 'DU-E' in resultado:
                    resultado_basico = {k: v for k, v in resultado.items() if k != 'dados_completos'}
                    resultados.append(resultado_basico)
                    
                    dados_completos = resultado.get('dados_completos')
                    if dados_completos:
                        for tabela, dados in dados_completos.items():
                            dados_normalizados_consolidados[tabela].extend(dados)
                    
                    sucessos += 1
                    logger.info(f"    ✅ {chave[:20]}... → DU-E: {resultado['DU-E']}")
                time.sleep(0.2)  # Delay reduzido
        else:
            logger.info("❌ Falha na renovação do token - chaves não reprocessadas")
    
    logger.info("=" * 60)
    logger.info(f"✅ Processamento concluído: {len(resultados)}/{total_chaves} sucessos")
    
    # Estatísticas dos caches
    chaves_cache_persistente = len([chave for chave in chaves_nf if chave in cache_nf_due])
    logger.info(f"💾 Cache persistente: {chaves_cache_persistente} relações Chave NF → DUE reutilizadas")
    logger.info(f"📦 Cache de chaves NF: {len(cache_chaves_nf)} chaves únicas processadas")
    logger.info(f"📦 Cache de DUEs: {len(cache_dues)} DUEs únicas consultadas")
    logger.info(f"📊 DUEs normalizadas: {len(dues_normalizadas)} DUEs únicas nos arquivos normalizados")
    
    # Economia de consultas (cache de DUEs + cache persistente)
    total_consultas_evitadas = total_chaves - len(cache_dues)
    if total_consultas_evitadas > 0:
        percentual_economia = (total_consultas_evitadas / total_chaves) * 100
        logger.info(f"🚀 Economia de consultas: {total_consultas_evitadas} evitadas ({percentual_economia:.1f}%)")
    
    # Economia de primeira consulta (cache persistente)
    if chaves_cache_persistente > 0:
        logger.info(f"⚡ Economia de primeira consulta: {chaves_cache_persistente} chaves pularam primeira API")
    
    # Economia de normalização (duplicatas)
    total_normalizacoes_evitadas = len(cache_dues) - len(dues_normalizadas)
    if total_normalizacoes_evitadas > 0:
        logger.info(f"🎯 Economia de normalização: {total_normalizacoes_evitadas} DUEs não duplicadas nos arquivos")
    
    return resultados, dados_normalizados_consolidados

def processar_sequencial_simples(
    chaves_nf: list[str],
    dados_normalizados_consolidados: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Fallback para processamento sequencial quando o paralelo falha"""
    logger.info("🔄 Executando processamento sequencial como fallback...")
    
    resultados = []
    sucessos = 0
    
    for i, chave in enumerate(chaves_nf, 1):
        logger.info(f"[{i:3d}/{len(chaves_nf)}] 🔄 Processando {chave[:20]}...")
        
        try:
            resultado = consultar_due_por_nf(chave, False)
            
            if resultado and isinstance(resultado, dict) and 'DU-E' in resultado:
                resultado_basico = {k: v for k, v in resultado.items() if k != 'dados_completos'}
                resultados.append(resultado_basico)
                
                dados_completos = resultado.get('dados_completos')
                if dados_completos:
                    for tabela, dados in dados_completos.items():
                        dados_normalizados_consolidados[tabela].extend(dados)
                
                sucessos += 1
                logger.info(f"[{i:3d}/{len(chaves_nf)}] ✅ {chave[:20]}... → DU-E: {resultado['DU-E']}")
            else:
                logger.info(f"[{i:3d}/{len(chaves_nf)}] ⚠️  {chave[:20]}... → Sem DU-E")
                
        except Exception as e:
            logger.info(f"[{i:3d}/{len(chaves_nf)}] ❌ {chave[:20]}... → Erro: {str(e)[:30]}")
        
        time.sleep(0.5)  # Delay no sequencial
    
    return resultados, dados_normalizados_consolidados

def salvar_resultados_normalizados(
    dados_normalizados: dict[str, list[dict[str, Any]]],
    pasta: str = 'dados/due-normalizados',
    modo_incremental: bool = True,
) -> None:
    """
    Salva todos os dados normalizados no PostgreSQL.
    
    Args:
        dados_normalizados: Dicionario com dados por tabela
        pasta: Pasta de destino (ignorado, mantido para compatibilidade)
        modo_incremental: Mantido para compatibilidade (sempre faz upsert no PostgreSQL)
    """
    
    if not USAR_POSTGRESQL:
        # Fallback para CSV (codigo antigo)
        _salvar_resultados_normalizados_csv(dados_normalizados, pasta, modo_incremental)
        return
    
    logger.info(f"\n💾 Salvando dados normalizados no PostgreSQL...")
    logger.info("-" * 50)
    
    # Conectar ao banco se nao estiver conectado
    if not db_manager.conn:
        if not db_manager.conectar():
            logger.error("[ERRO] Falha ao conectar ao PostgreSQL, tentando CSV como fallback...")
            _salvar_resultados_normalizados_csv(dados_normalizados, pasta, modo_incremental)
            return
    
    # Contar registros por tabela
    total_registros = 0
    tabelas_salvas = 0
    
    for tabela, dados in dados_normalizados.items():
        if dados:
            logger.info(f"   ✅ {tabela} → {len(dados)} registros")
            total_registros += len(dados)
            tabelas_salvas += 1
        else:
            logger.info(f"   ⚠️  {tabela} → Sem dados")
    
    # Inserir no banco
    if db_manager.inserir_due_completa(dados_normalizados):
        logger.info("-" * 50)
        logger.info(f"📊 {tabelas_salvas} tabelas salvas, {total_registros} registros no PostgreSQL")
    else:
        logger.error("[ERRO] Falha ao salvar no PostgreSQL")


def _salvar_resultados_normalizados_csv(
    dados_normalizados: dict[str, list[dict[str, Any]]],
    pasta: str = 'dados/due-normalizados',
    modo_incremental: bool = True,
) -> None:
    """
    Salva todos os dados normalizados em CSVs separados (fallback).
    """
    
    # Garantir que a pasta existe
    if not os.path.exists(pasta):
        os.makedirs(pasta)
    
    logger.info(f"\n💾 Salvando dados normalizados em: {pasta}")
    logger.info("-" * 50)
    
    # Chaves primarias por tabela para evitar duplicatas
    chaves_primarias = {
        'due_principal': ['numero'],
        'due_eventos_historico': ['numero_due', 'data', 'tipoEvento'],
        'due_itens': ['numero_due', 'numeroItem'],
        'due_item_enquadramentos': ['numero_due', 'numeroItem', 'codigo'],
        'due_item_paises_destino': ['numero_due', 'numeroItem', 'codigoPaisDestino'],
        'due_item_tratamentos_administrativos': ['numero_due', 'numeroItem', 'codigoLPCO'],
        'due_item_tratamentos_administrativos_orgaos': ['numero_due', 'numeroItem', 'codigoLPCO', 'codigoOrgao'],
        'due_item_notas_remessa': ['numero_due', 'numeroItem', 'chaveDeAcesso'],
        'due_item_nota_fiscal_exportacao': ['numero_due', 'chaveDeAcesso'],
        'due_item_notas_complementares': ['numero_due', 'numeroItem', 'chaveDeAcesso'],
        'due_item_atributos': ['numero_due', 'numeroItem', 'codigo'],
        'due_item_documentos_importacao': ['numero_due', 'numeroItem', 'numero'],
        'due_item_documentos_transformacao': ['numero_due', 'numeroItem', 'numero'],
        'due_item_calculo_tributario_tratamentos': ['numero_due', 'numeroItem'],
        'due_item_calculo_tributario_quadros': ['numero_due', 'numeroItem', 'codigoQuadro'],
        'due_situacoes_carga': ['numero_due', 'sequencial'],
        'due_solicitacoes': ['numero_due', 'tipoSolicitacao', 'dataSolicitacao'],
        'due_declaracao_tributaria_compensacoes': ['numero_due', 'codigoReceita'],
        'due_declaracao_tributaria_recolhimentos': ['numero_due', 'codigoReceita'],
        'due_declaracao_tributaria_contestacoes': ['numero_due'],
        'due_atos_concessorios_suspensao': ['numero_due', 'numero']
    }
    
    for tabela, dados in dados_normalizados.items():
        arquivo = os.path.join(pasta, f"{tabela}.csv")
        
        if not dados:
            logger.info(f"   ⚠️  {tabela}.csv → Sem dados novos")
            continue
        
        df_novo = pd.DataFrame(dados)
        df_final = df_novo  # Default
        
        # Se modo incremental e arquivo existe, fazer merge
        if modo_incremental and os.path.exists(arquivo):
            try:
                df_existente = pd.read_csv(arquivo, sep=';', encoding='utf-8-sig')
                chaves = chaves_primarias.get(tabela, ['numero_due'])
                chaves_validas = [c for c in chaves if c in df_novo.columns and c in df_existente.columns]
                
                if chaves_validas:
                    df_existente['_chave_temp'] = df_existente[chaves_validas].astype(str).agg('|'.join, axis=1)
                    df_novo['_chave_temp'] = df_novo[chaves_validas].astype(str).agg('|'.join, axis=1)
                    df_existente = df_existente[~df_existente['_chave_temp'].isin(df_novo['_chave_temp'])]
                    df_existente = df_existente.drop(columns=['_chave_temp'])
                    df_novo = df_novo.drop(columns=['_chave_temp'])
                    df_final = pd.concat([df_existente, df_novo], ignore_index=True)
                else:
                    df_final = pd.concat([df_existente, df_novo], ignore_index=True)
                
                logger.info(f"   ✅ {tabela}.csv → {len(df_novo)} novos + {len(df_existente)} existentes = {len(df_final)} total")
            except Exception as e:
                logger.info(f"   ⚠️  {tabela}.csv → Erro ao fazer merge: {e}, sobrescrevendo")
                df_final = df_novo
        else:
            logger.info(f"   ✅ {tabela}.csv → {len(df_final)} registros")
        
        df_final.to_csv(arquivo, sep=';', index=False, encoding='utf-8-sig')
    
    logger.info("-" * 50)
    logger.info(f"📊 Total de tabelas salvas: {len([t for t, d in dados_normalizados.items() if d])}")


def salvar_resultados(resultados: list[dict[str, Any]], arquivo: str = 'dados/due-siscomex.csv') -> None:
    """Salva os resultados básicos em CSV (compatibilidade)"""
    if not resultados:
        logger.info("⚠️  Nenhum resultado para salvar")
        return
    
    try:
        # Garantir que a pasta existe
        pasta = os.path.dirname(arquivo)
        if pasta and not os.path.exists(pasta):
            os.makedirs(pasta)
        
        # Criar DataFrame e salvar
        df = pd.DataFrame(resultados)
        df.to_csv(arquivo, sep=';', index=False, encoding='utf-8-sig')
        
        logger.info(f"\n💾 Dados básicos salvos em: {arquivo}")
        logger.info(f"   Total de registros: {len(df)}")
        logger.info(f"   Colunas: {', '.join(df.columns.tolist())}")
        
    except Exception as e:
        logger.info(f"❌ Erro ao salvar CSV: {e}")

def testar_normalizacao_due(
    client_id: str,
    client_secret: str,
    primeira_chave: str | None = None,
) -> None:
    """Testa a normalização com apenas uma DU-E para debug"""
    
    # Configurar credenciais no token manager compartilhado
    token_manager.configurar_credenciais(client_id, client_secret)
    
    logger.info("🔑 Realizando autenticação única para teste...")
    if not token_manager.autenticar():
        logger.info("❌ Falha na autenticação para teste")
        return
    
    logger.info(f"✅ Token obtido! Válido até: {token_manager.expiracao.strftime('%H:%M:%S') if token_manager.expiracao else 'N/A'}")
    
    # Usar a primeira chave ou ler do CSV
    if not primeira_chave:
        chaves_nf = ler_chaves_nf()
        if not chaves_nf:
            return
        primeira_chave = chaves_nf[0]
    
    logger.info(f"\n🧪 TESTE DE NORMALIZAÇÃO - Chave: {primeira_chave}")
    logger.info("=" * 60)
    
    # Consultar com debug habilitado
    resultado = consultar_due_por_nf(primeira_chave, debug_mode=True)
    
    if resultado and 'dados_completos' in resultado:
        logger.info("\n✅ Teste de normalização bem-sucedido!")
        dados_normalizados = resultado['dados_completos']
        for tabela, dados in dados_normalizados.items():
            if dados:
                logger.info(f"  • {tabela}: {len(dados)} registros")
    else:
        logger.info("\n❌ Teste de normalização falhou!")
        logger.info("   Verifique os logs acima para identificar o problema")

def main() -> None:
    """Função principal otimizada"""
    logger.info("=" * 70)
    logger.info("CONSULTA DUE SISCOMEX - VERSÃO NORMALIZADA COM ALTA PERFORMANCE")
    logger.info("=" * 70)
    logger.info(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    logger.info("🚀 Funcionalidades:")
    logger.info("   • Processamento paralelo otimizado")
    logger.info("   • Consulta de dados completos da DUE (2-3 requisições por NF)")
    logger.info("   • Normalização em múltiplas tabelas CSV")
    logger.info("   • Consulta de atos concessórios de suspensão (drawback)")
    logger.info("   • Pool de conexões HTTP reutilizáveis")
    logger.info("   • Rate limiting inteligente")
    logger.info("   • Modo de teste para debug")
    logger.info("=" * 70)
    
    # Verificar credenciais de autenticação
    logger.info("🔧 Verificando credenciais...")
    client_id = os.environ.get("SISCOMEX_CLIENT_ID")
    client_secret = os.environ.get("SISCOMEX_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        logger.info("❌ Credenciais do Siscomex não encontradas nas variáveis de ambiente")
        logger.info("Configure as variáveis SISCOMEX_CLIENT_ID e SISCOMEX_CLIENT_SECRET no arquivo .env")
        return
    
    logger.info("✅ Credenciais encontradas!")
    
    # Ler chaves do CSV
    logger.info("🔧 Lendo chaves do CSV...")
    chaves_nf = ler_chaves_nf()
    if not chaves_nf:
        logger.info("❌ Nenhuma chave encontrada - abortando")
        return
    
    logger.info(f"✅ {len(chaves_nf)} chaves carregadas com sucesso!")
    
    # Opções de processamento
    logger.info(f"\n📋 {len(chaves_nf)} chaves de NF encontradas")
    logger.info("📁 Será criado:")
    logger.info("   • due-siscomex.csv (dados básicos)")
    logger.info("   • dados/due-normalizados/ (13 tabelas normalizadas)")
    logger.info("\nOpções:")
    logger.info("  1. Processar todas as chaves (PRODUÇÃO)")
    logger.info("  2. Testar normalização com 1 DU-E (DEBUG)")
    logger.info("  3. Cancelar")
    
    escolha = input("Escolha uma opção (1-3): ").strip()
    
    if escolha == "2":
        logger.info("🧪 Iniciando teste de normalização...")
        testar_normalizacao_due(client_id, client_secret)
        return
    elif escolha != "1":
        logger.info("❌ Processamento cancelado")
        return
    
    # Processar todas as chaves
    logger.info("🚀 Iniciando processamento de todas as chaves...")
    resultados, dados_normalizados = processar_chaves_nf(chaves_nf, client_id, client_secret)
    
    # Salvar resultados
    if resultados:
        # Salvar dados básicos (compatibilidade)
        salvar_resultados(resultados)
        
        # Salvar dados normalizados
        salvar_resultados_normalizados(dados_normalizados)
        
        # Estatísticas finais
        logger.info(f"\n📊 ESTATÍSTICAS FINAIS:")
        logger.info("-" * 50)
        
        # Status final do token
        logger.info(f"🔑 Status do token ao final: {token_manager.status_token()}")
        logger.info("")
        
        df_basico = pd.DataFrame(resultados)
        
        # Canais encontrados
        canais = df_basico['canal'].value_counts()
        logger.info("Canais encontrados:")
        for canal, qtd in canais.items():
            logger.info(f"  - {canal}: {qtd} DU-Es")
        
        # Situações
        if 'situacao' in df_basico.columns:
            situacoes = df_basico['situacao'].value_counts()
            logger.info("\nSituações:")
            for situacao, qtd in situacoes.head(3).items():
                logger.info(f"  - {situacao}: {qtd}")
        
        # Valor total
        valor_total = df_basico['valorTotalMercadoria'].sum()
        logger.info(f"\nValor total das mercadorias: R$ {valor_total:,.2f}")
        logger.info(f"Total de DU-Es processadas: {len(df_basico)}")
        
        # Estatísticas dos dados normalizados
        logger.info(f"\nTabelas normalizadas criadas:")
        total_registros_normalizados = 0
        for tabela, dados in dados_normalizados.items():
            if dados:
                logger.info(f"  - {tabela}: {len(dados)} registros")
                total_registros_normalizados += len(dados)
        
        if total_registros_normalizados == 0:
            logger.info("  ⚠️  NENHUMA tabela normalizada foi criada!")
            logger.info("  💡 Possíveis causas:")
            logger.info("     • API não retorna dados completos")
            logger.info("     • Estrutura JSON diferente do esperado")
            logger.info("     • Problemas na função de processamento")
        else:
            logger.info(f"  ✅ Total de registros normalizados: {total_registros_normalizados}")
        
        # Estatísticas específicas dos atos concessórios
        atos_count = len(dados_normalizados.get('due_atos_concessorios_suspensao', []))
        if atos_count > 0:
            logger.info(f"\n🎯 Atos concessórios de suspensão:")
            logger.info(f"  - Total de registros: {atos_count}")
            
            # Analisar por tipo se houver dados
            df_atos = pd.DataFrame(dados_normalizados['due_atos_concessorios_suspensao'])
            if not df_atos.empty and 'tipo_descricao' in df_atos.columns:
                tipos = df_atos['tipo_descricao'].value_counts()
                for tipo, qtd in tipos.items():
                    logger.info(f"  - {tipo}: {qtd} registros")
        
    logger.info("\n" + "=" * 70)
    logger.info("PROCESSAMENTO FINALIZADO")
    logger.info("=" * 70)

if __name__ == "__main__":
    main()
