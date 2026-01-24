"""Funções auxiliares para chamadas à API do Siscomex."""

from __future__ import annotations

import json
from typing import Any

from src.core.constants import DEFAULT_HTTP_TIMEOUT_SEC
from src.core.logger import logger


def buscar_dados_complementares(
    numero_due: str,
    tipo: str,
    url: str,
    token_manager: Any,
) -> dict | list | None:
    """Busca dados complementares da DUE (atos concessórios ou exigências fiscais).

    Args:
        numero_due: Número da DUE
        tipo: Tipo de dados ('atos_suspensao', 'atos_isencao', 'exigencias_fiscais')
        url: URL completa do endpoint
        token_manager: Instância do gerenciador de tokens

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
            if dados:
                logger.info(f"  - {len(dados)} {tipo}")
            return dados
        else:
            logger.warning(
                f"[AVISO] Falha ao buscar {tipo}: "
                f"HTTP {response.status_code}"
            )
            return None
    except json.JSONDecodeError as e:
        logger.warning(f"[AVISO] Erro ao decodificar JSON de {tipo}: {e}")
        return None
    except Exception as e:
        logger.warning(f"[AVISO] Erro ao buscar {tipo}: {e}")
        return None


def buscar_todos_dados_complementares(
    numero_due: str,
    token_manager: Any,
    fetch_atos_suspensao: bool = False,
    fetch_atos_isencao: bool = False,
    fetch_exigencias_fiscais: bool = False,
) -> tuple[list | None, list | None, list | None]:
    """Busca todos os dados complementares de uma DUE.

    Args:
        numero_due: Número da DUE
        token_manager: Instância do gerenciador de tokens
        fetch_atos_suspensao: Se deve buscar atos de suspensão
        fetch_atos_isencao: Se deve buscar atos de isenção
        fetch_exigencias_fiscais: Se deve buscar exigências fiscais

    Returns:
        Tupla (atos_suspensao, atos_isencao, exigencias_fiscais)
    """
    logger.info(f"[INFO] Consultando atos concessorios...")
    atos_suspensao = None
    atos_isencao = None
    exigencias_fiscais = None

    if fetch_atos_suspensao:
        url_atos_susp = f"https://portalunico.siscomex.gov.br/due/api/ext/due/{numero_due}/drawback/suspensao/atos-concessorios"
        atos_suspensao = buscar_dados_complementares(
            numero_due, "atos de suspensao", url_atos_susp, token_manager
        )

    if fetch_atos_isencao:
        url_atos_isen = f"https://portalunico.siscomex.gov.br/due/api/ext/due/{numero_due}/drawback/isencao/atos-concessorios"
        atos_isencao = buscar_dados_complementares(
            numero_due, "atos de isencao", url_atos_isen, token_manager
        )

    if fetch_exigencias_fiscais:
        url_exig = f"https://portalunico.siscomex.gov.br/due/api/ext/due/{numero_due}/exigencias-fiscais"
        exigencias_fiscais = buscar_dados_complementares(
            numero_due, "exigencias fiscais", url_exig, token_manager
        )

    return atos_suspensao, atos_isencao, exigencias_fiscais
