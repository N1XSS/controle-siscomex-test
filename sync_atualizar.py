"""
Atualizacao de DUEs Existentes - OTIMIZADO
==========================================

Este servico atualiza os dados das DUEs existentes com verificacao inteligente:
- Ignora DUEs CANCELADAS (nunca atualiza)
- DUEs PENDENTES (EM_CARGA, DESEMBARACADA, etc): atualiza completo
- DUEs AVERBADAS: verifica se dataDeRegistro mudou antes de atualizar

Otimizacoes:
- Compara dataDeRegistro da API com banco para evitar atualizacoes desnecessarias
- Respeita limite de 1000 req/hora do Siscomex
- Pode ser agendado para execucao diaria

Uso:
    python sync_atualizar.py
    python sync_atualizar.py --force  # Atualiza todas independente da data
    python sync_atualizar.py --limit 100  # Limita quantidade de atualizacoes
"""

import os
import sys
import pandas as pd
from datetime import datetime, timedelta
import warnings
from dotenv import load_dotenv
from token_manager import token_manager
from db_manager import db_manager
import time
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import requests

warnings.filterwarnings('ignore')
load_dotenv('config.env')

# Flag para usar PostgreSQL
USAR_POSTGRESQL = True

# URL base da API
URL_DUE_BASE = "https://portalunico.siscomex.gov.br/due/api/ext/due"

# Configuracoes
HORAS_PARA_ATUALIZACAO = 24
MAX_ATUALIZACOES_POR_EXECUCAO = 500
DIAS_AVERBACAO_RECENTE = 7  # DUEs averbadas ha menos de 7 dias: atualiza completo

# Situacoes que NAO devem ser atualizadas
SITUACOES_CANCELADAS = [
    'CANCELADA_POR_EXPIRACAO_DE_PRAZO',
    'CANCELADA_PELA_ADUANA_A_PEDIDO_DO_EXPORTADOR',
    'CANCELADA_PELO_EXPORTADOR',
    'CANCELADA_PELO_SISCOMEX'
]

# Situacoes finais (averbadas) - verificar dataDeRegistro antes de atualizar
SITUACOES_AVERBADAS = [
    'AVERBADA_SEM_DIVERGENCIA',
    'AVERBADA_COM_DIVERGENCIA'
]

# Situacoes pendentes (em andamento) - sempre atualizar
SITUACOES_PENDENTES = [
    'EM_CARGA',
    'DESEMBARACADA',
    'AGUARDANDO_AVERBACAO',
    'EM_ELABORACAO',
    'REGISTRADA',
    'PARAMETRIZADA_VERDE',
    'PARAMETRIZADA_AMARELO',
    'PARAMETRIZADA_VERMELHO',
    'INTERROMPIDA'
]


def carregar_dues_para_verificar(forcar_todas=False, limite=None):
    """
    Carrega lista de DUEs para verificar/atualizar
    
    Retorna dict com:
    - 'pendentes': lista de DUEs que devem ser atualizadas diretamente
    - 'averbadas_recentes': averbadas ha menos de 7 dias (atualizar direto)
    - 'averbadas_antigas': averbadas ha mais de 7 dias (verificar dataDeRegistro)
    """
    if not db_manager.conn:
        db_manager.conectar()
    
    if not db_manager.conn:
        print("[ERRO] Nao foi possivel conectar ao banco de dados")
        return None
    
    resultado = {
        'pendentes': [],
        'averbadas_recentes': [],
        'averbadas_antigas': []
    }
    
    try:
        cur = db_manager.conn.cursor()
        
        agora = datetime.utcnow()
        limite_atualizacao = agora - timedelta(hours=HORAS_PARA_ATUALIZACAO)
        limite_averbacao_recente = agora - timedelta(days=DIAS_AVERBACAO_RECENTE)
        
        if forcar_todas:
            # Modo forcado: todas as DUEs (exceto canceladas)
            cur.execute("""
                SELECT numero, situacao, data_de_registro, data_da_averbacao
                FROM due_principal
                WHERE situacao NOT IN %s
                ORDER BY data_ultima_atualizacao ASC NULLS FIRST
            """, (tuple(SITUACOES_CANCELADAS),))
        else:
            # Modo normal: filtrar por data de atualizacao
            cur.execute("""
                SELECT numero, situacao, data_de_registro, data_da_averbacao
                FROM due_principal
                WHERE situacao NOT IN %s
                  AND (data_ultima_atualizacao IS NULL 
                       OR data_ultima_atualizacao < %s)
                ORDER BY data_ultima_atualizacao ASC NULLS FIRST
            """, (tuple(SITUACOES_CANCELADAS), limite_atualizacao))
        
        rows = cur.fetchall()
        
        for numero, situacao, data_registro, data_averbacao in rows:
            if situacao in SITUACOES_AVERBADAS:
                # Verificar se averbacao foi recente
                if data_averbacao and data_averbacao > limite_averbacao_recente:
                    resultado['averbadas_recentes'].append({
                        'numero': numero,
                        'data_registro_bd': data_registro
                    })
                else:
                    resultado['averbadas_antigas'].append({
                        'numero': numero,
                        'data_registro_bd': data_registro
                    })
            else:
                resultado['pendentes'].append({
                    'numero': numero,
                    'data_registro_bd': data_registro
                })
        
        # Aplicar limite
        limite_final = limite if limite else MAX_ATUALIZACOES_POR_EXECUCAO
        
        total_pendentes = len(resultado['pendentes']) + len(resultado['averbadas_recentes'])
        total_verificar = len(resultado['averbadas_antigas'])
        
        print(f"[INFO] DUEs encontradas:")
        print(f"  - Pendentes (atualizar direto): {len(resultado['pendentes'])}")
        print(f"  - Averbadas recentes (atualizar direto): {len(resultado['averbadas_recentes'])}")
        print(f"  - Averbadas antigas (verificar antes): {len(resultado['averbadas_antigas'])}")
        
        # Limitar as listas
        if total_pendentes + total_verificar > limite_final:
            # Priorizar pendentes
            if len(resultado['pendentes']) > limite_final:
                resultado['pendentes'] = resultado['pendentes'][:limite_final]
                resultado['averbadas_recentes'] = []
                resultado['averbadas_antigas'] = []
            else:
                restante = limite_final - len(resultado['pendentes'])
                if len(resultado['averbadas_recentes']) > restante:
                    resultado['averbadas_recentes'] = resultado['averbadas_recentes'][:restante]
                    resultado['averbadas_antigas'] = []
                else:
                    restante2 = restante - len(resultado['averbadas_recentes'])
                    resultado['averbadas_antigas'] = resultado['averbadas_antigas'][:restante2]
            
            print(f"[INFO] Limitado a {limite_final} DUEs por execucao")
        
        return resultado
        
    except Exception as e:
        print(f"[ERRO] Erro ao carregar DUEs: {e}")
        return None


def verificar_se_due_mudou(numero_due, data_registro_bd):
    """
    Verifica se uma DUE foi modificada comparando dataDeRegistro
    
    Args:
        numero_due: Numero da DUE
        data_registro_bd: Data de registro armazenada no banco
    
    Returns:
        tuple: (mudou: bool, dados_due: dict ou None, mensagem_erro: str ou None)
    """
    try:
        url = f"{URL_DUE_BASE}/numero-da-due/{numero_due}"
        response = token_manager.session.get(url, headers=token_manager.obter_headers(), timeout=10)
        
        if response.status_code == 401:
            return None, None, "Token expirado (401)"
        
        if response.status_code == 404:
            return None, None, f"DUE não encontrada (404)"
        
        if response.status_code == 422:
            return None, None, f"Erro de validação (422) - possível rate limiting"
        
        if response.status_code != 200:
            return None, None, f"Status HTTP {response.status_code}"
        
        dados = response.json()
        data_registro_api_str = dados.get('dataDeRegistro', '')
        
        if not data_registro_api_str:
            return True, dados, None  # Sem data, atualizar por seguranca
        
        # Converter e comparar datas
        try:
            # Formato API: 2026-01-07T11:29:42.000-0300
            data_registro_api = datetime.fromisoformat(data_registro_api_str.replace('-0300', '-03:00').replace('-0200', '-02:00'))
            
            if data_registro_bd:
                # Comparar (ignorando timezone para simplificar)
                data_api_naive = data_registro_api.replace(tzinfo=None)
                data_bd_naive = data_registro_bd.replace(tzinfo=None) if hasattr(data_registro_bd, 'replace') else data_registro_bd
                
                # Se a data da API for mais recente, houve mudanca
                if data_api_naive > data_bd_naive:
                    return True, dados, None
                else:
                    return False, None, None  # Nao mudou
            else:
                return True, dados, None  # Sem data no BD, atualizar
                
        except (ValueError, TypeError) as e:
            return True, dados, None  # Erro na conversao, atualizar por seguranca
            
    except requests.exceptions.Timeout:
        return None, None, "Timeout na requisição"
    except requests.exceptions.ConnectionError:
        return None, None, "Erro de conexão com o servidor"
    except Exception as e:
        return None, None, f"Erro inesperado: {str(e)[:100]}"


def consultar_dados_adicionais(numero_due, dados_due):
    """Consulta dados adicionais de uma DUE (drawback, exigencias)"""
    atos_suspensao = None
    atos_isencao = None
    exigencias_fiscais = None
    
    # Atos de suspensao
    try:
        url = f"{URL_DUE_BASE}/{numero_due}/drawback/suspensao/atos-concessorios"
        response = token_manager.session.get(url, headers=token_manager.obter_headers(), timeout=10)
        if response.status_code == 200:
            atos_suspensao = response.json()
    except:
        pass
    
    # Atos de isencao
    try:
        url = f"{URL_DUE_BASE}/{numero_due}/drawback/isencao/atos-concessorios"
        response = token_manager.session.get(url, headers=token_manager.obter_headers(), timeout=10)
        if response.status_code == 200:
            atos_isencao = response.json()
    except:
        pass
    
    # Exigencias fiscais
    try:
        url = f"{URL_DUE_BASE}/{numero_due}/exigencias-fiscais"
        response = token_manager.session.get(url, headers=token_manager.obter_headers(), timeout=10)
        if response.status_code == 200:
            exigencias_fiscais = response.json()
    except:
        pass
    
    return atos_suspensao, atos_isencao, exigencias_fiscais


def processar_due_averbada_antiga(due_info):
    """
    Processa uma única DUE averbada antiga (thread-safe).
    
    Args:
        due_info: dict com 'numero' e 'data_registro_bd'
    
    Returns:
        dict com resultado: {
            'numero_due': str,
            'mudou': bool ou None,
            'dados_norm': dict ou None,
            'erro': bool
        }
    """
    numero_due = due_info['numero']
    data_registro_bd = due_info['data_registro_bd']
    
    resultado = {
        'numero_due': numero_due,
        'mudou': None,
        'dados_norm': None,
        'erro': False,
        'mensagem_erro': None
    }
    
    try:
        # Verificar se mudou
        mudou, dados_due, mensagem_erro = verificar_se_due_mudou(numero_due, data_registro_bd)
        
        if mudou is None:
            resultado['erro'] = True
            resultado['mensagem_erro'] = mensagem_erro or 'Falha ao verificar DUE (resposta None)'
            return resultado
        
        resultado['mudou'] = mudou
        
        if mudou and dados_due:
            # Houve mudança, processar dados completos
            try:
                from due_processor import processar_dados_due
                atos_susp, atos_isen, exig = consultar_dados_adicionais(numero_due, dados_due)
                dados_norm = processar_dados_due(dados_due, atos_susp, atos_isen, exig)
                resultado['dados_norm'] = dados_norm
            except Exception as e:
                resultado['erro'] = True
                resultado['mensagem_erro'] = f'Erro ao processar dados completos: {str(e)[:100]}'
        
        # Delay para rate limiting (respeitando limite de 1000 req/hora do Siscomex)
        # Com 5 workers e sleep de 0.5s: ~600 req/hora (seguro)
        time.sleep(0.5)
        
    except Exception as e:
        resultado['erro'] = True
        resultado['mensagem_erro'] = f'Erro inesperado: {str(e)[:100]}'
    
    return resultado


def processar_dues_averbadas_antigas_paralelo(dues_info_list, max_workers=8):
    """
    Processa DUEs averbadas antigas em paralelo usando ThreadPoolExecutor.
    
    Args:
        dues_info_list: Lista de dicts com 'numero' e 'data_registro_bd'
        max_workers: Número máximo de threads paralelas (padrão: 8)
    
    Returns:
        tuple: (
            dados_consolidados: dict,
            dues_sem_mudanca: list[str],
            stats: dict
        )
    """
    dados_consolidados = {
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
        'due_atos_concessorios_suspensao': [],
        'due_atos_concessorios_isencao': [],
        'due_exigencias_fiscais': []
    }
    
    dues_sem_mudanca = []
    dues_com_erro = []  # Lista de DUEs com erro e detalhes
    stats = {
        'mudou': 0,
        'sem_mudanca': 0,
        'erros': 0
    }
    
    total = len(dues_info_list)
    processados = 0
    lock = threading.Lock()
    
    # Ajustar max_workers baseado no total (respeitando limite de 1000 req/hora do Siscomex)
    # Cálculo de rate limiting:
    # - Limite Siscomex: 1000 req/hora = ~16.67 req/min = ~0.28 req/s
    # - Cada DUE: 1 req para verificar + até 3 req adicionais se mudou = máximo 4 req/DUE
    # - Na prática: maioria das DUEs não muda (1 req apenas)
    # - Com 5 workers e sleep de 0.5s: cada worker faz ~2 req/s = 10 req/s total
    # - Para 466 DUEs (1 req cada): ~46.6 segundos de processamento
    # - Isso resulta em ~466 req em ~47s = ~600 req/hora (bem abaixo de 1000)
    # - Se algumas DUEs mudarem (4 req cada), ainda fica dentro do limite
    max_workers = min(max_workers, 5, total)
    
    print(f"  [INFO] Processando {total} DUEs com {max_workers} workers paralelos...")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submeter todas as tarefas
        future_to_due = {
            executor.submit(processar_due_averbada_antiga, due_info): due_info
            for due_info in dues_info_list
        }
        
        # Processar resultados conforme completam
        for future in as_completed(future_to_due):
            due_info = future_to_due[future]
            processados += 1
            
            try:
                resultado = future.result(timeout=30)
                
                with lock:
                    if resultado['erro']:
                        stats['erros'] += 1
                        # Armazenar detalhes do erro
                        erro_info = {
                            'numero_due': resultado['numero_due'],
                            'mensagem': resultado.get('mensagem_erro', 'Erro desconhecido')
                        }
                        dues_com_erro.append(erro_info)
                    elif resultado['mudou']:
                        stats['mudou'] += 1
                        if resultado['dados_norm']:
                            # Consolidar dados normalizados
                            for tabela, dados in resultado['dados_norm'].items():
                                if tabela in dados_consolidados:
                                    dados_consolidados[tabela].extend(dados)
                    else:
                        stats['sem_mudanca'] += 1
                        dues_sem_mudanca.append(resultado['numero_due'])
                
                # Progresso a cada 50 DUEs
                if processados % 50 == 0:
                    print(f"  [PROGRESSO] {processados}/{total}...")
                    
            except Exception as e:
                with lock:
                    stats['erros'] += 1
                    # Armazenar erro de timeout ou exceção
                    erro_info = {
                        'numero_due': due_info.get('numero', 'DESCONHECIDA'),
                        'mensagem': f'Timeout ou exceção: {str(e)[:100]}'
                    }
                    dues_com_erro.append(erro_info)
                if processados % 50 == 0:
                    print(f"  [PROGRESSO] {processados}/{total}... (erro: {str(e)[:30]})")
    
    return dados_consolidados, dues_sem_mudanca, stats, dues_com_erro


def atualizar_dues():
    """Processo principal de atualizacao de DUEs"""
    parser = argparse.ArgumentParser(description='Atualizar DUEs existentes')
    parser.add_argument('--force', action='store_true', 
                        help='Forca atualizacao de todas as DUEs')
    parser.add_argument('--limit', type=int, 
                        help='Limite de DUEs para atualizar')
    args = parser.parse_args()
    
    print("=" * 60)
    print("ATUALIZACAO DE DUEs EXISTENTES (OTIMIZADO)")
    print("=" * 60)
    print(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    if args.force:
        print("Modo: FORCADO (todas as DUEs)")
    else:
        print(f"Modo: INCREMENTAL (DUEs > {HORAS_PARA_ATUALIZACAO}h)")
    print("=" * 60)
    print()
    
    # 1. Carregar DUEs classificadas
    dues_info = carregar_dues_para_verificar(
        forcar_todas=args.force, 
        limite=args.limit
    )
    
    if not dues_info:
        print("[ERRO] Nao foi possivel carregar DUEs")
        return
    
    total_dues = (len(dues_info['pendentes']) + 
                  len(dues_info['averbadas_recentes']) + 
                  len(dues_info['averbadas_antigas']))
    
    if total_dues == 0:
        print("[OK] Nenhuma DUE precisa ser atualizada!")
        return
    
    # 2. Autenticar no Siscomex
    print("\n[INFO] Autenticando no Siscomex...")
    client_id = os.getenv('SISCOMEX_CLIENT_ID')
    client_secret = os.getenv('SISCOMEX_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        print("[ERRO] Credenciais nao configuradas")
        return
    
    token_manager.configurar_credenciais(client_id, client_secret)
    
    if not token_manager.autenticar():
        print("[ERRO] Falha na autenticacao")
        return
    
    print("[OK] Autenticado com sucesso!")
    
    # 3. Importar funcoes de processamento
    try:
        from due_processor import processar_dados_due, salvar_resultados_normalizados, consultar_due_completa
    except ImportError as e:
        print(f"[ERRO] Nao foi possivel importar due_processor: {e}")
        return
    
    # 4. Estrutura para consolidar dados
    dados_consolidados = {
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
        'due_atos_concessorios_suspensao': [],
        'due_atos_concessorios_isencao': [],
        'due_exigencias_fiscais': []
    }
    
    stats = {
        'pendentes_ok': 0,
        'pendentes_erro': 0,
        'averbadas_recentes_ok': 0,
        'averbadas_recentes_erro': 0,
        'averbadas_antigas_mudou': 0,
        'averbadas_antigas_sem_mudanca': 0,
        'averbadas_antigas_erro': 0
    }
    
    # 5. Processar DUEs PENDENTES (atualizar direto)
    dues_pendentes = dues_info['pendentes'] + dues_info['averbadas_recentes']
    if dues_pendentes:
        print(f"\n[FASE 1] Atualizando {len(dues_pendentes)} DUEs pendentes/recentes...")
        
        for i, due_info in enumerate(dues_pendentes, 1):
            numero_due = due_info['numero']
            
            if i % 25 == 0:
                print(f"  [PROGRESSO] {i}/{len(dues_pendentes)}...")
            
            dados_due = consultar_due_completa(numero_due)
            
            if dados_due:
                atos_susp, atos_isen, exig = consultar_dados_adicionais(numero_due, dados_due)
                dados_norm = processar_dados_due(dados_due, atos_susp, atos_isen, exig)
                
                if dados_norm:
                    for tabela, dados in dados_norm.items():
                        if tabela in dados_consolidados:
                            dados_consolidados[tabela].extend(dados)
                    
                    if due_info in dues_info['pendentes']:
                        stats['pendentes_ok'] += 1
                    else:
                        stats['averbadas_recentes_ok'] += 1
                else:
                    if due_info in dues_info['pendentes']:
                        stats['pendentes_erro'] += 1
                    else:
                        stats['averbadas_recentes_erro'] += 1
            else:
                if due_info in dues_info['pendentes']:
                    stats['pendentes_erro'] += 1
                else:
                    stats['averbadas_recentes_erro'] += 1
            
            time.sleep(0.3)
    
    # 6. Processar DUEs AVERBADAS ANTIGAS (verificar antes) - PARALELO
    dues_sem_mudanca = []
    dues_com_erro = []
    if dues_info['averbadas_antigas']:
        print(f"\n[FASE 2] Verificando {len(dues_info['averbadas_antigas'])} DUEs averbadas antigas (PARALELO)...")
        
        # Processar em paralelo
        dados_paralelos, dues_sem_mudanca, stats_paralelos, dues_com_erro = processar_dues_averbadas_antigas_paralelo(
            dues_info['averbadas_antigas']
        )
        
        # Consolidar dados paralelos
        for tabela, dados in dados_paralelos.items():
            if tabela in dados_consolidados and dados:
                dados_consolidados[tabela].extend(dados)
        
        # Atualizar estatísticas
        stats['averbadas_antigas_mudou'] = stats_paralelos['mudou']
        stats['averbadas_antigas_sem_mudanca'] = stats_paralelos['sem_mudanca']
        stats['averbadas_antigas_erro'] = stats_paralelos['erros']
        
        # Atualizar data_ultima_atualizacao em batch para DUEs que não mudaram
        if dues_sem_mudanca:
            print(f"\n[INFO] Atualizando data_ultima_atualizacao para {len(dues_sem_mudanca)} DUEs sem mudança...")
            count_atualizado = db_manager.atualizar_data_ultima_atualizacao_batch(dues_sem_mudanca)
            if count_atualizado > 0:
                print(f"[OK] {count_atualizado} DUEs atualizadas em batch")
    
    # 7. Salvar dados atualizados
    total_atualizadas = (stats['pendentes_ok'] + stats['averbadas_recentes_ok'] + 
                         stats['averbadas_antigas_mudou'])
    
    if total_atualizadas > 0:
        print(f"\n[INFO] Salvando {total_atualizadas} DUEs atualizadas...")
        salvar_resultados_normalizados(dados_consolidados)
    
    # 8. Resumo
    print("\n" + "=" * 60)
    print("ATUALIZACAO CONCLUIDA")
    print("=" * 60)
    
    print(f"\n[RESUMO]")
    print(f"  DUEs Pendentes:")
    print(f"    - Atualizadas: {stats['pendentes_ok']}")
    print(f"    - Erros: {stats['pendentes_erro']}")
    
    print(f"  DUEs Averbadas Recentes (<{DIAS_AVERBACAO_RECENTE} dias):")
    print(f"    - Atualizadas: {stats['averbadas_recentes_ok']}")
    print(f"    - Erros: {stats['averbadas_recentes_erro']}")
    
    print(f"  DUEs Averbadas Antigas:")
    print(f"    - Com mudancas (atualizadas): {stats['averbadas_antigas_mudou']}")
    print(f"    - Sem mudancas (ignoradas): {stats['averbadas_antigas_sem_mudanca']}")
    print(f"    - Erros: {stats['averbadas_antigas_erro']}")
    
    total_ok = stats['pendentes_ok'] + stats['averbadas_recentes_ok'] + stats['averbadas_antigas_mudou']
    total_ignoradas = stats['averbadas_antigas_sem_mudanca']
    total_erros = stats['pendentes_erro'] + stats['averbadas_recentes_erro'] + stats['averbadas_antigas_erro']
    
    print(f"\n  TOTAL:")
    print(f"    - Atualizadas: {total_ok}")
    print(f"    - Ignoradas (sem mudanca): {total_ignoradas}")
    print(f"    - Erros: {total_erros}")
    
    requisicoes_economizadas = total_ignoradas * 3  # 3 req extras por DUE que nao precisou atualizar
    print(f"\n  [OTIMIZACAO] ~{requisicoes_economizadas} requisicoes economizadas!")
    
    # Exibir detalhes dos erros se houver
    if dues_com_erro:
        print(f"\n  [DETALHES DOS ERROS] {len(dues_com_erro)} DUEs com erro:")
        print("-" * 60)
        
        # Agrupar erros por tipo
        erros_por_tipo = {}
        for erro in dues_com_erro:
            msg = erro['mensagem']
            # Simplificar mensagem para agrupamento
            if 'Falha ao verificar' in msg or 'resposta None' in msg:
                tipo = 'Falha ao verificar DUE (API retornou None ou erro)'
            elif 'processar dados completos' in msg:
                tipo = 'Erro ao processar dados completos'
            elif 'Timeout' in msg:
                tipo = 'Timeout na requisição'
            else:
                tipo = msg[:50] + '...' if len(msg) > 50 else msg
            
            if tipo not in erros_por_tipo:
                erros_por_tipo[tipo] = []
            erros_por_tipo[tipo].append(erro['numero_due'])
        
        # Exibir resumo por tipo
        for tipo, numeros in erros_por_tipo.items():
            print(f"    • {tipo}: {len(numeros)} DUEs")
            if len(numeros) <= 10:
                # Se poucas DUEs, mostrar todas
                print(f"      DUEs: {', '.join(numeros)}")
            else:
                # Se muitas, mostrar apenas as primeiras
                print(f"      DUEs (primeiras 10): {', '.join(numeros[:10])}...")
        
        print("-" * 60)


def main():
    """Funcao principal"""
    atualizar_dues()


if __name__ == "__main__":
    main()
