"""
Gerenciador de Sincronizacao DUE
=================================

Orquestrador unificado para sincronizacao de DUEs com o Siscomex.
Oferece menu interativo e geracao de scripts para agendamento.

Opcoes:
1. Sincronizar novas DUEs (consulta SAP + Siscomex)
2. Atualizar DUEs existentes (> 24h)
3. Sincronizacao completa (novas + atualizacao)
4. Gerar script de agendamento (Windows Task Scheduler)
5. Status do sistema

Uso:
    python -m src.main                          # Menu interativo
    python -m src.main --novas                  # Apenas novas DUEs
    python -m src.main --atualizar              # Apenas atualizacao
    python -m src.main --atualizar-due 24BR...  # Atualizar DUE especifica
    python -m src.main --atualizar-drawback 24BR...,25BR...  # Atualizar drawback
    python -m src.main --atualizar-drawback     # Atualizar drawback de todas
    python -m src.main --completo               # Sincronizacao completa
    python -m src.main --status                 # Exibir status do sistema
"""

import argparse
import os
import subprocess
import sys
from datetime import datetime

from src.core.constants import (
    DEFAULT_DB_STATUS_INTERVAL_HOURS,
    DEFAULT_HTTP_TIMEOUT_SEC,
    ENV_CONFIG_FILE,
    SCRIPT_SAP,
    SCRIPT_SYNC_ATUALIZAR,
    SCRIPT_SYNC_NOVAS,
    SCRIPTS_DIR,
)
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
    logger.info("\n[STATUS DO SISTEMA]")
    logger.info("-" * 40)
    
    try:
        from src.database.manager import db_manager
        
        if not db_manager.conn:
            db_manager.conectar()
        
        if db_manager.conn:
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
            except:
                pass
            
        else:
            logger.error("  [ERRO] Nao foi possivel conectar ao PostgreSQL")
        
    except Exception as e:
        logger.error(f"  [ERRO] Erro ao obter status: {e}")
    
    logger.info("-" * 40)


def executar_modulo(modulo: str, args: list[str] | None = None) -> bool:
    """Executa um modulo Python via -m.

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
        # Isso garante que os subprocessos herdem as variáveis mesmo quando executado via cron
        env = os.environ.copy()
        result = subprocess.run(cmd, check=False, env=env)
        return result.returncode == 0
    except Exception as e:
        logger.error(f"[ERRO] Erro ao executar {script_path}: {e}")
        return False


def sincronizar_novas() -> None:
    """Executa sincronizacao de novas DUEs."""
    logger.info("\n[SINCRONIZANDO NOVAS DUEs]")
    logger.info("-" * 40)
    
    # 1. Atualizar NFs do SAP
    logger.info("\n[1/2] Consultando SAP para NFs de exportacao...")
    executar_modulo(SCRIPT_SAP)
    
    # 2. Sincronizar novas DUEs
    logger.info("\n[2/2] Sincronizando novas DUEs com Siscomex...")
    executar_modulo(SCRIPT_SYNC_NOVAS)


def atualizar_due_especifica(numero_due: str) -> None:
    """Atualiza uma DUE especifica.

    Args:
        numero_due: Numero da DUE.
    """
    logger.info("\n[ATUALIZANDO DUE ESPECIFICA]")
    logger.info("-" * 40)
    logger.info(f"DUE: {numero_due}")
    logger.info("")
    
    try:
        from src.processors.due import consultar_due_completa, processar_dados_due
        from src.api.siscomex.token import token_manager
        from src.database.manager import db_manager
        from dotenv import load_dotenv
        
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
        logger.info(f"[INFO] Consultando atos concessorios...")
        atos_suspensao = None
        atos_isencao = None
        exigencias_fiscais = None
        
        try:
            url_atos_susp = f"https://portalunico.siscomex.gov.br/due/api/ext/due/{numero_due}/drawback/suspensao/atos-concessorios"
            response = token_manager.request("GET", 
                url_atos_susp,
                headers=token_manager.obter_headers(),
                timeout=DEFAULT_HTTP_TIMEOUT_SEC,
            )
            if response.status_code == 200:
                atos_suspensao = response.json()
                if atos_suspensao:
                    logger.info(f"  - {len(atos_suspensao)} atos de suspensao")
        except:
            pass
        
        try:
            url_atos_isen = f"https://portalunico.siscomex.gov.br/due/api/ext/due/{numero_due}/drawback/isencao/atos-concessorios"
            response = token_manager.request("GET", 
                url_atos_isen,
                headers=token_manager.obter_headers(),
                timeout=DEFAULT_HTTP_TIMEOUT_SEC,
            )
            if response.status_code == 200:
                atos_isencao = response.json()
                if atos_isencao:
                    logger.info(f"  - {len(atos_isencao)} atos de isencao")
        except:
            pass
        
        try:
            url_exig = f"https://portalunico.siscomex.gov.br/due/api/ext/due/{numero_due}/exigencias-fiscais"
            response = token_manager.request("GET", 
                url_exig,
                headers=token_manager.obter_headers(),
                timeout=DEFAULT_HTTP_TIMEOUT_SEC,
            )
            if response.status_code == 200:
                exigencias_fiscais = response.json()
                if exigencias_fiscais:
                    logger.info(f"  - {len(exigencias_fiscais)} exigencias fiscais")
        except:
            pass
        
        # Processar dados
        logger.info(f"[INFO] Processando dados...")
        dados_normalizados = processar_dados_due(
            dados_due,
            atos_concessorios=atos_suspensao,
            atos_isencao=atos_isencao,
            exigencias_fiscais=exigencias_fiscais,
            debug_mode=False
        )
        
        if dados_normalizados:
            # Salvar no banco
            logger.info(f"[INFO] Salvando no banco...")
            if db_manager.inserir_due_completa(dados_normalizados):
                logger.info(f"\n[OK] DUE {numero_due} atualizada com sucesso!")
                
                # Mostrar resumo
                logger.info(f"\n[RESUMO]")
                total_registros = 0
                for tabela, registros in dados_normalizados.items():
                    if registros:
                        logger.info(f"  - {tabela}: {len(registros)} registros")
                        total_registros += len(registros)
                logger.info(f"\nTotal: {total_registros} registros")
            else:
                logger.error(f"[ERRO] Erro ao salvar DUE")
        else:
            logger.error(f"[ERRO] Erro ao processar dados")
        
        db_manager.desconectar()
        
    except Exception as e:
        logger.error(f"[ERRO] {e}")
        import traceback
        traceback.print_exc()


def atualizar_drawback(dues_str: str | None = None, todas: bool = False) -> None:
    """Atualiza atos concessorios de drawback.

    Args:
        dues_str: Numeros de DUE separados por virgula.
        todas: Quando True, atualiza todas as DUEs com atos.
    """
    logger.info("\n[ATUALIZANDO ATOS CONCESSORIOS DE DRAWBACK]")
    logger.info("-" * 40)
    
    try:
        from src.api.siscomex.token import token_manager
        from src.database.manager import db_manager
        from dotenv import load_dotenv
        
        load_dotenv(ENV_CONFIG_FILE)
        
        # Conectar ao banco
        if not db_manager.conectar():
            logger.error("[ERRO] Nao foi possivel conectar ao banco de dados")
            return
        
        # Determinar DUEs a atualizar
        if todas:
            # Buscar todas DUEs que tem atos concessorios
            try:
                cur = db_manager.conn.cursor()
                cur.execute("SELECT DISTINCT numero_due FROM due_atos_concessorios_suspensao")
                dues = [row[0] for row in cur.fetchall()]
                if not dues:
                    logger.info("[INFO] Nenhuma DUE com atos concessorios encontrada")
                    db_manager.desconectar()
                    return
                logger.info(f"[INFO] {len(dues)} DUEs com atos concessorios")
            except Exception as e:
                logger.error(f"[ERRO] Erro ao buscar DUEs: {e}")
                db_manager.desconectar()
                return
        elif dues_str:
            dues = [d.strip() for d in dues_str.split(',') if d.strip()]
            if not dues:
                logger.error("[ERRO] Nenhuma DUE especificada")
                db_manager.desconectar()
                return
            logger.info(f"[INFO] {len(dues)} DUEs para atualizar")
        else:
            logger.error("[ERRO] Especifique DUEs ou use --todas")
            db_manager.desconectar()
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
        logger.info("")
        
        # Atualizar cada DUE
        atualizadas = 0
        erros = 0
        sem_atos = 0
        
        URL_BASE = "https://portalunico.siscomex.gov.br/due/api/ext/due"
        
        for i, numero_due in enumerate(dues, 1):
            if i % 25 == 0 or len(dues) <= 10:
                logger.info(f"[PROGRESSO] {i}/{len(dues)} - {numero_due}")
            
            try:
                # Consultar atos de suspensao
                url = f"{URL_BASE}/{numero_due}/drawback/suspensao/atos-concessorios"
                response = token_manager.request("GET", 
                    url,
                    headers=token_manager.obter_headers(),
                    timeout=DEFAULT_HTTP_TIMEOUT_SEC,
                )
                
                if response.status_code == 200:
                    atos = response.json()
                    
                    if atos and len(atos) > 0:
                        # Salvar no banco
                        registros = []
                        for ato in atos:
                            registros.append({
                                'numero_due': numero_due,
                                'ato_numero': ato.get('numero', ''),
                                'tipo_codigo': ato.get('tipo', {}).get('codigo', 0),
                                'tipo_descricao': ato.get('tipo', {}).get('descricao', ''),
                                'item_numero': ato.get('item', {}).get('numero', ''),
                                'item_ncm': ato.get('item', {}).get('ncm', ''),
                                'beneficiario_cnpj': ato.get('beneficiario', {}).get('cnpj', ''),
                                'quantidadeExportada': ato.get('quantidadeExportada', 0),
                                'valorComCoberturaCambial': ato.get('valorComCoberturaCambial', 0),
                                'valorSemCoberturaCambial': ato.get('valorSemCoberturaCambial', 0),
                                'itemDeDUE_numero': ato.get('itemDeDUE', {}).get('numero', '')
                            })
                        
                        # Deletar registros antigos e inserir novos
                        cur = db_manager.conn.cursor()
                        cur.execute("DELETE FROM due_atos_concessorios_suspensao WHERE numero_due = %s", (numero_due,))
                        
                        for reg in registros:
                            cur.execute("""
                                INSERT INTO due_atos_concessorios_suspensao 
                                (numero_due, ato_numero, tipo_codigo, tipo_descricao, item_numero, 
                                 item_ncm, beneficiario_cnpj, quantidade_exportada, 
                                 valor_com_cobertura_cambial, valor_sem_cobertura_cambial, item_de_due_numero)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """, (
                                reg['numero_due'], reg['ato_numero'], reg['tipo_codigo'],
                                reg['tipo_descricao'], reg['item_numero'], reg['item_ncm'],
                                reg['beneficiario_cnpj'], reg['quantidadeExportada'],
                                reg['valorComCoberturaCambial'], reg['valorSemCoberturaCambial'],
                                reg['itemDeDUE_numero']
                            ))
                        
                        db_manager.conn.commit()
                        atualizadas += 1
                        
                        if len(dues) <= 10:
                            logger.info(f"  [OK] {len(registros)} atos atualizados")
                    else:
                        sem_atos += 1
                        if len(dues) <= 10:
                            logger.info(f"  [INFO] Nenhum ato encontrado")
                else:
                    erros += 1
                    if len(dues) <= 10:
                        logger.error(f"  [ERRO] Status {response.status_code}")
                        
            except Exception as e:
                erros += 1
                if len(dues) <= 10:
                    logger.error(f"  [ERRO] {str(e)[:50]}")
            
            import time
            time.sleep(0.2)
        
        db_manager.desconectar()
        
        # Resumo
        logger.info("\n" + "-" * 40)
        logger.info(f"[RESUMO]")
        logger.info(f"  - DUEs processadas: {len(dues)}")
        logger.info(f"  - Atualizadas com sucesso: {atualizadas}")
        logger.info(f"  - Sem atos concessorios: {sem_atos}")
        logger.info(f"  - Erros: {erros}")
        
    except Exception as e:
        logger.error(f"[ERRO] {e}")
        import traceback
        traceback.print_exc()


def atualizar_existentes(force: bool = False, limit: int | None = None) -> None:
    """Executa atualizacao de DUEs existentes.

    Args:
        force: Quando True, atualiza todas as DUEs.
        limit: Limita a quantidade de atualizacoes.
    """
    logger.info("\n[ATUALIZANDO DUEs EXISTENTES]")
    logger.info("-" * 40)
    
    args = []
    if force:
        args.append('--force')
    if limit:
        args.extend(['--limit', str(limit)])
    executar_modulo(SCRIPT_SYNC_ATUALIZAR, args)


def sincronizacao_completa() -> None:
    """Executa sincronizacao completa (novas + atualizacao)."""
    logger.info("\n[SINCRONIZACAO COMPLETA]")
    logger.info("=" * 60)
    
    # 1. Sincronizar novas
    sincronizar_novas()
    
    # 2. Atualizar existentes
    atualizar_existentes()
    
    logger.info("\n" + "=" * 60)
    logger.info("[SINCRONIZACAO COMPLETA FINALIZADA]")
    logger.info("=" * 60)


def gerar_script_agendamento() -> None:
    """Gera scripts para agendamento no Windows Task Scheduler."""
    logger.info("\n[GERANDO SCRIPTS DE AGENDAMENTO]")
    logger.info("-" * 40)
    
    # Obter caminho absoluto do Python e do projeto
    python_path = sys.executable
    projeto_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    pasta_scripts = os.path.join(projeto_path, SCRIPTS_DIR)
    os.makedirs(pasta_scripts, exist_ok=True)
    
    # Script para sincronizacao de novas (executar a cada hora comercial)
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
    
    # Script para atualizacao diaria (executar 1x por dia, ex: 6h da manha)
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
    
    caminho_instrucoes = os.path.join(pasta_scripts, 'INSTRUCOES_AGENDAMENTO.txt')
    with open(caminho_instrucoes, 'w', encoding='utf-8') as f:
        f.write(instrucoes)
    logger.info(f"[OK] Criado: {caminho_instrucoes}")
    
    logger.info(instrucoes)


def menu_interativo() -> None:
    """Exibe menu interativo."""
    while True:
        exibir_cabecalho()
        
        logger.info("\n[OPCOES]")
        logger.info("  1. Sincronizar novas DUEs (SAP + Siscomex)")
        logger.info("  2. Atualizar DUEs existentes (> 24h)")
        logger.info("  3. Sincronizacao completa (novas + atualizacao)")
        logger.info("  4. Gerar scripts de agendamento")
        logger.info("  5. Status do sistema")
        logger.info("  0. Sair")
        
        logger.info("")
        opcao = input("Escolha uma opcao: ").strip()
        
        if opcao == '1':
            sincronizar_novas()
        elif opcao == '2':
            atualizar_existentes()
        elif opcao == '3':
            sincronizacao_completa()
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
    parser.add_argument('--atualizar-drawback', type=str, metavar='DUES', nargs='?', const='--todas',
                        help='Atualizar atos concessorios de drawback (DUEs separadas por virgula ou --todas)')
    parser.add_argument('--completo', action='store_true',
                        help='Sincronizacao completa')
    parser.add_argument('--status', action='store_true',
                        help='Exibir status do sistema')
    parser.add_argument('--gerar-scripts', action='store_true',
                        help='Gerar scripts de agendamento')
    
    args = parser.parse_args()
    
    # Se nenhum argumento, mostrar menu interativo
    if not any([args.novas, args.atualizar, args.atualizar_due, args.atualizar_drawback, args.completo, args.status, args.gerar_scripts]):
        menu_interativo()
        return
    
    # Executar opcao especificada
    exibir_cabecalho()
    
    if args.status:
        exibir_status()
    elif args.atualizar_due:
        atualizar_due_especifica(args.atualizar_due)
    elif args.atualizar_drawback:
        if args.atualizar_drawback == '--todas':
            atualizar_drawback(todas=True)
        else:
            atualizar_drawback(dues_str=args.atualizar_drawback)
    elif args.novas:
        sincronizar_novas()
    elif args.atualizar:
        atualizar_existentes()
    elif args.completo:
        sincronizacao_completa()
    elif args.gerar_scripts:
        gerar_script_agendamento()


if __name__ == "__main__":
    main()
