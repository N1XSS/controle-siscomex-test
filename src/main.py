"""
Gerenciador de Sincronizacao DUE
=================================

Orquestrador unificado para sincronizacao de DUEs com o Siscomex.
Oferece menu interativo e geracao de scripts para agendamento.

Uso:
    python -m src.main                          # Menu interativo
    python -m src.main --novas                  # Apenas novas DUEs
    python -m src.main --atualizar              # Apenas atualizacao
    python -m src.main --atualizar-due 24BR...  # Atualizar DUE especifica
    python -m src.main --completo               # Sincronizacao completa
    python -m src.main --status                 # Exibir status do sistema
"""

from __future__ import annotations

import argparse
import sys

from dotenv import load_dotenv

from src.core.constants import (
    DUE_DOWNLOAD_WORKERS,
    ENV_CONFIG_FILE,
)
from src.core.logger import logger
from src.core.config_validator import validar_configuracao
from src.cli.commands import (
    sincronizar_novas,
    atualizar_existentes,
    atualizar_due_especifica,
    sincronizar_completo,
    gerar_script_agendamento,
)
from src.cli.display import exibir_cabecalho, exibir_status, exibir_menu


def menu_interativo() -> None:
    """Menu interativo para selecao de operacoes."""
    exibir_cabecalho()

    while True:
        exibir_menu()
        opcao = input("Escolha uma opcao: ").strip()

        if opcao == '1':
            sincronizar_novas()
        elif opcao == '2':
            atualizar_existentes()
        elif opcao == '3':
            sincronizar_completo()
        elif opcao == '4':
            gerar_script_agendamento()
        elif opcao == '5':
            exibir_status()
        elif opcao == '0':
            logger.info("\nAte logo!")
            break
        else:
            logger.warning("\n[AVISO] Opcao invalida!")

        logger.info("")
        input("Pressione Enter para continuar...")


def main() -> None:
    """Funcao principal do CLI."""
    # Carregar variáveis de ambiente
    load_dotenv(ENV_CONFIG_FILE)

    # Validar configurações obrigatórias
    if not validar_configuracao():
        logger.error("\n❌ Configuração inválida. Corrija os erros acima e tente novamente.")
        sys.exit(1)

    parser = argparse.ArgumentParser(
        description='Gerenciador de Sincronizacao DUE',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Exemplos:
  python -m src.main              # Menu interativo
  python -m src.main --novas      # Sincronizar apenas novas DUEs
  python -m src.main --atualizar  # Atualizar apenas DUEs existentes
  python -m src.main --completo   # Sincronizacao completa
  python -m src.main --status     # Exibir status do sistema
'''
    )

    parser.add_argument('--novas', action='store_true',
                        help='Sincronizar novas DUEs')
    parser.add_argument('--atualizar', action='store_true',
                        help='Atualizar DUEs existentes')
    parser.add_argument('--atualizar-due', type=str, metavar='NUMERO_DUE',
                        help='Atualizar uma DUE especifica (ex: 24BR0008165929)')
    parser.add_argument('--completo', action='store_true',
                        help='Sincronizacao completa')
    parser.add_argument('--status', action='store_true',
                        help='Exibir status do sistema')
    parser.add_argument('--gerar-scripts', action='store_true',
                        help='Gerar scripts de agendamento')
    parser.add_argument('--workers-download', type=int, default=DUE_DOWNLOAD_WORKERS,
                        help=f'Numero de workers paralelos para download de DUEs (default: {DUE_DOWNLOAD_WORKERS})')

    args = parser.parse_args()

    # Se nenhum argumento, mostrar menu interativo
    if not any([args.novas, args.atualizar, args.atualizar_due, args.completo, args.status, args.gerar_scripts]):
        menu_interativo()
        return

    # Exibir cabecalho
    exibir_cabecalho()

    # Executar comando especifico
    if args.status:
        exibir_status()
    elif args.gerar_scripts:
        gerar_script_agendamento()
    elif args.atualizar_due:
        atualizar_due_especifica(args.atualizar_due)
    elif args.novas:
        sincronizar_novas(workers_download=args.workers_download)
    elif args.atualizar:
        atualizar_existentes(workers_download=args.workers_download)
    elif args.completo:
        sincronizar_completo(workers_download=args.workers_download)


if __name__ == "__main__":
    main()
