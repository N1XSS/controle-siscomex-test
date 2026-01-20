"""
Gerenciador de conexao e operacoes com PostgreSQL
Sistema DUE - Siscomex
"""

import os
import time
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, Generator, List, Optional

import psycopg2
from psycopg2 import pool, sql
from psycopg2.extras import RealDictCursor, execute_values
from dotenv import load_dotenv

from src.core.constants import (
    DB_CONNECTION_TIMEOUT_SEC,
    ENV_CONFIG_FILE,
    SITUACOES_AVERBADAS,
    SITUACOES_CANCELADAS,
    SITUACOES_PENDENTES,
)
from src.database.schema import ALL_TABLES, DROP_ALL_TABLES
from src.core.logger import logger

# Carregar variáveis de ambiente (arquivo .env se existir, mas não sobrescreve variáveis já definidas)
# No Docker, as variáveis vêm do ambiente (Dokploy), não de arquivos
load_dotenv(ENV_CONFIG_FILE)


class DatabaseManager:
    """Gerenciador de conexao e operacoes com PostgreSQL"""
    
    def __init__(self) -> None:
        self._pool: pool.ThreadedConnectionPool | None = None
        self.conn = None
        self.host = os.getenv('POSTGRES_HOST')
        self.port = os.getenv('POSTGRES_PORT', '5432')
        self.user = os.getenv('POSTGRES_USER')
        self.password = os.getenv('POSTGRES_PASSWORD')
        self.database = os.getenv('POSTGRES_DB')

    def _initialize_pool(self) -> None:
        """Inicializa o pool de conexoes se necessario."""
        if self._pool is not None:
            return

        self._pool = pool.ThreadedConnectionPool(
            minconn=2,
            maxconn=10,
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database,
            connect_timeout=DB_CONNECTION_TIMEOUT_SEC,
        )
        logger.info("PostgreSQL pool initialized (2-10 connections)")

    @contextmanager
    def get_connection(self) -> Generator[psycopg2.extensions.connection, None, None]:
        """Obtém uma conexao do pool com context manager."""
        if self.conn is not None:
            yield self.conn
            return

        self._initialize_pool()
        conn = self._pool.getconn() if self._pool else None
        try:
            if conn is None:
                raise RuntimeError("Connection pool not initialized")
            conn.autocommit = False
            yield conn
        finally:
            if conn and self._pool:
                try:
                    conn.rollback()
                except Exception:
                    pass
                self._pool.putconn(conn)

    @contextmanager
    def use_connection(self) -> Generator[psycopg2.extensions.connection, None, None]:
        """Disponibiliza uma conexao e garante self.conn durante o escopo."""
        if self.conn is not None:
            yield self.conn
            return

        self._initialize_pool()
        conn = self._pool.getconn() if self._pool else None
        try:
            if conn is None:
                raise RuntimeError("Connection pool not initialized")
            conn.autocommit = False
            previous = self.conn
            self.conn = conn
            yield conn
        finally:
            self.conn = previous
            if conn and self._pool:
                try:
                    conn.rollback()
                except Exception:
                    pass
                self._pool.putconn(conn)
    
    def conectar(self) -> bool:
        """Estabelece conexao com o banco de dados.

        Returns:
            True quando a conexao foi estabelecida.
        """
        try:
            self._initialize_pool()
            if self.conn is None and self._pool:
                self.conn = self._pool.getconn()
            self.conn.autocommit = False
            logger.info(
                "Connected to PostgreSQL: %s:%s/%s",
                self.host,
                self.port,
                self.database,
            )
            return True
        except Exception as e:
            logger.error("Failed to connect to PostgreSQL: %s", e, exc_info=True)
            return False
    
    def desconectar(self) -> None:
        """Fecha a conexao ou devolve ao pool."""
        if self.conn:
            if self._pool:
                self._pool.putconn(self.conn)
            else:
                self.conn.close()
            self.conn = None
            logger.info("PostgreSQL connection released")

    def fechar_pool(self) -> None:
        """Fecha todas as conexoes do pool."""
        if self._pool:
            self._pool.closeall()
            self._pool = None
            logger.info("PostgreSQL pool closed")
    
    def executar_query(self, query: str, params: tuple = None, commit: bool = True) -> bool:
        """Executa uma query SQL.

        Args:
            query: SQL a executar.
            params: Parametros opcionais da query.
            commit: Confirma a transacao quando True.

        Returns:
            True quando a execucao ocorreu sem erro.
        """
        conn = None
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, params)
                    if commit:
                        conn.commit()
            return True
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error("Query failed: %s", e, exc_info=True)
            return False
    
    def executar_query_retorno(self, query: str, params: tuple = None) -> List[Dict]:
        """Executa uma query SQL e retorna resultados.

        Args:
            query: SQL a executar.
            params: Parametros opcionais da query.

        Returns:
            Lista de registros em formato dict.
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(query, params)
                    return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            logger.error("Query failed: %s", e, exc_info=True)
            return []
    
    # =========================================================================
    # CRIACAO DE TABELAS
    # =========================================================================
    
    def criar_tabelas(self, drop_existing: bool = False) -> bool:
        """Cria todas as tabelas do schema.

        Args:
            drop_existing: Quando True, remove tabelas antes de recriar.

        Returns:
            True quando a criacao foi concluida.
        """
        conn = None
        try:
            with self.get_connection() as conn:
                if drop_existing:
                    logger.info("Dropping existing tables...")
                    with conn.cursor() as cur:
                        cur.execute(DROP_ALL_TABLES)
                    conn.commit()

                logger.info("Creating %s tables...", len(ALL_TABLES))
                for nome, ddl in ALL_TABLES:
                    with conn.cursor() as cur:
                        cur.execute(ddl)
                    logger.info("Table created: %s", nome)

                conn.commit()
                logger.info("%s tables created successfully", len(ALL_TABLES))
                return True
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error("Failed to create tables: %s", e, exc_info=True)
            return False
    
    # =========================================================================
    # OPERACOES NFE_SAP
    # =========================================================================
    
    def inserir_nf_sap(self, chaves_nf: List[str]) -> int:
        """Insere chaves NF do SAP (upsert)"""
        if not chaves_nf:
            return 0
        
        conn = None
        try:
            query = """
                INSERT INTO nfe_sap (chave_nf, data_importacao, ativo)
                VALUES %s
                ON CONFLICT (chave_nf) DO UPDATE SET
                    data_importacao = CURRENT_TIMESTAMP,
                    ativo = TRUE
            """
            dados = [(chave, datetime.now(), True) for chave in chaves_nf]

            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    execute_values(cur, query, dados)

                conn.commit()
            return len(chaves_nf)
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error("Failed to insert SAP NFs: %s", e, exc_info=True)
            return 0
    
    def obter_nfs_sap(self) -> List[str]:
        """Retorna todas as chaves NF ativas do SAP"""
        query = "SELECT chave_nf FROM nfe_sap WHERE ativo = TRUE"
        result = self.executar_query_retorno(query)
        return [r['chave_nf'] for r in result]
    
    # =========================================================================
    # OPERACOES NF_DUE_VINCULO
    # =========================================================================
    
    def inserir_vinculo_nf_due(self, chave_nf: str, numero_due: str, origem: str = 'SISCOMEX') -> bool:
        """Insere ou atualiza vinculo NF->DUE"""
        conn = None
        try:
            query = """
                INSERT INTO nf_due_vinculo (chave_nf, numero_due, data_vinculo, origem)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (chave_nf) DO UPDATE SET
                    numero_due = EXCLUDED.numero_due,
                    data_vinculo = EXCLUDED.data_vinculo,
                    origem = EXCLUDED.origem
            """
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (chave_nf, numero_due, datetime.now(), origem))
                conn.commit()
            return True
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error("Failed to insert NF-DUE link: %s", e, exc_info=True)
            return False
    
    def inserir_vinculos_batch(self, vinculos: List[Dict]) -> int:
        """Insere multiplos vinculos NF->DUE"""
        if not vinculos:
            return 0
        
        conn = None
        try:
            query = """
                INSERT INTO nf_due_vinculo (chave_nf, numero_due, data_vinculo, origem)
                VALUES %s
                ON CONFLICT (chave_nf) DO UPDATE SET
                    numero_due = EXCLUDED.numero_due,
                    data_vinculo = EXCLUDED.data_vinculo,
                    origem = EXCLUDED.origem
            """
            dados = [
                (v['chave_nf'], v['numero_due'], v.get('data_vinculo', datetime.now()), v.get('origem', 'SISCOMEX'))
                for v in vinculos
            ]

            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    execute_values(cur, query, dados)
                conn.commit()
            return len(vinculos)
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error("Failed to insert NF-DUE links: %s", e, exc_info=True)
            return 0
    
    def obter_vinculos(self) -> Dict[str, str]:
        """Retorna dicionario de vinculos NF->DUE"""
        query = "SELECT chave_nf, numero_due FROM nf_due_vinculo"
        result = self.executar_query_retorno(query)
        return {r['chave_nf']: r['numero_due'] for r in result}
    
    def obter_nfs_sem_vinculo(self) -> List[str]:
        """Retorna NFs do SAP que nao tem vinculo com DUE"""
        query = """
            SELECT s.chave_nf 
            FROM nfe_sap s
            LEFT JOIN nf_due_vinculo v ON s.chave_nf = v.chave_nf
            WHERE s.ativo = TRUE AND v.chave_nf IS NULL
        """
        result = self.executar_query_retorno(query)
        return [r['chave_nf'] for r in result]
    
    # =========================================================================
    # OPERACOES DUE_PRINCIPAL
    # =========================================================================
    
    def inserir_due_principal(self, dados: Dict) -> bool:
        """Insere ou atualiza DUE principal"""
        try:
            # Mapear campos do JSON para colunas do banco
            colunas = [
                'numero', 'chave_de_acesso', 'data_de_registro', 'bloqueio', 'canal',
                'embarque_em_recinto_alfandegado', 'despacho_em_recinto_alfandegado',
                'forma_de_exportacao', 'impedido_de_embarque', 'informacoes_complementares',
                'ruc', 'situacao', 'situacao_do_tratamento_administrativo', 'tipo',
                'tratamento_prioritario', 'responsavel_pelo_acd', 'despacho_em_recinto_domiciliar',
                'data_de_criacao', 'data_do_cce', 'data_do_desembaraco', 'data_do_acd',
                'data_da_averbacao', 'valor_total_mercadoria', 'inclusao_nota_fiscal',
                'exigencia_ativa', 'consorciada', 'dat', 'oea',
                'declarante_numero_do_documento', 'declarante_tipo_do_documento',
                'declarante_nome', 'declarante_estrangeiro', 'declarante_nacionalidade_codigo',
                'declarante_nacionalidade_nome', 'declarante_nacionalidade_nome_resumido',
                'moeda_codigo', 'pais_importador_codigo', 'recinto_aduaneiro_de_despacho_codigo',
                'recinto_aduaneiro_de_embarque_codigo', 'unidade_local_de_despacho_codigo',
                'unidade_local_de_embarque_codigo', 'declaracao_tributaria_divergente',
                'data_ultima_atualizacao'
            ]
            
            valores = [dados.get(col) for col in colunas]
            
            placeholders = ', '.join(['%s'] * len(colunas))
            colunas_str = ', '.join(colunas)
            
            # Construir UPDATE para upsert
            update_parts = [f"{col} = EXCLUDED.{col}" for col in colunas if col != 'numero']
            update_str = ', '.join(update_parts)
            
            query = f"""
                INSERT INTO due_principal ({colunas_str})
                VALUES ({placeholders})
                ON CONFLICT (numero) DO UPDATE SET {update_str}
            """
            
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, valores)
            
            return True
        except Exception as e:
            logger.error("Failed to insert DUE principal: %s", e, exc_info=True)
            return False
    
    def obter_dues_desatualizadas(self, horas: int = 24, ignorar_canceladas: bool = True) -> List[str]:
        """
        Retorna DUEs que nao foram atualizadas nas ultimas X horas.
        
        Args:
            horas: Numero de horas para considerar desatualizada
            ignorar_canceladas: Se True, ignora DUEs com situacao CANCELADA
        
        Returns:
            Lista de numeros de DUE
        """
        if ignorar_canceladas:
            query = """
                SELECT numero FROM due_principal
                WHERE situacao NOT IN %s
                  AND (data_ultima_atualizacao IS NULL 
                       OR data_ultima_atualizacao < %s)
                ORDER BY data_ultima_atualizacao ASC NULLS FIRST
            """
            limite = datetime.now() - timedelta(hours=horas)
            result = self.executar_query_retorno(query, (tuple(SITUACOES_CANCELADAS), limite))
        else:
            query = """
                SELECT numero FROM due_principal
                WHERE data_ultima_atualizacao IS NULL 
                   OR data_ultima_atualizacao < %s
                ORDER BY data_ultima_atualizacao ASC NULLS FIRST
            """
            limite = datetime.now() - timedelta(hours=horas)
            result = self.executar_query_retorno(query, (limite,))
        
        return [r['numero'] for r in result]
    
    def obter_dues_por_situacao(self, situacoes: List[str]) -> List[Dict]:
        """Retorna DUEs filtradas por situacao.

        Args:
            situacoes: Lista de situacoes desejadas.

        Returns:
            Lista de registros de DUE.
        """
        query = """
            SELECT numero, situacao, data_de_registro, data_da_averbacao, data_ultima_atualizacao
            FROM due_principal
            WHERE situacao = ANY(%s)
            ORDER BY data_ultima_atualizacao ASC NULLS FIRST
        """
        return self.executar_query_retorno(query, (situacoes,))
    
    def obter_data_registro(self, numero_due: str) -> Optional[datetime]:
        """Retorna a data_de_registro de uma DUE especifica"""
        query = "SELECT data_de_registro FROM due_principal WHERE numero = %s"
        result = self.executar_query_retorno(query, (numero_due,))
        if result:
            return result[0].get('data_de_registro')
        return None
    
    def obter_todas_dues(self) -> List[str]:
        """Retorna todos os numeros de DUE"""
        query = "SELECT numero FROM due_principal"
        result = self.executar_query_retorno(query)
        return [r['numero'] for r in result]
    
    # =========================================================================
    # INSERCAO DE DADOS NORMALIZADOS (COMPLETA)
    # =========================================================================
    
    def inserir_due_completa(self, dados_normalizados: Dict) -> bool:
        """
        Insere todos os dados normalizados de uma ou mais DUEs.
        Recebe o dicionario com todas as tabelas como chaves.
        """
        conn = None
        try:
            with self.use_connection() as conn:
                # 1. due_principal
                if dados_normalizados.get('due_principal'):
                    for registro in dados_normalizados['due_principal']:
                        self._inserir_due_principal_normalizado(registro)

                # 2. due_eventos_historico
                if dados_normalizados.get('due_eventos_historico'):
                    self._inserir_batch_eventos_historico(dados_normalizados['due_eventos_historico'])

                # 3. due_itens
                if dados_normalizados.get('due_itens'):
                    self._inserir_batch_itens(dados_normalizados['due_itens'])

                # 4. due_item_enquadramentos
                if dados_normalizados.get('due_item_enquadramentos'):
                    self._inserir_batch_generico(
                        'due_item_enquadramentos',
                        dados_normalizados['due_item_enquadramentos'],
                    )

                # 5. due_item_paises_destino
                if dados_normalizados.get('due_item_paises_destino'):
                    self._inserir_batch_generico(
                        'due_item_paises_destino',
                        dados_normalizados['due_item_paises_destino'],
                    )

                # 6. due_item_tratamentos_administrativos
                if dados_normalizados.get('due_item_tratamentos_administrativos'):
                    self._inserir_batch_tratamentos_admin(
                        dados_normalizados['due_item_tratamentos_administrativos'],
                    )

                # 7. due_item_tratamentos_administrativos_orgaos
                if dados_normalizados.get('due_item_tratamentos_administrativos_orgaos'):
                    self._inserir_batch_generico(
                        'due_item_tratamentos_administrativos_orgaos',
                        dados_normalizados['due_item_tratamentos_administrativos_orgaos'],
                    )

                # 8. due_item_notas_remessa
                if dados_normalizados.get('due_item_notas_remessa'):
                    self._inserir_batch_generico(
                        'due_item_notas_remessa',
                        dados_normalizados['due_item_notas_remessa'],
                    )

                # 9. due_item_nota_fiscal_exportacao
                if dados_normalizados.get('due_item_nota_fiscal_exportacao'):
                    self._inserir_batch_nf_exportacao(
                        dados_normalizados['due_item_nota_fiscal_exportacao'],
                    )

                # 10. due_item_notas_complementares
                if dados_normalizados.get('due_item_notas_complementares'):
                    self._inserir_batch_generico(
                        'due_item_notas_complementares',
                        dados_normalizados['due_item_notas_complementares'],
                    )

                # 11. due_item_atributos
                if dados_normalizados.get('due_item_atributos'):
                    self._inserir_batch_generico(
                        'due_item_atributos',
                        dados_normalizados['due_item_atributos'],
                    )

                # 12. due_item_documentos_importacao
                if dados_normalizados.get('due_item_documentos_importacao'):
                    self._inserir_batch_generico(
                        'due_item_documentos_importacao',
                        dados_normalizados['due_item_documentos_importacao'],
                    )

                # 13. due_item_documentos_transformacao
                if dados_normalizados.get('due_item_documentos_transformacao'):
                    self._inserir_batch_generico(
                        'due_item_documentos_transformacao',
                        dados_normalizados['due_item_documentos_transformacao'],
                    )

                # 14. due_item_calculo_tributario_tratamentos
                if dados_normalizados.get('due_item_calculo_tributario_tratamentos'):
                    self._inserir_batch_generico(
                        'due_item_calculo_tributario_tratamentos',
                        dados_normalizados['due_item_calculo_tributario_tratamentos'],
                    )

                # 15. due_item_calculo_tributario_quadros
                if dados_normalizados.get('due_item_calculo_tributario_quadros'):
                    self._inserir_batch_generico(
                        'due_item_calculo_tributario_quadros',
                        dados_normalizados['due_item_calculo_tributario_quadros'],
                    )

                # 16. due_situacoes_carga
                if dados_normalizados.get('due_situacoes_carga'):
                    self._inserir_batch_generico(
                        'due_situacoes_carga',
                        dados_normalizados['due_situacoes_carga'],
                    )

                # 17. due_solicitacoes
                if dados_normalizados.get('due_solicitacoes'):
                    self._inserir_batch_generico(
                        'due_solicitacoes',
                        dados_normalizados['due_solicitacoes'],
                    )

                # 18-20. Declaracao tributaria
                for tabela in [
                    'due_declaracao_tributaria_compensacoes',
                    'due_declaracao_tributaria_recolhimentos',
                    'due_declaracao_tributaria_contestacoes',
                ]:
                    if dados_normalizados.get(tabela):
                        self._inserir_batch_generico(
                            tabela,
                            dados_normalizados[tabela],
                        )

                # 21. due_atos_concessorios_suspensao
                if dados_normalizados.get('due_atos_concessorios_suspensao'):
                    self._inserir_batch_atos_concessorios(
                        'due_atos_concessorios_suspensao',
                        dados_normalizados['due_atos_concessorios_suspensao'],
                    )

                # 22. due_atos_concessorios_isencao
                if dados_normalizados.get('due_atos_concessorios_isencao'):
                    self._inserir_batch_atos_concessorios(
                        'due_atos_concessorios_isencao',
                        dados_normalizados['due_atos_concessorios_isencao'],
                    )

                # 23. due_exigencias_fiscais
                if dados_normalizados.get('due_exigencias_fiscais'):
                    self._inserir_batch_generico(
                        'due_exigencias_fiscais',
                        dados_normalizados['due_exigencias_fiscais'],
                    )

                self.conn.commit()
                return True
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error("Failed to insert full DUE: %s", e, exc_info=True)
            return False
    
    def _limpar_valor(self, valor: Any, tipo_esperado: str = 'string') -> Any:
        """Limpa valores vazios e converte para None quando apropriado"""
        if valor is None:
            return None
        if isinstance(valor, str):
            valor = valor.strip()
            if valor == '' or valor.lower() == 'null':
                return None
            # Se for campo de data/timestamp vazio, retornar None
            if tipo_esperado in ('timestamp', 'datetime', 'date'):
                if valor == '':
                    return None
        return valor
    
    def _inserir_due_principal_normalizado(self, registro: Dict) -> None:
        """Insere registro na due_principal com mapeamento de campos"""
        # Mapeamento de campos do JSON normalizado para colunas do banco
        mapeamento = {
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
            'declarante_numeroDoDocumento': 'declarante_numero_do_documento',
            'declarante_tipoDoDocumento': 'declarante_tipo_do_documento',
            'declarante_nome': 'declarante_nome',
            'declarante_estrangeiro': 'declarante_estrangeiro',
            'declarante_nacionalidade_codigo': 'declarante_nacionalidade_codigo',
            'declarante_nacionalidade_nome': 'declarante_nacionalidade_nome',
            'declarante_nacionalidade_nomeResumido': 'declarante_nacionalidade_nome_resumido',
            'moeda_codigo': 'moeda_codigo',
            'paisImportador_codigo': 'pais_importador_codigo',
            'recintoAduaneiroDeDespacho_codigo': 'recinto_aduaneiro_de_despacho_codigo',
            'recintoAduaneiroDeEmbarque_codigo': 'recinto_aduaneiro_de_embarque_codigo',
            'unidadeLocalDeDespacho_codigo': 'unidade_local_de_despacho_codigo',
            'unidadeLocalDeEmbarque_codigo': 'unidade_local_de_embarque_codigo',
            'declaracaoTributaria_divergente': 'declaracao_tributaria_divergente',
            'data_ultima_atualizacao': 'data_ultima_atualizacao'
        }
        
        # Campos que sao timestamps
        campos_timestamp = [
            'data_de_registro', 'data_de_criacao', 'data_do_cce', 'data_do_desembaraco',
            'data_do_acd', 'data_da_averbacao', 'data_ultima_atualizacao'
        ]
        
        # Construir dados mapeados
        dados_mapeados = {}
        for json_key, db_col in mapeamento.items():
            if json_key in registro:
                valor = registro[json_key]
                # Limpar valores vazios, especialmente em campos timestamp
                if db_col in campos_timestamp:
                    valor = self._limpar_valor(valor, 'timestamp')
                else:
                    valor = self._limpar_valor(valor)
                dados_mapeados[db_col] = valor
        
        # Se nao tem data_ultima_atualizacao, adicionar
        if 'data_ultima_atualizacao' not in dados_mapeados or dados_mapeados['data_ultima_atualizacao'] is None:
            dados_mapeados['data_ultima_atualizacao'] = datetime.utcnow().isoformat()
        
        colunas = list(dados_mapeados.keys())
        valores = list(dados_mapeados.values())
        
        placeholders = ', '.join(['%s'] * len(colunas))
        colunas_str = ', '.join(colunas)
        update_parts = [f"{col} = EXCLUDED.{col}" for col in colunas if col != 'numero']
        update_str = ', '.join(update_parts)
        
        query = f"""
            INSERT INTO due_principal ({colunas_str})
            VALUES ({placeholders})
            ON CONFLICT (numero) DO UPDATE SET {update_str}
        """
        
        with self.conn.cursor() as cur:
            cur.execute(query, valores)
    
    def _inserir_batch_eventos_historico(self, registros: List[Dict]) -> None:
        """Insere eventos do historico (deleta existentes e reinsere)"""
        if not registros:
            return
        
        # Obter DUEs unicas
        dues = set(r.get('numero_due') for r in registros if r.get('numero_due'))
        
        # Deletar eventos existentes dessas DUEs
        with self.conn.cursor() as cur:
            cur.execute(
                "DELETE FROM due_eventos_historico WHERE numero_due = ANY(%s)",
                (list(dues),)
            )
        
        # Inserir novos
        # NOTA: Campos removidos (não existem na API Siscomex): detalhes, motivo, tipo_evento, data
        colunas = ['numero_due', 'data_e_hora_do_evento', 'evento', 'responsavel', 'informacoes_adicionais']

        dados = []
        for r in registros:
            dados.append((
                r.get('numero_due'),
                self._limpar_valor(r.get('dataEHoraDoEvento'), 'timestamp'),
                self._limpar_valor(r.get('evento')),
                self._limpar_valor(r.get('responsavel')),
                self._limpar_valor(r.get('informacoesAdicionais'))
            ))
        
        query = f"""
            INSERT INTO due_eventos_historico ({', '.join(colunas)})
            VALUES %s
        """
        
        with self.conn.cursor() as cur:
            execute_values(cur, query, dados)
    
    def _inserir_batch_itens(self, registros: List[Dict]) -> None:
        """Insere itens da DUE"""
        if not registros:
            return
        
        colunas = [
            'id', 'numero_due', 'numero_item', 'quantidade_na_unidade_estatistica',
            'peso_liquido_total', 'valor_da_mercadoria_na_condicao_de_venda',
            'valor_da_mercadoria_no_local_de_embarque', 
            'valor_da_mercadoria_no_local_de_embarque_em_reais',
            'valor_da_mercadoria_na_condicao_de_venda_em_reais', 'data_de_conversao',
            'descricao_da_mercadoria', 'unidade_comercializada', 'nome_importador',
            'endereco_importador', 'valor_total_calculado_item',
            'quantidade_na_unidade_comercializada', 'ncm_codigo', 'ncm_descricao',
            'ncm_unidade_medida_estatistica', 'exportador_numero_do_documento',
            'exportador_tipo_do_documento', 'exportador_nome', 'exportador_estrangeiro',
            'exportador_nacionalidade_codigo', 'exportador_nacionalidade_nome',
            'exportador_nacionalidade_nome_resumido', 'codigo_condicao_venda',
            'exportacao_temporaria'
        ]
        
        dados = []
        for r in registros:
            # Obter numero_item (pode vir como numeroItem ou numero_item)
            numero_item = r.get('numeroItem') or r.get('numero_item') or 0
            if numero_item == 0:
                # Tentar extrair do indice se disponivel
                numero_item = r.get('numero', 0) or 0
            
            # Criar ID: numero_due + _ + numero_item
            item_id = f"{r.get('numero_due')}_{numero_item}"
            dados.append((
                item_id,
                r.get('numero_due'),
                numero_item,
                r.get('quantidadeNaUnidadeEstatistica'),
                r.get('pesoLiquidoTotal'),
                r.get('valorDaMercadoriaNaCondicaoDeVenda'),
                r.get('valorDaMercadoriaNoLocalDeEmbarque'),
                r.get('valorDaMercadoriaNoLocalDeEmbarqueEmReais'),
                r.get('valorDaMercadoriaNaCondicaoDeVendaEmReais'),
                self._limpar_valor(r.get('dataDeConversao'), 'timestamp'),
                r.get('descricaoDaMercadoria'),
                r.get('unidadeComercializada'),
                r.get('nomeImportador'),
                r.get('enderecoImportador'),
                r.get('valorTotalCalculadoItem'),
                r.get('quantidadeNaUnidadeComercializada'),
                r.get('ncm_codigo'),
                r.get('ncm_descricao'),
                r.get('ncm_unidadeMedidaEstatistica'),
                r.get('exportador_numeroDoDocumento'),
                r.get('exportador_tipoDoDocumento'),
                r.get('exportador_nome'),
                r.get('exportador_estrangeiro'),
                r.get('exportador_nacionalidade_codigo'),
                r.get('exportador_nacionalidade_nome'),
                r.get('exportador_nacionalidade_nomeResumido'),
                r.get('codigoCondicaoVenda'),
                r.get('exportacaoTemporaria')
            ))
        
        # Upsert
        update_parts = [f"{col} = EXCLUDED.{col}" for col in colunas if col != 'id']
        update_str = ', '.join(update_parts)
        
        query = f"""
            INSERT INTO due_itens ({', '.join(colunas)})
            VALUES %s
            ON CONFLICT (id) DO UPDATE SET {update_str}
        """
        
        with self.conn.cursor() as cur:
            execute_values(cur, query, dados)
    
    def _inserir_batch_tratamentos_admin(self, registros: List[Dict]) -> None:
        """Insere tratamentos administrativos"""
        if not registros:
            return
        
        colunas = ['id', 'due_item_id', 'numero_due', 'numero_item', 'mensagem',
                   'impeditivo_de_embarque', 'codigo_lpco', 'situacao']
        
        dados = []
        for r in registros:
            # Obter numero_item (pode vir como numeroItem ou numero_item)
            numero_item = r.get('numeroItem') or r.get('numero_item') or r.get('item_numero') or 0
            if numero_item == 0:
                numero_item = r.get('numero', 0) or 0
            
            # ID do tratamento: numero_due_item_indice
            trat_id = r.get('id', f"{r.get('numero_due')}_{numero_item}_{len(dados)}")
            item_id = f"{r.get('numero_due')}_{numero_item}"
            dados.append((
                trat_id,
                item_id,
                r.get('numero_due'),
                numero_item,
                r.get('mensagem'),
                r.get('impeditivoDeEmbarque'),
                r.get('codigoLPCO'),
                r.get('situacao')
            ))
        
        update_parts = [f"{col} = EXCLUDED.{col}" for col in colunas if col != 'id']
        update_str = ', '.join(update_parts)
        
        query = f"""
            INSERT INTO due_item_tratamentos_administrativos ({', '.join(colunas)})
            VALUES %s
            ON CONFLICT (id) DO UPDATE SET {update_str}
        """
        
        with self.conn.cursor() as cur:
            execute_values(cur, query, dados)
    
    def _inserir_batch_nf_exportacao(self, registros: List[Dict]) -> None:
        """Insere notas fiscais de exportacao"""
        if not registros:
            return
        
        colunas = [
            'due_item_id', 'numero_due', 'numero_item', 'numero_do_item', 'chave_de_acesso',
            'modelo', 'serie', 'numero_do_documento', 'uf_do_emissor',
            'identificacao_emitente', 'emitente_cnpj', 'emitente_cpf', 'finalidade',
            'quantidade_de_itens', 'nota_fiscal_eletronica', 'cfop', 'codigo_do_produto',
            'descricao', 'quantidade_estatistica', 'unidade_comercial',
            'valor_total_calculado', 'ncm_codigo', 'ncm_descricao',
            'ncm_unidade_medida_estatistica', 'apresentada_para_despacho'
        ]
        
        dados = []
        for r in registros:
            # Obter numero_item (pode vir como numeroItem, numero_item, ou item_numero)
            numero_item = r.get('numeroItem') or r.get('numero_item') or r.get('item_numero')
            if numero_item is None or numero_item == 0:
                numero_item = r.get('numero')
            # Garantir que numero_item seja sempre um inteiro válido (nunca None)
            if numero_item is None:
                numero_item = 0
            else:
                try:
                    numero_item = int(numero_item)
                except (ValueError, TypeError):
                    numero_item = 0
            
            item_id = f"{r.get('numero_due')}_{numero_item}"
            dados.append((
                item_id,
                r.get('numero_due'),
                numero_item,
                r.get('numeroDoItem'),
                r.get('chaveDeAcesso'),
                r.get('modelo'),
                r.get('serie'),
                r.get('numeroDoDocumento'),
                r.get('ufDoEmissor'),
                r.get('identificacao_emitente'),
                r.get('emitente_cnpj'),
                r.get('emitente_cpf'),
                r.get('finalidade'),
                r.get('quantidadeDeItens'),
                r.get('notaFiscalEletronica'),
                r.get('cfop'),
                r.get('codigoDoProduto'),
                r.get('descricao'),
                r.get('quantidadeEstatistica'),
                r.get('unidadeComercial'),
                r.get('valorTotalCalculado'),
                r.get('ncm_codigo'),
                r.get('ncm_descricao'),
                r.get('ncm_unidadeMedidaEstatistica'),
                r.get('apresentadaParaDespacho')
            ))
        
        update_parts = [f"{col} = EXCLUDED.{col}" for col in colunas if col != 'due_item_id']
        update_str = ', '.join(update_parts)
        
        query = f"""
            INSERT INTO due_item_nota_fiscal_exportacao ({', '.join(colunas)})
            VALUES %s
            ON CONFLICT (due_item_id) DO UPDATE SET {update_str}
        """
        
        with self.conn.cursor() as cur:
            execute_values(cur, query, dados)
    
    def _inserir_batch_generico(self, tabela: str, registros: List[Dict]) -> None:
        """Insere registros de forma generica em tabelas com SERIAL id"""
        if not registros:
            return
        
        # Obter DUEs unicas para deletar registros antigos
        dues = set(r.get('numero_due') for r in registros if r.get('numero_due'))
        
        if dues:
            with self.conn.cursor() as cur:
                cur.execute(
                    f"DELETE FROM {tabela} WHERE numero_due = ANY(%s)",
                    (list(dues),)
                )
        
        # Obter colunas do primeiro registro (exceto 'id' se for serial)
        if not registros:
            return
        
        # Mapeamento de colunas JSON para banco
        mapeamento_colunas = {
            'numeroItem': 'numero_item',
            'item_numero': 'numero_item',  # Mapeamento alternativo
            'codigoPaisDestino': 'codigo_pais_destino',
            'codigo_pais': 'codigo_pais_destino',  # Mapeamento alternativo
            'chaveDeAcesso': 'chave_de_acesso',
            'dataEHoraDoEvento': 'data_e_hora_do_evento',
            'informacoesAdicionais': 'informacoes_adicionais',
            'tipoEvento': 'tipo_evento',
            'numeroDoItem': 'numero_do_item',
            'codigoDoProduto': 'codigo_do_produto',
            'quantidadeEstatistica': 'quantidade_estatistica',
            'unidadeComercial': 'unidade_comercial',
            'valorTotalBruto': 'valor_total_bruto',
            'quantidadeConsumida': 'quantidade_consumida',
            'ncm_unidadeMedidaEstatistica': 'ncm_unidade_medida_estatistica',
            'numeroDoDocumento': 'numero_do_documento',
            'ufDoEmissor': 'uf_do_emissor',
            'identificacao_emitente': 'identificacao_emitente',
            'apresentadaParaDespacho': 'apresentada_para_despacho',
            'quantidadeDeItens': 'quantidade_de_itens',
            'notaFiscalEletronica': 'nota_fiscal_eletronica',
            'emitente_cnpj': 'emitente_cnpj',
            'emitente_cpf': 'emitente_cpf',
            'tipoSolicitacao': 'tipo_solicitacao',
            'dataDaSolicitacao': 'data_da_solicitacao',
            'usuarioResponsavel': 'usuario_responsavel',
            'codigoDoStatusDaSolicitacao': 'codigo_do_status_da_solicitacao',
            'statusDaSolicitacao': 'status_da_solicitacao',
            'dataDeApreciacao': 'data_de_apreciacao',
            'cargaOperada': 'carga_operada',
            'impeditivoDeEmbarque': 'impeditivo_de_embarque',
            'codigoLPCO': 'codigo_lpco',
            'codigoOrgao': 'codigo_orgao',
            'orgao': 'codigo_orgao',  # Mapeamento alternativo
            'dataRegistro': 'data_registro',
            'baseDeCalculo': 'base_de_calculo',
            'valorDevido': 'valor_devido',
            'valorRecolhido': 'valor_recolhido',
            'valorCompensado': 'valor_compensado',
            'dataDoRegistro': 'data_do_registro',
            'numeroDaDeclaracao': 'numero_da_declaracao',
            'dataDoPagamento': 'data_do_pagamento',
            'valorDaMulta': 'valor_da_multa',
            'valorDoImpostoRecolhido': 'valor_do_imposto_recolhido',
            'valorDosJurosMora': 'valor_dos_juros_mora',
            'codigoReceita': 'codigo_receita',
            'itemDocumento': 'item_documento',
            'quantidadeUtilizada': 'quantidade_utilizada'
        }
        
        # Pegar colunas do primeiro registro
        primeiro = registros[0]
        colunas_json = [k for k in primeiro.keys() if k not in ('id',)]
        
        # Mapear para nomes do banco
        colunas_db = []
        for col in colunas_json:
            db_col = mapeamento_colunas.get(col, col)
            colunas_db.append(db_col)
        
        # Preparar dados
        dados = []
        for r in registros:
            valores = []
            for col in colunas_json:
                valor = r.get(col)
                # Limpar valores vazios
                if isinstance(valor, str) and valor.strip() == '':
                    valor = None
                valores.append(valor)
            dados.append(tuple(valores))
        
        # Construir query
        colunas_str = ', '.join(colunas_db)
        query = f"""
            INSERT INTO {tabela} ({colunas_str})
            VALUES %s
        """
        
        with self.conn.cursor() as cur:
            execute_values(cur, query, dados)
    
    # =========================================================================
    # OPERACOES TABELAS DE SUPORTE
    # =========================================================================
    
    def inserir_suporte_batch(self, tabela: str, registros: List[Dict], pk_col: str = 'codigo') -> int:
        """Insere registros em tabela de suporte com upsert.

        Args:
            tabela: Nome da tabela de suporte.
            registros: Registros para inserir.
            pk_col: Coluna de chave primaria.

        Returns:
            Quantidade inserida.
        """
        if not registros:
            return 0
        
        conn = None
        try:
            # Obter colunas do primeiro registro
            colunas = list(registros[0].keys())

            # Preparar dados
            dados = [tuple(r.get(col) for col in colunas) for r in registros]

            # Construir query com upsert
            colunas_str = ', '.join(colunas)
            placeholders = ', '.join(['%s'] * len(colunas))
            update_parts = [f"{col} = EXCLUDED.{col}" for col in colunas if col != pk_col]
            update_str = ', '.join(update_parts)

            query = f"""
                INSERT INTO {tabela} ({colunas_str})
                VALUES %s
                ON CONFLICT ({pk_col}) DO UPDATE SET {update_str}
            """

            with self.use_connection() as conn:
                with self.conn.cursor() as cur:
                    execute_values(cur, query, dados)

                self.conn.commit()
            return len(registros)
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error("Failed to insert into %s: %s", tabela, e, exc_info=True)
            return 0
    
    def _inserir_batch_atos_concessorios(self, tabela: str, registros: List[Dict]) -> None:
        """Insere registros de atos concessórios com mapeamento específico"""
        if not registros:
            return
        
        # Obter DUEs únicas para deletar registros antigos
        dues = set(r.get('numero_due') for r in registros if r.get('numero_due'))
        
        if dues:
            with self.conn.cursor() as cur:
                cur.execute(
                    f"DELETE FROM {tabela} WHERE numero_due = ANY(%s)",
                    (list(dues),)
                )
        
        # Mapeamento específico para atos concessórios
        mapeamento = {
            'numero_due': 'numero_due',
            'ato_numero': 'ato_numero',
            'tipo_codigo': 'tipo_codigo',
            'tipo_descricao': 'tipo_descricao',
            'item_numero': 'item_numero',
            'item_ncm': 'item_ncm',
            'beneficiario_cnpj': 'beneficiario_cnpj',
            'quantidadeExportada': 'quantidade_exportada',
            'valorComCoberturaCambial': 'valor_com_cobertura_cambial',
            'valorSemCoberturaCambial': 'valor_sem_cobertura_cambial',
            'itemDeDUE_numero': 'item_de_due_numero',
        }
        
        # Preparar dados com mapeamento
        dados_mapeados = []
        for registro in registros:
            dados_linha = {}
            for json_key, db_col in mapeamento.items():
                if json_key in registro:
                    valor = registro[json_key]
                    # Converter tipos numéricos
                    if 'valor' in db_col or 'quantidade' in db_col:
                        try:
                            valor = float(valor) if valor else 0
                        except:
                            valor = 0
                    dados_linha[db_col] = valor
            dados_mapeados.append(dados_linha)
        
        if not dados_mapeados:
            return
        
        # Inserir em batch
        from psycopg2.extras import execute_values
        
        colunas = list(dados_mapeados[0].keys())
        valores = [[linha.get(col) for col in colunas] for linha in dados_mapeados]
        
        colunas_str = ', '.join(colunas)
        placeholders = ', '.join(['%s'] * len(colunas))
        
        query = f"INSERT INTO {tabela} ({colunas_str}) VALUES %s"
        
        try:
            with self.conn.cursor() as cur:
                execute_values(cur, query, valores)
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            logger.error("Failed to insert concession acts into %s: %s", tabela, e, exc_info=True)
            raise
    
    # =========================================================================
    # ATUALIZACAO EM BATCH
    # =========================================================================
    
    def atualizar_data_ultima_atualizacao_batch(self, numeros_due: List[str]) -> int:
        """
        Atualiza data_ultima_atualizacao para múltiplas DUEs de uma vez.
        Processa em lotes menores para evitar problemas de conexão.

        Args:
            numeros_due: Lista de números de DUE para atualizar

        Returns:
            Número de DUEs atualizadas
        """
        if not numeros_due:
            return 0

        started_with_conn = self.conn is not None
        try:
            # Verificar/reconectar se necessário
            try:
                if not self.conn:
                    if not self.conectar():
                        logger.error("Could not connect to database")
                        return 0
                # Testar conexão fazendo uma query simples
                with self.conn.cursor() as cur:
                    cur.execute("SELECT 1")
            except (psycopg2.InterfaceError, psycopg2.OperationalError):
                # Conexão fechada ou inválida, reconectar
                if not self.conectar():
                    logger.error("Could not reconnect to database")
                    return 0

            total_atualizado = 0
            tamanho_lote = 50  # Processar em lotes de 50 para evitar problemas de conexão

            try:
                agora = datetime.utcnow().isoformat()

                # Processar em lotes
                for i in range(0, len(numeros_due), tamanho_lote):
                    lote = numeros_due[i:i + tamanho_lote]

                    try:
                        # Verificar conexão antes de cada lote
                        try:
                            with self.conn.cursor() as test_cur:
                                test_cur.execute("SELECT 1")
                        except (psycopg2.InterfaceError, psycopg2.OperationalError):
                            # Conexão fechada, reconectar
                            if not self.conectar():
                                logger.error("Connection closed, failed to reconnect")
                                break

                        query = """
                            UPDATE due_principal
                            SET data_ultima_atualizacao = %s
                            WHERE numero = ANY(%s)
                        """

                        with self.conn.cursor() as cur:
                            cur.execute(query, (agora, lote))
                            count = cur.rowcount
                            total_atualizado += count

                        self.conn.commit()

                        # Pequeno delay entre lotes para não sobrecarregar o servidor
                        time.sleep(0.1)

                    except Exception as e:
                        # Tentar rollback apenas se conexão ainda estiver aberta
                        try:
                            if self.conn:
                                self.conn.rollback()
                        except:
                            pass

                        logger.error(
                            "Failed to update batch %s: %s",
                            i // tamanho_lote + 1,
                            e,
                            exc_info=True,
                        )
                        # Tentar reconectar para próximo lote
                        try:
                            with self.conn.cursor() as test_cur:
                                test_cur.execute("SELECT 1")
                        except (psycopg2.InterfaceError, psycopg2.OperationalError):
                            if not self.conectar():
                                logger.error("Failed to reconnect, stopping batch update")
                                break

                return total_atualizado

            except Exception as e:
                # Tentar rollback apenas se conexão ainda estiver aberta
                try:
                    if self.conn:
                        self.conn.rollback()
                except:
                    pass
                logger.error(
                    "Failed to update data_ultima_atualizacao in batch: %s",
                    e,
                    exc_info=True,
                )
                return total_atualizado
        finally:
            if not started_with_conn:
                self.desconectar()
    
    # =========================================================================
    # ESTATISTICAS
    # =========================================================================
    
    def obter_estatisticas(self) -> Dict[str, int]:
        """Retorna estatisticas das tabelas principais"""
        tabelas = [
            'nfe_sap', 'nf_due_vinculo', 'due_principal', 'due_itens',
            'due_eventos_historico', 'due_item_nota_fiscal_exportacao'
        ]
        
        stats = {}
        for tabela in tabelas:
            try:
                result = self.executar_query_retorno(f"SELECT COUNT(*) as cnt FROM {tabela}")
                stats[tabela] = result[0]['cnt'] if result else 0
            except:
                stats[tabela] = -1
        
        return stats


# Instancia global
db_manager = DatabaseManager()


if __name__ == "__main__":
    # Teste de conexao
    logger.info("=== DatabaseManager self-test ===")
    
    if db_manager.conectar():
        logger.info("Testing table creation...")
        # Nao criar tabelas no teste direto
        # db_manager.criar_tabelas()
        
        logger.info("Statistics:")
        stats = db_manager.obter_estatisticas()
        for tabela, count in stats.items():
            logger.info("%s: %s registros", tabela, count)
        
        db_manager.desconectar()
    else:
        logger.error("Could not connect to database")
