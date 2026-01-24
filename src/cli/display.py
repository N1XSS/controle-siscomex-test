"""Funções de formatação de output para o CLI."""

from __future__ import annotations

from datetime import datetime

from src.core.constants import DEFAULT_DB_STATUS_INTERVAL_HOURS
from src.core.logger import logger


def exibir_cabecalho() -> None:
    """Exibe cabecalho do sistema."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("   GERENCIADOR DE SINCRONIZACAO DUE - SISCOMEX")
    logger.info("=" * 60)
    logger.info(f"   Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    logger.info("=" * 60)


def exibir_status() -> None:
    """Exibe status do sistema consultando PostgreSQL."""
    from src.database.manager import db_manager

    logger.info("\n[STATUS DO SISTEMA]")
    logger.info("-" * 40)

    try:
        if not db_manager.conectar():
            logger.error("  [ERRO] Nao foi possivel conectar ao PostgreSQL")
            return

        stats = db_manager.obter_estatisticas()

        logger.info(f"  NFs SAP: {stats.get('nfe_sap', 0)} chaves")
        logger.info(f"  Vinculos NF->DUE: {stats.get('nf_due_vinculo', 0)} registros")
        logger.info(f"  DUEs baixadas: {stats.get('due_principal', 0)} total")
        logger.info(f"  Itens de DUE: {stats.get('due_itens', 0)} registros")
        logger.info(f"  Eventos historico: {stats.get('due_eventos_historico', 0)} registros")
        logger.info(f"  Notas fiscais: {stats.get('due_item_nota_fiscal_exportacao', 0)} registros")

        # Verificar DUEs desatualizadas
        try:
            desatualizadas = db_manager.obter_dues_desatualizadas(
                horas=DEFAULT_DB_STATUS_INTERVAL_HOURS
            )
            logger.info(
                "  DUEs para atualizar (> "
                f"{DEFAULT_DB_STATUS_INTERVAL_HOURS}h): "
                f"{len(desatualizadas) if desatualizadas else 0}"
            )
        except Exception as e:
            logger.warning(f"  [AVISO] Erro ao consultar DUEs desatualizadas: {e}")

        db_manager.desconectar()

    except Exception as e:
        logger.error(f"  [ERRO] Erro ao obter status: {e}")


def exibir_menu() -> None:
    """Exibe menu interativo."""
    logger.info("\n[MENU PRINCIPAL]")
    logger.info("-" * 40)
    logger.info("1. Sincronizar novas DUEs")
    logger.info("2. Atualizar DUEs existentes")
    logger.info("3. Sincronizacao completa (1 + 2)")
    logger.info("4. Gerar scripts de agendamento")
    logger.info("5. Status do sistema")
    logger.info("0. Sair")
    logger.info("-" * 40)
