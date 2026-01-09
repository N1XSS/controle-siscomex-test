"""
Sincronizacao de Novas DUEs - OTIMIZADO
========================================

Este servico identifica NFs de exportacao do SAP que ainda nao possuem
DUE vinculada e consulta o Siscomex para obter os dados.

Otimizacoes:
- Cache de vinculos NF->DUE no PostgreSQL (nao reconsulta NFs ja vinculadas)
- Agrupa NFs por DUE para evitar requisicoes duplicadas
- Consulta dados adicionais (drawback suspensao/isencao, exigencias)
- Respeita limite de 1000 req/hora do Siscomex

Uso:
    python sync_novas.py
    python sync_novas.py --limit 200  # Limita consultas
"""

import os
import pandas as pd
from datetime import datetime
import warnings
from dotenv import load_dotenv
from token_manager import token_manager
from db_manager import db_manager
import time
import argparse

warnings.filterwarnings('ignore')
load_dotenv('config.env')

# Flag para usar PostgreSQL
USAR_POSTGRESQL = True

# Caminhos dos arquivos (fallback CSV)
CAMINHO_NFE_SAP = 'dados/nfe-sap.csv'
CAMINHO_VINCULO = 'dados/nf_due_vinculo.csv'

# URL base da API
URL_DUE_BASE = "https://portalunico.siscomex.gov.br/due/api/ext/due"

# Configuracoes
MAX_CONSULTAS_NF = 400  # Limite de NFs por execucao


def carregar_nfs_sap():
    """Carrega as chaves NF do PostgreSQL ou arquivo CSV"""
    if USAR_POSTGRESQL:
        if not db_manager.conn:
            db_manager.conectar()
        
        if db_manager.conn:
            try:
                chaves = db_manager.obter_nfs_sap()
                if chaves:
                    print(f"[INFO] {len(chaves)} chaves NF carregadas do PostgreSQL")
                    return chaves
            except Exception as e:
                print(f"[AVISO] Erro ao carregar NFs do PostgreSQL: {e}, tentando CSV...")
    
    # Fallback para CSV
    if not os.path.exists(CAMINHO_NFE_SAP):
        print(f"[AVISO] Arquivo {CAMINHO_NFE_SAP} nao encontrado")
        print("Execute primeiro: python consulta_sap.py")
        return []
    
    try:
        df = pd.read_csv(CAMINHO_NFE_SAP, sep=';', encoding='utf-8-sig')
        
        col_chave = 'Chave NF' if 'Chave NF' in df.columns else 'KeyNfe'
        if col_chave not in df.columns:
            print(f"[ERRO] Coluna de chave NF nao encontrada")
            return []
        
        chaves = df[col_chave].dropna().astype(str)
        chaves = chaves[chaves.str.len() >= 44]
        chaves = chaves.unique().tolist()
        
        print(f"[INFO] {len(chaves)} chaves NF carregadas do CSV")
        return chaves
        
    except Exception as e:
        print(f"[ERRO] Erro ao carregar NFs do SAP: {e}")
        return []


def carregar_vinculos_existentes():
    """
    Carrega vinculos NF->DUE existentes do PostgreSQL
    Retorna dict: {chave_nf: numero_due}
    """
    if not db_manager.conn:
        db_manager.conectar()
    
    if db_manager.conn:
        try:
            vinculos = db_manager.obter_vinculos()
            if vinculos:
                print(f"[INFO] {len(vinculos)} vinculos existentes carregados")
                return vinculos
        except Exception as e:
            print(f"[AVISO] Erro ao carregar vinculos: {e}")
    
    return {}


def salvar_novos_vinculos(novos_vinculos):
    """
    Salva novos vinculos NF->DUE no PostgreSQL
    
    Args:
        novos_vinculos: dict {chave_nf: numero_due}
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
    
    if db_manager.conn:
        try:
            count = db_manager.inserir_vinculos_batch(registros)
            if count > 0:
                print(f"[OK] {count} novos vinculos salvos")
                return
        except Exception as e:
            print(f"[AVISO] Erro ao salvar vinculos: {e}")
    
    # Fallback para CSV
    try:
        os.makedirs('dados', exist_ok=True)
        
        # Carregar existentes e adicionar novos
        if os.path.exists(CAMINHO_VINCULO):
            df_existente = pd.read_csv(CAMINHO_VINCULO, sep=';', encoding='utf-8-sig')
            df_novo = pd.DataFrame(registros)
            df = pd.concat([df_existente, df_novo], ignore_index=True)
        else:
            df = pd.DataFrame(registros)
        
        df.to_csv(CAMINHO_VINCULO, sep=';', index=False, encoding='utf-8-sig')
        print(f"[OK] {len(novos_vinculos)} vinculos salvos em CSV")
        
    except Exception as e:
        print(f"[ERRO] Erro ao salvar vinculo CSV: {e}")


def consultar_dados_adicionais(numero_due):
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


def processar_novas_nfs():
    """Processa NFs do SAP que ainda nao tem DUE vinculada"""
    parser = argparse.ArgumentParser(description='Sincronizar novas NFs com DUEs')
    parser.add_argument('--limit', type=int, default=MAX_CONSULTAS_NF,
                        help=f'Limite de NFs para consultar (default: {MAX_CONSULTAS_NF})')
    args = parser.parse_args()
    
    print("=" * 60)
    print("SINCRONIZACAO DE NOVAS DUEs")
    print("=" * 60)
    print(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 60)
    print()
    
    # Conectar ao PostgreSQL
    if USAR_POSTGRESQL:
        if not db_manager.conectar():
            print("[AVISO] Nao foi possivel conectar ao PostgreSQL")
    
    # 1. Carregar NFs do SAP
    nfs_sap = carregar_nfs_sap()
    if not nfs_sap:
        print("[AVISO] Nenhuma NF encontrada no SAP")
        return
    
    # 2. Carregar vinculos existentes (CACHE)
    vinculos_existentes = carregar_vinculos_existentes()
    
    # 3. Identificar NFs que AINDA NAO tem vinculo
    nfs_sem_vinculo = [nf for nf in nfs_sap if nf not in vinculos_existentes]
    
    print(f"\n[CACHE] NFs do SAP: {len(nfs_sap)}")
    print(f"[CACHE] Vinculos existentes: {len(vinculos_existentes)}")
    print(f"[CACHE] NFs sem vinculo: {len(nfs_sem_vinculo)}")
    
    if not nfs_sem_vinculo:
        print("\n[OK] Todas as NFs ja possuem DUE vinculada!")
        print("[INFO] Cache 100% efetivo - nenhuma requisicao necessaria")
        return
    
    # 4. Autenticar no Siscomex
    print("\n[INFO] Autenticando no Siscomex...")
    client_id = os.getenv('SISCOMEX_CLIENT_ID')
    client_secret = os.getenv('SISCOMEX_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        print("[ERRO] Credenciais SISCOMEX_CLIENT_ID e SISCOMEX_CLIENT_SECRET nao configuradas")
        return
    
    token_manager.configurar_credenciais(client_id, client_secret)
    
    if not token_manager.autenticar():
        print("[ERRO] Falha na autenticacao")
        return
    
    print("[OK] Autenticado com sucesso!")
    
    # 5. Importar funcoes
    try:
        from due_processor import consultar_due_por_nf, processar_dados_due, salvar_resultados_normalizados, consultar_due_completa
    except ImportError as e:
        print(f"[ERRO] Nao foi possivel importar due_processor: {e}")
        return
    
    # 6. Consultar DUEs para NFs sem vinculo
    novos_vinculos = {}
    dues_para_baixar = set()
    
    max_consultas = min(len(nfs_sem_vinculo), args.limit)
    print(f"\n[INFO] Consultando DUEs para {max_consultas} NFs...")
    
    nfs_sem_due_encontrada = 0
    
    for i, chave_nf in enumerate(nfs_sem_vinculo[:max_consultas], 1):
        if i % 50 == 0:
            print(f"  [PROGRESSO] {i}/{max_consultas} NFs consultadas...")
        
        resultado = consultar_due_por_nf(chave_nf)
        numero_due = resultado.get('numero') if isinstance(resultado, dict) and resultado else None
        
        if numero_due:
            novos_vinculos[chave_nf] = numero_due
            dues_para_baixar.add(numero_due)
        else:
            nfs_sem_due_encontrada += 1
        
        time.sleep(0.2)
    
    print(f"\n[INFO] {len(novos_vinculos)} novos vinculos encontrados")
    print(f"[INFO] {nfs_sem_due_encontrada} NFs sem DUE no Siscomex")
    print(f"[INFO] {len(dues_para_baixar)} DUEs unicas para baixar")
    
    # 7. Salvar novos vinculos
    if novos_vinculos:
        salvar_novos_vinculos(novos_vinculos)
    
    # 8. Baixar dados completos das DUEs novas
    if dues_para_baixar:
        print(f"\n[INFO] Baixando dados de {len(dues_para_baixar)} DUEs...")
        
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
        
        dues_ok = 0
        dues_erro = 0
        
        for i, numero_due in enumerate(dues_para_baixar, 1):
            if i % 10 == 0:
                print(f"  [PROGRESSO] {i}/{len(dues_para_baixar)} DUEs...")
            
            dados_due = consultar_due_completa(numero_due)
            
            if dados_due:
                # Consultar dados adicionais
                atos_susp, atos_isen, exig = consultar_dados_adicionais(numero_due)
                
                # Processar dados
                dados_norm = processar_dados_due(dados_due, atos_susp, atos_isen, exig)
                
                if dados_norm:
                    for tabela, dados in dados_norm.items():
                        if tabela in dados_consolidados:
                            dados_consolidados[tabela].extend(dados)
                    dues_ok += 1
                else:
                    dues_erro += 1
            else:
                dues_erro += 1
            
            time.sleep(0.3)
        
        print(f"\n[OK] {dues_ok} DUEs baixadas com sucesso")
        if dues_erro > 0:
            print(f"[AVISO] {dues_erro} DUEs com erro")
        
        # Salvar dados
        if dues_ok > 0:
            salvar_resultados_normalizados(dados_consolidados)
    
    # 9. Resumo
    print("\n" + "=" * 60)
    print("SINCRONIZACAO CONCLUIDA")
    print("=" * 60)
    
    print(f"\n[RESUMO]")
    print(f"  NFs no SAP: {len(nfs_sap)}")
    print(f"  Vinculos existentes (cache): {len(vinculos_existentes)}")
    print(f"  NFs consultadas: {max_consultas}")
    print(f"  Novos vinculos: {len(novos_vinculos)}")
    print(f"  DUEs baixadas: {len(dues_para_baixar)}")
    
    if len(nfs_sem_vinculo) > max_consultas:
        restantes = len(nfs_sem_vinculo) - max_consultas
        print(f"\n[INFO] Restam {restantes} NFs para processar na proxima execucao")


def main():
    """Funcao principal"""
    processar_novas_nfs()


if __name__ == "__main__":
    main()
