"""
Consulta AWS Athena - Notas Fiscais de Exportacao de Pluma
===========================================================

Este script consulta o AWS Athena para obter as chaves de NF
de exportacao de algodao em pluma (CFOP 7504) de 2 empresas:
- sap_sboagropecuarialocks
- sap_sbosamuelmaggilocks

O resultado e salvo no PostgreSQL (tabela nfe_sap) ou exportado para CSV.

Uso:
    python consulta_sap.py
"""

import boto3
from botocore.exceptions import ClientError, BotoCoreError
import pandas as pd
from datetime import datetime
import warnings
import os
import time
from dotenv import load_dotenv
from db_manager import db_manager
warnings.filterwarnings('ignore')

# Carregar variáveis de ambiente
load_dotenv()

# Flag para usar PostgreSQL
USAR_POSTGRESQL = True

# Configurações AWS Athena
AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_KEY')
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
ATHENA_CATALOG = os.getenv('ATHENA_CATALOG', 'AwsDataCatalog')
ATHENA_DATABASE = os.getenv('ATHENA_DATABASE', 'default')
ATHENA_WORKGROUP = os.getenv('ATHENA_WORKGROUP', 'primary')
S3_OUTPUT_LOCATION = os.getenv('S3_OUTPUT_LOCATION', 's3://locks-query-result/athena_odbc/')

# Query SQL - consulta 2 databases para NFs de exportacao de pluma
QUERY = """
WITH 
-- sap_sboagropecuarialocks
PluginAntigo_AGROPECUARIA AS (
    SELECT
        u_docentry,
        u_chaveacesso,
        ROW_NUMBER() OVER (PARTITION BY u_docentry ORDER BY u_createdate DESC) AS rn
    FROM sap_sboagropecuarialocks.skl25nfe
    WHERE u_tipodocumento = 'NS'
),
PluginNovo_AGROPECUARIA AS (
    SELECT
        p.docentry,
        p.keynfe,
        ROW_NUMBER() OVER (PARTITION BY p.docentry ORDER BY p.ultimaalocacao DESC) AS rn
    FROM sap_sboagropecuarialocks.process p
    INNER JOIN sap_sboagropecuarialocks.processstatus ps ON ps.id = p.statusid
    WHERE p.doctype = 13
),

-- sap_sbosamuelmaggilocks
PluginAntigo_SAMUELMAGGI AS (
    SELECT
        u_docentry,
        u_chaveacesso,
        ROW_NUMBER() OVER (PARTITION BY u_docentry ORDER BY u_createdate DESC) AS rn
    FROM sap_sbosamuelmaggilocks.skl25nfe
    WHERE u_tipodocumento = 'NS'
),
PluginNovo_SAMUELMAGGI AS (
    SELECT
        p.docentry,
        p.keynfe,
        ROW_NUMBER() OVER (PARTITION BY p.docentry ORDER BY p.ultimaalocacao DESC) AS rn
    FROM sap_sbosamuelmaggilocks.process p
    INNER JOIN sap_sbosamuelmaggilocks.processstatus ps ON ps.id = p.statusid
    WHERE p.doctype = 13
)

-- sap_sboagropecuarialocks
SELECT
    COALESCE(pn.keynfe, pa.u_chaveacesso) AS keynfe
FROM sap_sboagropecuarialocks.oinv nf
LEFT JOIN PluginAntigo_AGROPECUARIA pa ON pa.u_docentry = nf.docentry AND pa.rn = 1
LEFT JOIN PluginNovo_AGROPECUARIA pn ON pn.docentry = nf.docentry AND pn.rn = 1
WHERE nf.canceled = 'N'
  AND EXISTS (
      SELECT 1 FROM sap_sboagropecuarialocks.inv1 itens
      WHERE itens.docentry = nf.docentry
        AND itens.dscription LIKE 'ALGODAO EM PLUMA%'
        AND itens.cfopcode = '7504'
  )
  AND COALESCE(pn.keynfe, pa.u_chaveacesso) IS NOT NULL

UNION ALL

-- sap_sbosamuelmaggilocks
SELECT
    COALESCE(pn.keynfe, pa.u_chaveacesso) AS keynfe
FROM sap_sbosamuelmaggilocks.oinv nf
LEFT JOIN PluginAntigo_SAMUELMAGGI pa ON pa.u_docentry = nf.docentry AND pa.rn = 1
LEFT JOIN PluginNovo_SAMUELMAGGI pn ON pn.docentry = nf.docentry AND pn.rn = 1
WHERE nf.canceled = 'N'
  AND EXISTS (
      SELECT 1 FROM sap_sbosamuelmaggilocks.inv1 itens
      WHERE itens.docentry = nf.docentry
        AND itens.dscription LIKE 'ALGODAO EM PLUMA%'
        AND itens.cfopcode = '7504'
  )
  AND COALESCE(pn.keynfe, pa.u_chaveacesso) IS NOT NULL
"""


def criar_cliente_athena():
    """
    Cria e retorna cliente do AWS Athena
    
    Returns:
        boto3.client: Cliente do Athena ou None em caso de erro
    """
    try:
        if not AWS_ACCESS_KEY or not AWS_SECRET_KEY:
            print("[ERRO] Credenciais AWS nao encontradas nas variaveis de ambiente")
            print("Configure AWS_ACCESS_KEY e AWS_SECRET_KEY no arquivo .env")
            return None
        
        cliente = boto3.client(
            'athena',
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY,
            region_name=AWS_REGION
        )
        return cliente
    except Exception as e:
        print(f"[ERRO] Erro ao criar cliente Athena: {e}")
        return None


def executar_query_athena(cliente, query):
    """
    Executa query no AWS Athena e retorna o resultado como DataFrame
    
    Args:
        cliente: Cliente do boto3 para Athena
        query: Query SQL a ser executada
        
    Returns:
        pd.DataFrame: DataFrame com os resultados ou None em caso de erro
    """
    try:
        print("Iniciando execucao da query no Athena...")
        
        # Iniciar execução da query
        response = cliente.start_query_execution(
            QueryString=query,
            QueryExecutionContext={
                'Database': ATHENA_DATABASE,
                'Catalog': ATHENA_CATALOG
            },
            ResultConfiguration={
                'OutputLocation': S3_OUTPUT_LOCATION
            },
            WorkGroup=ATHENA_WORKGROUP
        )
        
        query_execution_id = response['QueryExecutionId']
        print(f"[OK] Query iniciada. Execution ID: {query_execution_id}")
        
        # Aguardar conclusão da query
        print("Aguardando conclusao da query...")
        while True:
            response = cliente.get_query_execution(QueryExecutionId=query_execution_id)
            status = response['QueryExecution']['Status']['State']
            
            if status in ['SUCCEEDED']:
                print("[OK] Query executada com sucesso!")
                break
            elif status in ['FAILED', 'CANCELLED']:
                reason = response['QueryExecution']['Status'].get('StateChangeReason', 'N/A')
                print(f"[ERRO] Query falhou ou foi cancelada: {reason}")
                return None
            else:
                # Status: QUEUED, RUNNING
                time.sleep(1)
        
        # Obter resultados
        print("Obtendo resultados...")
        resultados = []
        next_token = None
        
        while True:
            if next_token:
                response = cliente.get_query_results(
                    QueryExecutionId=query_execution_id,
                    NextToken=next_token
                )
            else:
                response = cliente.get_query_results(QueryExecutionId=query_execution_id)
            
            # Processar colunas (primeira linha)
            if not resultados:
                colunas = [col['Name'] for col in response['ResultSet']['ResultSetMetadata']['ColumnInfo']]
            
            # Processar linhas de dados (pular primeira linha que são os headers)
            rows = response['ResultSet']['Rows']
            for i, row in enumerate(rows):
                if i == 0 and not resultados:
                    # Primeira linha são os headers, pular
                    continue
                valores = [cell.get('VarCharValue', '') for cell in row['Data']]
                resultados.append(valores)
            
            # Verificar se há mais resultados
            next_token = response.get('NextToken')
            if not next_token:
                break
        
        # Criar DataFrame
        if resultados:
            df = pd.DataFrame(resultados, columns=colunas)
            return df
        else:
            print("[AVISO] Nenhum resultado retornado pela query")
            return pd.DataFrame()
        
    except ClientError as e:
        print(f"[ERRO] Erro do cliente AWS: {e}")
        return None
    except BotoCoreError as e:
        print(f"[ERRO] Erro do BotoCore: {e}")
        return None
    except Exception as e:
        print(f"[ERRO] Erro ao executar query: {e}")
        return None


def consultar_nfs_exportacao():
    """
    Consulta o AWS Athena e retorna DataFrame com as chaves de NF
    de exportacao de algodao em pluma (CFOP 7504).
    
    Returns:
        pd.DataFrame: DataFrame com coluna 'keynfe' ou None em caso de erro
    """
    try:
        print("Conectando ao AWS Athena...")
        print("-" * 50)
        
        cliente = criar_cliente_athena()
        if not cliente:
            return None
        
        print("[OK] Cliente Athena criado com sucesso!")
        print(f"Region: {AWS_REGION}")
        print(f"Database: {ATHENA_DATABASE}")
        print(f"Workgroup: {ATHENA_WORKGROUP}")
        print("-" * 50)
        
        print("Executando consulta SQL...")
        print("Buscando NFs de exportacao de algodao em pluma (CFOP 7504)")
        print("Databases: AGROPECUARIA, SAMUELMAGGI")
        print("-" * 50)
        
        df = executar_query_athena(cliente, QUERY)
        
        if df is None:
            return None
        
        if df.empty:
            print("[AVISO] Nenhum resultado encontrado")
            return df
        
        # Renomear coluna para manter compatibilidade
        if 'keynfe' in df.columns:
            df = df.rename(columns={'keynfe': 'KeyNfe'})
        
        # Filtrar apenas chaves validas
        df = df.dropna(subset=['KeyNfe'])
        df = df[df['KeyNfe'].str.len() >= 44]
        df = df.drop_duplicates(subset=['KeyNfe'])
        
        print(f"[OK] Consulta executada com sucesso!")
        print(f"Total de chaves NF unicas encontradas: {len(df)}")
        print("-" * 50)
        
        return df
        
    except Exception as e:
        print(f"[ERRO] Erro ao executar consulta: {e}")
        return None


def salvar_nfs(df):
    """
    Salva as chaves NF no PostgreSQL
    
    Args:
        df: DataFrame com as chaves NF
    """
    if df is None or df.empty:
        print("[AVISO] Nao ha dados para salvar.")
        return False
    
    # Extrair chaves
    col_chave = 'KeyNfe' if 'KeyNfe' in df.columns else 'Chave NF'
    chaves = df[col_chave].dropna().astype(str).unique().tolist()
    
    # Conectar ao PostgreSQL
    if not db_manager.conn:
        if not db_manager.conectar():
            print("[ERRO] Nao foi possivel conectar ao PostgreSQL")
            return False
    
    try:
        count = db_manager.inserir_nf_sap(chaves)
        if count > 0:
            print(f"\n[OK] {count} chaves NF salvas no PostgreSQL")
            return True
        else:
            print("[AVISO] Nenhuma chave NF foi salva")
            return False
    except Exception as e:
        print(f"[ERRO] Erro ao salvar no PostgreSQL: {e}")
        return False


def main():
    """Funcao principal"""
    print("=" * 60)
    print("CONSULTA AWS ATHENA - NFS EXPORTACAO PLUMA")
    print("=" * 60)
    print(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 60)
    print()
    
    # Executa consulta
    df = consultar_nfs_exportacao()
    
    # Salva no PostgreSQL
    if df is not None and not df.empty:
        print("\n" + "=" * 60)
        print("Salvando dados no PostgreSQL...")
        salvar_nfs(df)
    
    print("\n" + "=" * 60)
    print("PROCESSO FINALIZADO")
    print("=" * 60)
    
    # Desconectar do PostgreSQL
    if db_manager.conn:
        db_manager.desconectar()
    
    return df


if __name__ == "__main__":
    main()
