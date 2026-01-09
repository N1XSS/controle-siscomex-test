"""
Consulta SAP HANA - Notas Fiscais de Exportacao de Pluma
=========================================================

Este script consulta o banco de dados SAP HANA para obter as chaves de NF
de exportacao de algodao em pluma (CFOP 7504) de 4 empresas:
- SBOAGROPECUARIALOCKS
- SBOLOCKSAGROBUSINESS
- SBOLOCKSAGRICOLA
- SBOSAMUELMAGGILOCKS

O resultado e salvo no PostgreSQL (tabela nfe_sap) ou exportado para CSV.

Uso:
    python consulta_sap.py
"""

import pyodbc
import pandas as pd
from datetime import datetime
import warnings
import os
from db_manager import db_manager
warnings.filterwarnings('ignore')

# Flag para usar PostgreSQL
USAR_POSTGRESQL = True

# Configuracoes de conexao
CONNECTION_STRING = (
    "Driver=HDBODBC;"
    "ServerNode=SRVLKSOCIHANA01:30015;"
    "UID=LKS_BI;"
    "PWD=!@#BiL0cks!@#4;"
)

# Query SQL otimizada - consulta 4 databases para NFs de exportacao de pluma
QUERY = """
WITH 
-- SBOAGROPECUARIALOCKS
PluginAntigo_AGROPECUARIA AS (
    SELECT
        "U_DocEntry",
        "U_ChaveAcesso",
        ROW_NUMBER() OVER (PARTITION BY "U_DocEntry" ORDER BY "U_CreateDate" DESC) AS rn
    FROM SBOAGROPECUARIALOCKS."@SKL25NFE"
    WHERE "U_tipoDocumento" = 'NS'
),
PluginNovo_AGROPECUARIA AS (
    SELECT
        p."DocEntry",
        p."KeyNfe",
        ROW_NUMBER() OVER (PARTITION BY p."DocEntry" ORDER BY p."UltimaAlocacao" DESC) AS rn
    FROM SBOAGROPECUARIALOCKS."Process" p
    INNER JOIN SBOAGROPECUARIALOCKS."ProcessStatus" ps ON ps."ID" = p."StatusId"
    WHERE p."DocType" = 13
),

-- SBOLOCKSAGROBUSINESS
PluginAntigo_AGROBUSINESS AS (
    SELECT
        "U_DocEntry",
        "U_ChaveAcesso",
        ROW_NUMBER() OVER (PARTITION BY "U_DocEntry" ORDER BY "U_CreateDate" DESC) AS rn
    FROM SBOLOCKSAGROBUSINESS."@SKL25NFE"
    WHERE "U_tipoDocumento" = 'NS'
),
PluginNovo_AGROBUSINESS AS (
    SELECT
        p."DocEntry",
        p."KeyNfe",
        ROW_NUMBER() OVER (PARTITION BY p."DocEntry" ORDER BY p."UltimaAlocacao" DESC) AS rn
    FROM SBOLOCKSAGROBUSINESS."Process" p
    INNER JOIN SBOLOCKSAGROBUSINESS."ProcessStatus" ps ON ps."ID" = p."StatusId"
    WHERE p."DocType" = 13
),

-- SBOLOCKSAGRICOLA
PluginAntigo_AGRICOLA AS (
    SELECT
        "U_DocEntry",
        "U_ChaveAcesso",
        ROW_NUMBER() OVER (PARTITION BY "U_DocEntry" ORDER BY "U_CreateDate" DESC) AS rn
    FROM SBOLOCKSAGRICOLA."@SKL25NFE"
    WHERE "U_tipoDocumento" = 'NS'
),
PluginNovo_AGRICOLA AS (
    SELECT
        p."DocEntry",
        p."KeyNfe",
        ROW_NUMBER() OVER (PARTITION BY p."DocEntry" ORDER BY p."UltimaAlocacao" DESC) AS rn
    FROM SBOLOCKSAGRICOLA."Process" p
    INNER JOIN SBOLOCKSAGRICOLA."ProcessStatus" ps ON ps."ID" = p."StatusId"
    WHERE p."DocType" = 13
),

-- SBOSAMUELMAGGILOCKS
PluginAntigo_SAMUELMAGGI AS (
    SELECT
        "U_DocEntry",
        "U_ChaveAcesso",
        ROW_NUMBER() OVER (PARTITION BY "U_DocEntry" ORDER BY "U_CreateDate" DESC) AS rn
    FROM SBOSAMUELMAGGILOCKS."@SKL25NFE"
    WHERE "U_tipoDocumento" = 'NS'
),
PluginNovo_SAMUELMAGGI AS (
    SELECT
        p."DocEntry",
        p."KeyNfe",
        ROW_NUMBER() OVER (PARTITION BY p."DocEntry" ORDER BY p."UltimaAlocacao" DESC) AS rn
    FROM SBOSAMUELMAGGILOCKS."Process" p
    INNER JOIN SBOSAMUELMAGGILOCKS."ProcessStatus" ps ON ps."ID" = p."StatusId"
    WHERE p."DocType" = 13
)

-- SBOAGROPECUARIALOCKS
SELECT
    COALESCE(pn."KeyNfe", pa."U_ChaveAcesso") AS "KeyNfe"
FROM SBOAGROPECUARIALOCKS.OINV nf
LEFT JOIN PluginAntigo_AGROPECUARIA pa ON pa."U_DocEntry" = nf."DocEntry" AND pa.rn = 1
LEFT JOIN PluginNovo_AGROPECUARIA pn ON pn."DocEntry" = nf."DocEntry" AND pn.rn = 1
WHERE nf."CANCELED" = 'N'
  AND EXISTS (
      SELECT 1 FROM SBOAGROPECUARIALOCKS.INV1 itens
      WHERE itens."DocEntry" = nf."DocEntry"
        AND itens."Dscription" LIKE 'ALGODAO EM PLUMA%'
        AND itens."CFOPCode" = '7504'
  )

UNION ALL

-- SBOLOCKSAGROBUSINESS
SELECT
    COALESCE(pn."KeyNfe", pa."U_ChaveAcesso") AS "KeyNfe"
FROM SBOLOCKSAGROBUSINESS.OINV nf
LEFT JOIN PluginAntigo_AGROBUSINESS pa ON pa."U_DocEntry" = nf."DocEntry" AND pa.rn = 1
LEFT JOIN PluginNovo_AGROBUSINESS pn ON pn."DocEntry" = nf."DocEntry" AND pn.rn = 1
WHERE nf."CANCELED" = 'N'
  AND EXISTS (
      SELECT 1 FROM SBOLOCKSAGROBUSINESS.INV1 itens
      WHERE itens."DocEntry" = nf."DocEntry"
        AND itens."Dscription" LIKE 'ALGODAO EM PLUMA%'
        AND itens."CFOPCode" = '7504'
  )

UNION ALL

-- SBOLOCKSAGRICOLA
SELECT
    COALESCE(pn."KeyNfe", pa."U_ChaveAcesso") AS "KeyNfe"
FROM SBOLOCKSAGRICOLA.OINV nf
LEFT JOIN PluginAntigo_AGRICOLA pa ON pa."U_DocEntry" = nf."DocEntry" AND pa.rn = 1
LEFT JOIN PluginNovo_AGRICOLA pn ON pn."DocEntry" = nf."DocEntry" AND pn.rn = 1
WHERE nf."CANCELED" = 'N'
  AND EXISTS (
      SELECT 1 FROM SBOLOCKSAGRICOLA.INV1 itens
      WHERE itens."DocEntry" = nf."DocEntry"
        AND itens."Dscription" LIKE 'ALGODAO EM PLUMA%'
        AND itens."CFOPCode" = '7504'
  )

UNION ALL

-- SBOSAMUELMAGGILOCKS
SELECT
    COALESCE(pn."KeyNfe", pa."U_ChaveAcesso") AS "KeyNfe"
FROM SBOSAMUELMAGGILOCKS.OINV nf
LEFT JOIN PluginAntigo_SAMUELMAGGI pa ON pa."U_DocEntry" = nf."DocEntry" AND pa.rn = 1
LEFT JOIN PluginNovo_SAMUELMAGGI pn ON pn."DocEntry" = nf."DocEntry" AND pn.rn = 1
WHERE nf."CANCELED" = 'N'
  AND EXISTS (
      SELECT 1 FROM SBOSAMUELMAGGILOCKS.INV1 itens
      WHERE itens."DocEntry" = nf."DocEntry"
        AND itens."Dscription" LIKE 'ALGODAO EM PLUMA%'
        AND itens."CFOPCode" = '7504'
  )
"""


def consultar_nfs_exportacao():
    """
    Consulta o banco SAP HANA e retorna DataFrame com as chaves de NF
    de exportacao de algodao em pluma (CFOP 7504).
    
    Returns:
        pd.DataFrame: DataFrame com coluna 'KeyNfe' ou None em caso de erro
    """
    try:
        print("Conectando ao banco de dados SAP HANA...")
        print("-" * 50)
        
        conn = pyodbc.connect(CONNECTION_STRING)
        print("[OK] Conexao estabelecida com sucesso!")
        print("-" * 50)
        
        print("Executando consulta SQL...")
        print("Buscando NFs de exportacao de algodao em pluma (CFOP 7504)")
        print("Databases: AGROPECUARIA, AGROBUSINESS, AGRICOLA, SAMUELMAGGI")
        print("-" * 50)
        
        df = pd.read_sql(QUERY, conn)
        conn.close()
        
        # Filtrar apenas chaves validas
        df = df.dropna(subset=['KeyNfe'])
        df = df[df['KeyNfe'].str.len() >= 44]
        df = df.drop_duplicates(subset=['KeyNfe'])
        
        print(f"[OK] Consulta executada com sucesso!")
        print(f"Total de chaves NF unicas encontradas: {len(df)}")
        print("-" * 50)
        
        return df
        
    except pyodbc.Error as e:
        print(f"[ERRO] Erro de conexao ODBC: {e}")
        return None
    except Exception as e:
        print(f"[ERRO] Erro ao executar consulta: {e}")
        return None


def salvar_nfs(df):
    """
    Salva as chaves NF no PostgreSQL ou arquivo CSV
    
    Args:
        df: DataFrame com as chaves NF
    """
    if df is None or df.empty:
        print("[AVISO] Nao ha dados para salvar.")
        return False
    
    # Extrair chaves
    col_chave = 'KeyNfe' if 'KeyNfe' in df.columns else 'Chave NF'
    chaves = df[col_chave].dropna().astype(str).unique().tolist()
    
    # Tentar PostgreSQL primeiro
    if USAR_POSTGRESQL:
        try:
            if not db_manager.conn:
                if not db_manager.conectar():
                    print("[AVISO] Nao foi possivel conectar ao PostgreSQL, salvando em CSV...")
                else:
                    count = db_manager.inserir_nf_sap(chaves)
                    if count > 0:
                        print(f"\n[OK] {count} chaves NF salvas no PostgreSQL")
                        return True
        except Exception as e:
            print(f"[AVISO] Erro ao salvar no PostgreSQL: {e}, salvando em CSV...")
    
    # Fallback para CSV
    return _exportar_para_csv(df)


def _exportar_para_csv(df, nome_arquivo='nfe-sap.csv'):
    """
    Exporta o DataFrame para arquivo CSV na pasta dados/ (fallback)
    
    Args:
        df: DataFrame com as chaves NF
        nome_arquivo: Nome do arquivo de saida
    """
    if df is None or df.empty:
        print("[AVISO] Nao ha dados para exportar.")
        return False
    
    try:
        pasta_dados = 'dados'
        if not os.path.exists(pasta_dados):
            os.makedirs(pasta_dados)
            print(f"[INFO] Pasta '{pasta_dados}' criada.")
        
        caminho_arquivo = os.path.join(pasta_dados, nome_arquivo)
        
        # Renomear coluna para manter compatibilidade
        df_export = df.rename(columns={'KeyNfe': 'Chave NF'})
        
        df_export.to_csv(
            caminho_arquivo, 
            index=False, 
            sep=';', 
            encoding='utf-8-sig'
        )
        
        print(f"\n[OK] Dados exportados para: {caminho_arquivo}")
        print(f"    Total de {len(df_export)} chaves NF salvas.")
        print(f"    Formato: CSV com separador ';' e encoding UTF-8")
        
        return True
        
    except Exception as e:
        print(f"[ERRO] Erro ao exportar para CSV: {e}")
        return False


def main():
    """Funcao principal"""
    print("=" * 60)
    print("CONSULTA SAP HANA - NFS EXPORTACAO PLUMA")
    print("=" * 60)
    print(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 60)
    print()
    
    # Executa consulta
    df = consultar_nfs_exportacao()
    
    # Salva no PostgreSQL ou CSV
    if df is not None and not df.empty:
        print("\n" + "=" * 60)
        print("Salvando dados...")
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
