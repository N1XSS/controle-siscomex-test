"""Cliente para notificações WhatsApp via Evolution API."""

import requests
from datetime import datetime
from typing import Optional, Dict, Any
from src.core.constants import (
    WHATSAPP_ENABLED,
    WHATSAPP_BASE_URL,
    WHATSAPP_INSTANCE,
    WHATSAPP_APIKEY,
    WHATSAPP_REMOTE_JID,
)
from src.core.logger import logger


def send_notification(message: str) -> bool:
    """
    Envia notificação via WhatsApp usando Evolution API.

    Args:
        message: Texto da mensagem a ser enviada

    Returns:
        True se a notificação foi enviada com sucesso, False caso contrário

    Note:
        Falhas na notificação são logadas mas não lançam exceção.
        A sincronização continua mesmo se a notificação falhar.
    """
    if not WHATSAPP_ENABLED:
        logger.debug("Notificações WhatsApp desabilitadas (WHATSAPP_ENABLED=false)")
        return False

    if not all([WHATSAPP_BASE_URL, WHATSAPP_INSTANCE, WHATSAPP_APIKEY, WHATSAPP_REMOTE_JID]):
        logger.warning(
            "Configuração WhatsApp incompleta. "
            "Verifique WHATSAPP_BASE_URL, WHATSAPP_INSTANCE, WHATSAPP_APIKEY, WHATSAPP_REMOTE_JID"
        )
        return False

    try:
        # Monta URL do endpoint
        url = f"{WHATSAPP_BASE_URL}/message/sendText/{WHATSAPP_INSTANCE}"

        # Headers
        headers = {
            "apikey": WHATSAPP_APIKEY,
            "Content-Type": "application/json"
        }

        # Payload
        payload = {
            "number": WHATSAPP_REMOTE_JID,
            "text": message
        }

        # Envia requisição
        logger.debug(f"Enviando notificação WhatsApp para {WHATSAPP_REMOTE_JID}")
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()

        logger.info(f"Notificação WhatsApp enviada com sucesso: {message[:50]}...")
        return True

    except requests.exceptions.Timeout:
        logger.warning("Timeout ao enviar notificação WhatsApp (10s)")
        return False

    except requests.exceptions.RequestException as e:
        logger.warning(f"Erro ao enviar notificação WhatsApp: {e}")
        return False

    except Exception as e:
        logger.error(f"Erro inesperado ao enviar notificação WhatsApp: {e}")
        return False


def notify_sync_start(sync_type: str) -> bool:
    """
    Notifica início da sincronização.

    Args:
        sync_type: Tipo de sincronização (completo, novas, atualizar, etc.)

    Returns:
        True se notificação enviada com sucesso
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = f"🔄 Iniciando sincronização SISCOMEX [{sync_type}] - {timestamp}"
    return send_notification(message)


def notify_sync_complete(sync_type: str, stats: Optional[Dict[str, Any]] = None) -> bool:
    """
    Notifica conclusão da sincronização com estatísticas.

    Args:
        sync_type: Tipo de sincronização (completo, novas, atualizar, etc.)
        stats: Dicionário com estatísticas da execução:
            - novos_vinculos: Número de novos vínculos criados
            - dues_atualizadas: Número de DUEs atualizadas
            - tempo_execucao: Tempo de execução (formato HH:MM:SS)
            - timestamp: Timestamp de conclusão

    Returns:
        True se notificação enviada com sucesso
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if stats:
        novos_vinculos = stats.get("novos_vinculos", 0)
        dues_atualizadas = stats.get("dues_atualizadas", 0)
        tempo_execucao = stats.get("tempo_execucao", "N/A")

        message = (
            f"✅ Sincronização concluída [{sync_type}]\n"
            f"📊 Novos vínculos: {novos_vinculos}\n"
            f"📋 DUEs atualizadas: {dues_atualizadas}\n"
            f"⏱️ Tempo: {tempo_execucao}\n"
            f"🕐 {timestamp}"
        )
    else:
        message = f"✅ Sincronização concluída [{sync_type}] - {timestamp}"

    return send_notification(message)


def notify_sync_error(sync_type: str, error: str) -> bool:
    """
    Notifica erro durante a sincronização.

    Args:
        sync_type: Tipo de sincronização (completo, novas, atualizar, etc.)
        error: Descrição do erro ocorrido

    Returns:
        True se notificação enviada com sucesso
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Limita tamanho da mensagem de erro
    error_msg = error[:200] + "..." if len(error) > 200 else error

    message = (
        f"❌ Erro na sincronização [{sync_type}]: {error_msg}\n"
        f"🕐 {timestamp}"
    )

    return send_notification(message)
