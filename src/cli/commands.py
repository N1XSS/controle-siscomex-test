"""Comandos CLI para gerenciamento de DUEs."""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime

from src.core.constants import (
    SCRIPT_SAP,
    SCRIPT_SYNC_ATUALIZAR,
    SCRIPT_SYNC_NOVAS,
)
from src.core.logger import logger
from src.notifications import notify_sync_start, notify_sync_complete, notify_sync_error
from src.cli.api_helpers import buscar_todos_dados_complementares


def executar_modulo(modulo: str, args: list[str] | None = None) -> bool:
    """Executa um modulo Python como subprocess.

    Args:
        modulo: Modulo Python (ex: src.sync.new_dues).
        args: Argumentos adicionais.

    Returns:
        True quando o modulo executou sem erro.
    """
    cmd = [sys.executable, "-m", modulo]
    if args:
        cmd.extend(args)

    try:
        # Passar explicitamente as variáveis de ambiente do processo atual
        env = os.environ.copy()
        result = subprocess.run(cmd, check=False, env=env)
        return result.returncode == 0
    except Exception as e:
        logger.error(f"[ERRO] Erro ao executar módulo {modulo}: {e}")
        return False


def sincronizar_novas(workers_download: int | None = None) -> None:
    """Executa sincronizacao de novas DUEs.

    Args:
        workers_download: Número de workers paralelos para downloads (None = usar default).
    """
    logger.info("\n[SINCRONIZANDO NOVAS DUEs]")
    logger.info("-" * 40)

    notify_sync_start("novas")

    try:
        inicio = datetime.now()

        # 1. Atualizar NFs do SAP
        logger.info("\n[1/2] Consultando SAP para NFs de exportacao...")
        executar_modulo(SCRIPT_SAP)

        # 2. Sincronizar novas DUEs
        logger.info("\n[2/2] Sincronizando novas DUEs com Siscomex...")
        args = []
        if workers_download is not None:
            args.extend(['--workers-download', str(workers_download)])
        resultado = executar_modulo(SCRIPT_SYNC_NOVAS, args if args else None)

        # Calcular tempo de execução
        fim = datetime.now()
        duracao = fim - inicio
        tempo_formatado = str(duracao).split('.')[0]

        logger.info(f"\n⏱️ Tempo total: {tempo_formatado}")
        logger.info("\n" + "=" * 60)
        logger.info("[SINCRONIZACAO DE NOVAS DUEs FINALIZADA]")
        logger.info("=" * 60)

        # Notificar conclusão
        if resultado:
            stats = {"duracao": tempo_formatado}
            notify_sync_complete("novas", stats)
        else:
            notify_sync_error("novas", "O processo retornou código de erro")

    except Exception as e:
        logger.error(f"[ERRO] Falha na sincronização: {e}")
        notify_sync_error("novas", str(e))


def atualizar_existentes(workers_download: int | None = None) -> None:
    """Executa atualizacao de DUEs existentes.

    Args:
        workers_download: Número de workers paralelos para downloads (None = usar default).
    """
    logger.info("\n[ATUALIZANDO DUEs EXISTENTES]")
    logger.info("-" * 40)

    notify_sync_start("atualizacao")

    try:
        inicio = datetime.now()

        args = []
        if workers_download is not None:
            args.extend(['--workers-download', str(workers_download)])
        resultado = executar_modulo(SCRIPT_SYNC_ATUALIZAR, args if args else None)

        # Calcular tempo de execução
        fim = datetime.now()
        duracao = fim - inicio
        tempo_formatado = str(duracao).split('.')[0]

        logger.info(f"\n⏱️ Tempo total: {tempo_formatado}")
        logger.info("\n" + "=" * 60)
        logger.info("[ATUALIZACAO DE DUEs FINALIZADA]")
        logger.info("=" * 60)

        # Notificar conclusão
        if resultado:
            stats = {"duracao": tempo_formatado}
            notify_sync_complete("atualizacao", stats)
        else:
            notify_sync_error("atualizacao", "O processo retornou código de erro")

    except Exception as e:
        logger.error(f"[ERRO] Falha na atualização: {e}")
        notify_sync_error("atualizacao", str(e))


def atualizar_due_especifica(numero_due: str) -> None:
    """Atualiza uma DUE especifica.

    Args:
        numero_due: Numero da DUE.
    """
    from src.processors.due import consultar_due_completa, processar_dados_due
    from src.api.siscomex.token import token_manager
    from src.database.manager import db_manager
    from src.core.constants import (
        ENV_CONFIG_FILE,
        SISCOMEX_FETCH_ATOS_SUSPENSAO,
        SISCOMEX_FETCH_ATOS_ISENCAO,
        SISCOMEX_FETCH_EXIGENCIAS_FISCAIS,
    )
    from dotenv import load_dotenv

    logger.info("\n[ATUALIZANDO DUE ESPECIFICA]")
    logger.info("-" * 40)
    logger.info(f"DUE: {numero_due}")
    logger.info("")

    try:
        load_dotenv(ENV_CONFIG_FILE)

        # Conectar ao banco
        if not db_manager.conectar():
            logger.error("[ERRO] Nao foi possivel conectar ao banco de dados")
            return

        # Autenticar
        client_id = os.getenv('SISCOMEX_CLIENT_ID')
        client_secret = os.getenv('SISCOMEX_CLIENT_SECRET')

        if not client_id or not client_secret:
            logger.error("[ERRO] Credenciais nao configuradas")
            db_manager.desconectar()
            return

        token_manager.configurar_credenciais(client_id, client_secret)
        if not token_manager.autenticar():
            logger.error("[ERRO] Falha na autenticacao")
            db_manager.desconectar()
            return

        logger.info("[OK] Autenticado!")

        # Consultar DUE completa
        logger.info(f"[INFO] Consultando DUE...")
        dados_due = consultar_due_completa(numero_due, debug_mode=False)

        if not dados_due or (isinstance(dados_due, dict) and 'error' in dados_due):
            logger.error(f"[ERRO] Nao foi possivel consultar DUE")
            db_manager.desconectar()
            return

        # Consultar atos concessorios
        atos_suspensao, atos_isencao, exigencias_fiscais = buscar_todos_dados_complementares(
            numero_due,
            token_manager,
            SISCOMEX_FETCH_ATOS_SUSPENSAO,
            SISCOMEX_FETCH_ATOS_ISENCAO,
            SISCOMEX_FETCH_EXIGENCIAS_FISCAIS
        )

        # Processar dados
        logger.info(f"[INFO] Processando dados...")
        dados_normalizados = processar_dados_due(
            dados_due,
            atos_concessorios=atos_suspensao,
            atos_isencao=atos_isencao,
            exigencias_fiscais=exigencias_fiscais,
        )

        if not dados_normalizados:
            logger.error(f"[ERRO] Falha ao processar dados da DUE")
            db_manager.desconectar()
            return

        # Salvar no banco
        logger.info(f"[INFO] Salvando no banco de dados...")
        salvas, erros = db_manager.inserir_due_completa(dados_normalizados)

        if salvas > 0:
            logger.info(f"[OK] DUE {numero_due} atualizada com sucesso!")
        else:
            logger.error(f"[ERRO] Falha ao salvar DUE no banco ({erros} erros)")

        db_manager.desconectar()

    except Exception as e:
        logger.error(f"[ERRO] Erro ao atualizar DUE: {e}")
        if db_manager.conectado:
            db_manager.desconectar()


def sincronizar_completo(workers_download: int | None = None) -> None:
    """Executa sincronizacao completa (novas + atualizacao).

    Args:
        workers_download: Número de workers paralelos para downloads (None = usar default).
    """
    logger.info("\n" + "=" * 60)
    logger.info("[SINCRONIZACAO COMPLETA]")
    logger.info("=" * 60)

    notify_sync_start("completo")

    try:
        inicio = datetime.now()

        # 1. Sincronizar novas
        sincronizar_novas(workers_download=workers_download)

        # 2. Atualizar existentes
        atualizar_existentes(workers_download=workers_download)

        # Calcular tempo de execução total
        fim = datetime.now()
        duracao = fim - inicio
        tempo_formatado = str(duracao).split('.')[0]

        logger.info(f"\n⏱️ Tempo total da sincronização completa: {tempo_formatado}")

    except Exception as e:
        logger.error(f"[ERRO] Falha na sincronização completa: {e}")
        notify_sync_error("completo", str(e))

    logger.info("\n" + "=" * 60)
    logger.info("[SINCRONIZACAO COMPLETA FINALIZADA]")
    logger.info("=" * 60)


def gerar_script_agendamento() -> None:
    """Gera scripts para agendamento no Windows Task Scheduler."""
    from src.core.constants import SCRIPTS_DIR

    logger.info("\n[GERANDO SCRIPTS DE AGENDAMENTO]")
    logger.info("-" * 40)

    # Obter caminho absoluto do Python e do projeto
    python_path = sys.executable
    projeto_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    pasta_scripts = os.path.join(projeto_path, SCRIPTS_DIR)
    os.makedirs(pasta_scripts, exist_ok=True)

    # Script para sincronizacao de novas
    script_novas = f'''@echo off
REM Sincronizacao de Novas DUEs
REM Sugestao: Executar a cada hora durante horario comercial (8h-18h)

cd /d "{projeto_path}"
"{python_path}" -m {SCRIPT_SAP}
"{python_path}" -m {SCRIPT_SYNC_NOVAS}

echo.
echo Sincronizacao de novas DUEs concluida!
'''

    caminho_novas = os.path.join(pasta_scripts, 'sync_novas.bat')
    with open(caminho_novas, 'w', encoding='utf-8') as f:
        f.write(script_novas)
    logger.info(f"[OK] Criado: {caminho_novas}")

    # Script para atualizacao diaria
    script_atualizar = f'''@echo off
REM Atualizacao Diaria de DUEs
REM Sugestao: Executar 1x por dia as 6h da manha

cd /d "{projeto_path}"
"{python_path}" -m {SCRIPT_SYNC_ATUALIZAR}

echo.
echo Atualizacao diaria de DUEs concluida!
'''

    caminho_atualizar = os.path.join(pasta_scripts, 'sync_atualizar.bat')
    with open(caminho_atualizar, 'w', encoding='utf-8') as f:
        f.write(script_atualizar)
    logger.info(f"[OK] Criado: {caminho_atualizar}")

    # Script para sincronizacao completa
    script_completo = f'''@echo off
REM Sincronizacao Completa (Novas + Atualizacao)
REM Sugestao: Executar quando necessario ou 1x por dia

cd /d "{projeto_path}"
"{python_path}" -m {SCRIPT_SAP}
"{python_path}" -m {SCRIPT_SYNC_NOVAS}
"{python_path}" -m {SCRIPT_SYNC_ATUALIZAR}

echo.
echo Sincronizacao completa concluida!
'''

    caminho_completo = os.path.join(pasta_scripts, 'sync_completo.bat')
    with open(caminho_completo, 'w', encoding='utf-8') as f:
        f.write(script_completo)
    logger.info(f"[OK] Criado: {caminho_completo}")

    # Instrucoes de agendamento
    instrucoes = f'''
================================================================================
INSTRUCOES PARA AGENDAMENTO NO WINDOWS TASK SCHEDULER
================================================================================

1. Abra o "Agendador de Tarefas" (Task Scheduler)
   - Pressione Win + R, digite "taskschd.msc" e Enter

2. Crie uma nova tarefa basica:
   - Acao > Criar Tarefa Basica

3. TAREFA 1 - Sincronizar Novas DUEs (a cada hora comercial):
   - Nome: "DUE - Sincronizar Novas"
   - Disparador: Diariamente, repetir a cada 1 hora
   - Horario: 8:00, ate 18:00
   - Acao: Iniciar programa
   - Programa: {caminho_novas}

4. TAREFA 2 - Atualizar DUEs (1x por dia):
   - Nome: "DUE - Atualizar Existentes"
   - Disparador: Diariamente
   - Horario: 6:00 (antes do expediente)
   - Acao: Iniciar programa
   - Programa: {caminho_atualizar}

5. Configure as tarefas para:
   - "Executar estando o usuario conectado ou nao"
   - "Executar com privilegios mais altos"

================================================================================
'''

    logger.info(instrucoes)
    logger.info("\n[OK] Scripts de agendamento criados com sucesso!")
    logger.info(f"[INFO] Localizacao: {pasta_scripts}")
