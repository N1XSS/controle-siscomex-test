"""
Sincronizacao de Novas DUEs - OTIMIZADO
========================================

Este servico identifica NFs de exportacao do SAP que ainda nao possuem
DUE vinculada e consulta o Siscomex para obter os dados.

Otimizacoes:
- Cache de vinculos NF->DUE no PostgreSQL (nao reconsulta NFs ja vinculadas)
- Agrupa NFs por DUE para evitar requisicoes duplicadas
- Consulta dados adicionais (drawback suspensao/isencao, exigencias)
- Rate limiting inteligente com pausa automatica ao detectar PUCX-ER1001

Rate Limiting (docs.portalunico.siscomex.gov.br):
- Limite: 1000 requisicoes/hora por funcionalidade
- Bloqueio progressivo: 1a violacao = ate fim da hora, 2a = +1h, 3a+ = +2h
- Sistema pausa automaticamente e retoma apos desbloqueio

Uso:
    python -m src.sync.new_dues              # Processa todas (sem limite)
    python -m src.sync.new_dues --limit 200  # Limita a 200 NFs
"""

from __future__ import annotations

import argparse
import os
import time
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any

import pandas as pd
from dotenv import load_dotenv

from src.core.constants import (
    DEFAULT_HTTP_TIMEOUT_SEC,
    DUE_DOWNLOAD_WORKERS,
    ENABLE_PARALLEL_DOWNLOADS,
    ENV_CONFIG_FILE,
    SISCOMEX_FETCH_ATOS_ISENCAO,
    SISCOMEX_FETCH_ATOS_SUSPENSAO,
    SISCOMEX_FETCH_EXIGENCIAS_FISCAIS,
)
from src.database.manager import db_manager
from src.core.logger import logger
from src.core.metrics import timed
from src.core.exceptions import (
    ConfigurationError,
    ControleSiscomexError,
    DUEProcessingError,
    RateLimitError,
    SiscomexAPIError,
)
from src.api.siscomex.token import token_manager
from src.processors.due import (
    consultar_due_por_nf,
    consultar_due_completa,
    processar_dados_due,
    salvar_resultados_normalizados,
)
from src.notifications.whatsapp import notify_sync_complete_detailed

warnings.filterwarnings("ignore")
load_dotenv(ENV_CONFIG_FILE)

# Flag para usar PostgreSQL (OBRIGATÓRIO)
USAR_POSTGRESQL = True

# URL base da API
URL_DUE_BASE = "https://portalunico.siscomex.gov.br/due/api/ext/due"


def buscar_dados_complementares(
    numero_due: str,
    tipo: str,
    url: str,
) -> dict | list | None:
    """Busca dados complementares da DUE (atos concessórios ou exigências fiscais).

    Args:
        numero_due: Número da DUE
        tipo: Tipo de dados ('atos_suspensao', 'atos_isencao', 'exigencias_fiscais')
        url: URL completa do endpoint

    Returns:
        Dados JSON retornados pela API ou None em caso de erro
    """
    try:
        response = token_manager.request(
            "GET",
            url,
            headers=token_manager.obter_headers(),
            timeout=DEFAULT_HTTP_TIMEOUT_SEC,
        )
        if response.status_code == 200:
            dados = response.json()
            return dados
        else:
            logger.warning(
                f"[AVISO] Falha ao buscar {tipo} para DUE {numero_due}: "
                f"HTTP {response.status_code}"
            )
            return None
    except RateLimitError:
        # Propagar rate limit para salvar dados parciais
        raise
    except Exception as e:
        logger.warning(f"[AVISO] Erro ao buscar {tipo}: {e}")
        return None


@timed
def carregar_nfs_sap() -> list[str]:
    """Carrega as chaves NF do PostgreSQL.

    Returns:
        Lista de chaves NF.

    Raises:
        RuntimeError: Se não conseguir conectar ao PostgreSQL.
    """
    if not db_manager.conectar():
        raise RuntimeError("[ERRO] Nao foi possivel conectar ao PostgreSQL")

    try:
        chaves = db_manager.obter_nfs_sap()
        if chaves:
            logger.info(f"[INFO] {len(chaves)} chaves NF carregadas do PostgreSQL")
            return chaves
        else:
            logger.warning("[AVISO] Nenhuma NF encontrada no PostgreSQL")
            logger.info("[INFO] Execute primeiro: python -m src.api.athena.client")
            return []
    except Exception as e:
        logger.error(f"[ERRO] Erro ao carregar NFs do PostgreSQL: {e}")
        raise


@timed
def carregar_vinculos_existentes() -> dict[str, str]:
    """Carrega vinculos NF->DUE existentes.

    Returns:
        Dicionario {chave_nf: numero_due}.
    """
    if not db_manager.conectar():
        logger.warning("[AVISO] Nao foi possivel conectar ao PostgreSQL")
        return {}

    try:
        vinculos = db_manager.obter_vinculos()
        if vinculos:
            logger.info(f"[INFO] {len(vinculos)} vinculos existentes carregados")
            return vinculos
    except Exception as e:
        logger.warning(f"[AVISO] Erro ao carregar vinculos: {e}")
    
    return {}


@timed
def salvar_novos_vinculos(novos_vinculos: dict[str, str]) -> None:
    """Salva novos vinculos NF->DUE no PostgreSQL com retry e reconexão.

    Args:
        novos_vinculos: Mapa {chave_nf: numero_due}.

    Raises:
        RuntimeError: Se não conseguir salvar após todas as tentativas.
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

    # Tentar salvar no PostgreSQL com retry e reconexão
    max_tentativas = 3
    for tentativa in range(max_tentativas):
        try:
            if not db_manager.conectar():
                logger.warning(f"[AVISO] Falha ao conectar (tentativa {tentativa + 1})")
                if tentativa < max_tentativas - 1:
                    time.sleep(2)
                    continue
                raise RuntimeError("Nao foi possivel conectar ao banco apos todas as tentativas")

            # Tentar inserir
            count = db_manager.inserir_vinculos_batch(registros)
            if count > 0:
                logger.info(f"[OK] {count} novos vinculos salvos no PostgreSQL")
                return
            else:
                logger.warning(f"[AVISO] Nenhum vinculo foi salvo (tentativa {tentativa + 1})")

        except Exception as e:
            logger.warning(f"[AVISO] Erro ao salvar vinculos (tentativa {tentativa + 1}/{max_tentativas}): {e}")
            if tentativa < max_tentativas - 1:
                time.sleep(2)
                continue
            else:
                raise RuntimeError(f"Falha ao salvar vinculos apos {max_tentativas} tentativas: {e}") from e


@timed
def consultar_dados_adicionais(numero_due: str) -> tuple[Any, Any, Any]:
    """Consulta dados adicionais de uma DUE (drawback, exigencias)"""
    atos_suspensao = None
    atos_isencao = None
    exigencias_fiscais = None

    # Atos de suspensao
    if SISCOMEX_FETCH_ATOS_SUSPENSAO:
        url = f"{URL_DUE_BASE}/{numero_due}/drawback/suspensao/atos-concessorios"
        atos_suspensao = buscar_dados_complementares(
            numero_due, "atos de suspensao", url
        )

    # Atos de isencao
    if SISCOMEX_FETCH_ATOS_ISENCAO:
        url = f"{URL_DUE_BASE}/{numero_due}/drawback/isencao/atos-concessorios"
        atos_isencao = buscar_dados_complementares(
            numero_due, "atos de isencao", url
        )

    # Exigencias fiscais
    if SISCOMEX_FETCH_EXIGENCIAS_FISCAIS:
        url = f"{URL_DUE_BASE}/{numero_due}/exigencias-fiscais"
        exigencias_fiscais = buscar_dados_complementares(
            numero_due, "exigencias fiscais", url
        )

    return atos_suspensao, atos_isencao, exigencias_fiscais


def baixar_due_completa(numero_due: str) -> dict[str, Any] | None:
    """
    Baixa uma DUE completa com todos os dados adicionais.

    Esta função é usada para processamento paralelo de DUEs.

    Args:
        numero_due: Número da DUE a ser baixada

    Returns:
        Dicionário com dados normalizados da DUE ou None em caso de erro

    Raises:
        RateLimitError: Se o rate limit da API for atingido (429)
    """
    try:
        # Consultar DUE principal
        dados_due = consultar_due_completa(numero_due)

        if not dados_due:
            return None

        # Consultar dados adicionais
        atos_susp, atos_isen, exig = consultar_dados_adicionais(numero_due)

        # Processar dados
        dados_norm = processar_dados_due(dados_due, atos_susp, atos_isen, exig)

        return dados_norm

    except RateLimitError:
        # Propagar rate limit para que o chamador possa salvar dados parciais
        raise
    except Exception as e:
        logger.warning(f"Erro ao baixar DUE {numero_due}: {e}")
        return None


def _salvar_dados_parciais(dados_consolidados: dict, motivo: str) -> int:
    """
    Salva dados parciais no banco quando há interrupção.

    Args:
        dados_consolidados: Dados já baixados para salvar
        motivo: Motivo da interrupção (ex: "rate limit", "interrupcao manual")

    Returns:
        Número de DUEs salvas
    """
    # Contar DUEs nos dados
    dues_pendentes = len(dados_consolidados.get('due_principal', []))

    if dues_pendentes == 0:
        logger.info(f"[INFO] Nenhum dado para salvar ({motivo})")
        return 0

    logger.warning(f"\n{'='*60}")
    logger.warning(f"⚠️ SALVANDO DADOS PARCIAIS ({motivo})")
    logger.warning(f"{'='*60}")
    logger.info(f"[INFO] {dues_pendentes} DUEs pendentes para salvar...")

    try:
        salvas, erros = salvar_resultados_normalizados(dados_consolidados)
        logger.info(f"[OK] {salvas} DUEs salvas com sucesso, {erros} erros")
        return salvas
    except Exception as e:
        logger.error(f"[ERRO] Falha ao salvar dados parciais: {e}")
        return 0


@timed
def processar_novas_nfs() -> None:
    """Processa NFs do SAP que ainda nao tem DUE vinculada"""
    # Variaveis para rastreamento de erros e estatisticas
    inicio_execucao = datetime.now()
    erros_coletados: list[str] = []
    avisos_coletados: list[str] = []
    dues_salvas_banco = 0

    try:
        parser = argparse.ArgumentParser(description='Sincronizar novas NFs com DUEs')
        parser.add_argument('--limit', type=int, default=0,
                        help='Limite de NFs para consultar (0 = sem limite, processa todas)')
        parser.add_argument('--workers', type=int, default=5,
                        help='Numero de workers paralelos para consultas (default: 5)')
        parser.add_argument('--workers-download', type=int, default=DUE_DOWNLOAD_WORKERS,
                        help=f'Numero de workers paralelos para download de DUEs (default: {DUE_DOWNLOAD_WORKERS})')
        args = parser.parse_args()

        logger.info("=" * 60)
        logger.info("SINCRONIZACAO DE NOVAS DUEs")
        logger.info("=" * 60)
        logger.info(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        logger.info("=" * 60)
        logger.info("")
        
        # Conectar ao PostgreSQL
        if USAR_POSTGRESQL:
            if not db_manager.conectar():
                logger.warning("[AVISO] Nao foi possivel conectar ao PostgreSQL")
        
        # 1. Carregar NFs do SAP
        nfs_sap = carregar_nfs_sap()
        if not nfs_sap:
            logger.warning("[AVISO] Nenhuma NF encontrada no SAP")
            return
        
        # 2. Carregar vinculos existentes (CACHE)
        vinculos_existentes = carregar_vinculos_existentes()
        
        # 3. Identificar NFs que AINDA NAO tem vinculo
        nfs_sem_vinculo = [nf for nf in nfs_sap if nf not in vinculos_existentes]
        
        logger.info(f"\n[CACHE] NFs do SAP: {len(nfs_sap)}")
        logger.info(f"[CACHE] Vinculos existentes: {len(vinculos_existentes)}")
        logger.info(f"[CACHE] NFs sem vinculo: {len(nfs_sem_vinculo)}")
        
        if not nfs_sem_vinculo:
            logger.info("\n[OK] Todas as NFs ja possuem DUE vinculada!")
            logger.info("[INFO] Cache 100% efetivo - nenhuma requisicao necessaria")
            return
        
        # 4. Autenticar no Siscomex
        logger.info("\n[INFO] Autenticando no Siscomex...")
        client_id = os.getenv('SISCOMEX_CLIENT_ID')
        client_secret = os.getenv('SISCOMEX_CLIENT_SECRET')
        
        if not client_id or not client_secret:
            raise ConfigurationError(
                "Credenciais SISCOMEX_CLIENT_ID e SISCOMEX_CLIENT_SECRET nao configuradas"
            )
        
        token_manager.configurar_credenciais(client_id, client_secret)
        
        if not token_manager.autenticar():
            raise SiscomexAPIError("Falha na autenticacao")
        
        logger.info("[OK] Autenticado com sucesso!")

        # 5. Validar imports (já importados no topo do arquivo)
        # Imports movidos para o escopo global para evitar NameError em funções paralelas

        # 6. Consultar DUEs para NFs sem vinculo
        novos_vinculos = {}
        dues_para_baixar = set()

        # Se limit=0, processa todas as NFs (confia no rate limiting inteligente)
        max_consultas = args.limit if args.limit > 0 else len(nfs_sem_vinculo)
        logger.info(f"\n[INFO] Consultando DUEs para {max_consultas} NFs...")
        if args.limit == 0:
            logger.info("[INFO] Modo sem limite ativado - rate limiting inteligente controlara pausas")
        
        nfs_sem_due_encontrada = 0
        
        def consultar_nf(chave: str) -> tuple[str, str | None]:
            resultado = consultar_due_por_nf(chave)
            if isinstance(resultado, dict) and resultado:
                numero = resultado.get('DU-E') or resultado.get('numero')
            else:
                numero = None
            return chave, numero

        with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
            future_to_nf = {
                executor.submit(consultar_nf, chave_nf): chave_nf
                for chave_nf in nfs_sem_vinculo[:max_consultas]
            }

            for i, future in enumerate(as_completed(future_to_nf), 1):
                if i % 50 == 0 or i == max_consultas:
                    logger.info(f"  [PROGRESSO] {i}/{max_consultas} NFs consultadas...")

                chave_nf, numero_due = future.result()
                if numero_due:
                    novos_vinculos[chave_nf] = numero_due
                    dues_para_baixar.add(numero_due)
                else:
                    nfs_sem_due_encontrada += 1
        
        logger.info(f"\n[INFO] {len(novos_vinculos)} novos vinculos encontrados")
        logger.info(f"[INFO] {nfs_sem_due_encontrada} NFs sem DUE no Siscomex")
        logger.info(f"[INFO] {len(dues_para_baixar)} DUEs unicas para baixar")
        
        # 7. Salvar novos vinculos
        if novos_vinculos:
            salvar_novos_vinculos(novos_vinculos)
        
        # 8. Baixar dados completos das DUEs novas
        if dues_para_baixar:
            logger.info(f"\n[INFO] Baixando dados de {len(dues_para_baixar)} DUEs...")
            
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
            rate_limit_atingido = False
            interrupcao_manual = False

            # Usar processamento paralelo se habilitado
            try:
                if ENABLE_PARALLEL_DOWNLOADS and len(dues_para_baixar) > 1:
                    max_workers = max(1, args.workers_download)
                    logger.info(f"  Baixando DUEs em paralelo com {max_workers} workers...")

                    with ThreadPoolExecutor(max_workers=max_workers) as executor:
                        # Submeter todas as DUEs para download paralelo
                        future_to_due = {
                            executor.submit(baixar_due_completa, numero_due): numero_due
                            for numero_due in dues_para_baixar
                        }

                        # Processar resultados conforme completam
                        for i, future in enumerate(as_completed(future_to_due), 1):
                            numero_due = future_to_due[future]

                            if i % 10 == 0:
                                logger.info(f"  [PROGRESSO] {i}/{len(dues_para_baixar)} DUEs...")

                            try:
                                dados_norm = future.result()

                                if dados_norm:
                                    for tabela, dados in dados_norm.items():
                                        if tabela in dados_consolidados:
                                            dados_consolidados[tabela].extend(dados)
                                    dues_ok += 1
                                else:
                                    dues_erro += 1
                                    erros_coletados.append(f"DUE {numero_due}: falha ao baixar dados")

                            except RateLimitError as e:
                                logger.warning(f"⚠️ Rate limit atingido! Salvando dados parciais...")
                                rate_limit_atingido = True
                                erros_coletados.append(f"Rate limit atingido: {str(e)[:80]}")
                                # Cancelar tarefas pendentes
                                for f in future_to_due:
                                    f.cancel()
                                break

                            except Exception as e:
                                logger.warning(f"Erro ao processar DUE {numero_due}: {e}")
                                dues_erro += 1
                                erros_coletados.append(f"DUE {numero_due}: {str(e)[:80]}")
                else:
                    # Fallback para processamento sequencial (se desabilitado ou uma única DUE)
                    logger.info("  Baixando DUEs sequencialmente...")

                    for i, numero_due in enumerate(dues_para_baixar, 1):
                        if i % 10 == 0:
                            logger.info(f"  [PROGRESSO] {i}/{len(dues_para_baixar)} DUEs...")

                        try:
                            dados_norm = baixar_due_completa(numero_due)

                            if dados_norm:
                                for tabela, dados in dados_norm.items():
                                    if tabela in dados_consolidados:
                                        dados_consolidados[tabela].extend(dados)
                                dues_ok += 1
                            else:
                                dues_erro += 1
                                erros_coletados.append(f"DUE {numero_due}: falha ao baixar dados (sequencial)")

                        except RateLimitError as e:
                            logger.warning(f"⚠️ Rate limit atingido! Salvando dados parciais...")
                            rate_limit_atingido = True
                            erros_coletados.append(f"Rate limit atingido: {str(e)[:80]}")
                            break

            except KeyboardInterrupt:
                logger.warning("\n⚠️ Interrupção manual detectada (Ctrl+C)! Salvando dados parciais...")
                interrupcao_manual = True
                erros_coletados.append("Interrupção manual (Ctrl+C)")

            # Salvar dados parciais se houve interrupção
            if rate_limit_atingido or interrupcao_manual:
                motivo = "rate limit 429" if rate_limit_atingido else "interrupcao manual"
                dues_salvas_banco = _salvar_dados_parciais(dados_consolidados, motivo)
                avisos_coletados.append(f"Dados parciais salvos: {dues_salvas_banco} DUEs ({motivo})")
            else:
                # Salvamento normal (sem interrupção)
                logger.info(f"\n[OK] {dues_ok} DUEs baixadas com sucesso")
                if dues_erro > 0:
                    logger.warning(f"[AVISO] {dues_erro} DUEs com erro no download")

                # Salvar dados no banco
                if dues_ok > 0:
                    resultado = salvar_resultados_normalizados(dados_consolidados)
                    # Verificar se retornou tupla (dues_salvas, dues_erro)
                    if isinstance(resultado, tuple):
                        dues_salvas_banco, erros_banco = resultado
                        if erros_banco > 0:
                            avisos_coletados.append(f"{erros_banco} DUEs falharam ao salvar no banco")
                    else:
                        dues_salvas_banco = dues_ok  # fallback

        # 9. Calcular tempo de execução
        fim_execucao = datetime.now()
        tempo_total = fim_execucao - inicio_execucao
        horas, resto = divmod(tempo_total.seconds, 3600)
        minutos, segundos = divmod(resto, 60)
        if horas > 0:
            tempo_execucao_str = f"{horas}h {minutos}min {segundos}s"
        elif minutos > 0:
            tempo_execucao_str = f"{minutos}min {segundos}s"
        else:
            tempo_execucao_str = f"{segundos}s"

        # 10. Resumo detalhado
        logger.info("\n" + "=" * 60)
        logger.info("SINCRONIZACAO CONCLUIDA")
        logger.info("=" * 60)

        logger.info(f"\n[RESUMO]")
        logger.info(f"  NFs no SAP: {len(nfs_sap)}")
        logger.info(f"  Vinculos existentes (cache): {len(vinculos_existentes)}")
        logger.info(f"  NFs consultadas: {max_consultas}")
        logger.info(f"  Novos vinculos: {len(novos_vinculos)}")
        logger.info(f"  DUEs baixadas: {len(dues_para_baixar)}")
        logger.info(f"  DUEs salvas no banco: {dues_salvas_banco}")
        logger.info(f"  Tempo total: {tempo_execucao_str}")

        if erros_coletados:
            logger.warning(f"\n[ERROS] {len(erros_coletados)} erro(s) durante a execucao:")
            for erro in erros_coletados[:5]:
                logger.warning(f"  - {erro}")
            if len(erros_coletados) > 5:
                logger.warning(f"  ... e mais {len(erros_coletados) - 5} erros")

        if len(nfs_sem_vinculo) > max_consultas:
            restantes = len(nfs_sem_vinculo) - max_consultas
            logger.info(f"\n[INFO] Restam {restantes} NFs para processar na proxima execucao")

        # 11. Notificação WhatsApp detalhada
        stats = {
            'nfs_consultadas': max_consultas,
            'novos_vinculos': len(novos_vinculos),
            'dues_baixadas': len(dues_para_baixar),
            'dues_salvas': dues_salvas_banco,
            'dues_erro': dues_erro + len([e for e in erros_coletados if 'banco' in e.lower()]),
            'tempo_execucao': tempo_execucao_str,
        }
        notify_sync_complete_detailed("Novas DUEs", stats, erros_coletados, avisos_coletados)

        # 12. Salvar estatísticas em arquivo (compatibilidade)
        try:
            import json
            stats_file = '.sync_stats_novas.json'
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f)
        except Exception as e:
            logger.debug(f"Erro ao salvar estatísticas: {e}")

    except ControleSiscomexError as exc:
        logger.error("[ERRO] %s", exc)
        erros_coletados.append(f"Erro de configuração: {str(exc)[:100]}")
        # Notificar erro via WhatsApp
        tempo_total = datetime.now() - inicio_execucao
        stats = {'tempo_execucao': str(tempo_total), 'dues_erro': 1}
        notify_sync_complete_detailed("Novas DUEs", stats, erros_coletados, avisos_coletados)
    except Exception as exc:
        logger.error("[ERRO] Falha inesperada: %s", exc, exc_info=True)
        erros_coletados.append(f"Erro inesperado: {str(exc)[:100]}")
        # Notificar erro via WhatsApp
        tempo_total = datetime.now() - inicio_execucao
        stats = {'tempo_execucao': str(tempo_total), 'dues_erro': 1}
        notify_sync_complete_detailed("Novas DUEs", stats, erros_coletados, avisos_coletados)


def main() -> None:
    """Funcao principal de sincronizacao."""
    processar_novas_nfs()


if __name__ == "__main__":
    main()
