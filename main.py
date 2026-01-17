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
    python main.py                          # Menu interativo
    python main.py --novas                  # Apenas novas DUEs
    python main.py --atualizar              # Apenas atualizacao
    python main.py --atualizar-due 24BR...  # Atualizar DUE especifica
    python main.py --atualizar-drawback 24BR...,25BR...  # Atualizar drawback
    python main.py --atualizar-drawback     # Atualizar drawback de todas
    python main.py --completo               # Sincronizacao completa
    python main.py --status                 # Exibir status do sistema
"""

import os
import sys
import subprocess
from datetime import datetime
import argparse

# Caminhos dos scripts
SCRIPT_SAP = 'consulta_sap.py'
SCRIPT_SYNC_NOVAS = 'sync_novas.py'
SCRIPT_SYNC_ATUALIZAR = 'sync_atualizar.py'


def exibir_cabecalho():
    """Exibe cabecalho do sistema"""
    print()
    print("=" * 60)
    print("   GERENCIADOR DE SINCRONIZACAO DUE - SISCOMEX")
    print("=" * 60)
    print(f"   Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 60)


def exibir_status():
    """Exibe status do sistema consultando PostgreSQL"""
    print("\n[STATUS DO SISTEMA]")
    print("-" * 40)
    
    try:
        from db_manager import db_manager
        
        if not db_manager.conn:
            db_manager.conectar()
        
        if db_manager.conn:
            stats = db_manager.obter_estatisticas()
            
            print(f"  NFs SAP: {stats.get('nfe_sap', 0)} chaves")
            print(f"  Vinculos NF->DUE: {stats.get('nf_due_vinculo', 0)} registros")
            print(f"  DUEs baixadas: {stats.get('due_principal', 0)} total")
            print(f"  Itens de DUE: {stats.get('due_itens', 0)} registros")
            print(f"  Eventos historico: {stats.get('due_eventos_historico', 0)} registros")
            print(f"  Notas fiscais: {stats.get('due_item_nota_fiscal_exportacao', 0)} registros")
            
            # Verificar DUEs desatualizadas
            try:
                desatualizadas = db_manager.obter_dues_desatualizadas(horas=24)
                print(f"  DUEs para atualizar (> 24h): {len(desatualizadas) if desatualizadas else 0}")
            except:
                pass
            
        else:
            print("  [ERRO] Nao foi possivel conectar ao PostgreSQL")
        
    except Exception as e:
        print(f"  [ERRO] Erro ao obter status: {e}")
    
    print("-" * 40)


def executar_script(script_path, args=None):
    """Executa um script Python"""
    cmd = [sys.executable, script_path]
    if args:
        cmd.extend(args)
    
    try:
        # Passar explicitamente as variáveis de ambiente do processo atual
        # Isso garante que os subprocessos herdem as variáveis mesmo quando executado via cron
        env = os.environ.copy()
        result = subprocess.run(cmd, check=False, env=env)
        return result.returncode == 0
    except Exception as e:
        print(f"[ERRO] Erro ao executar {script_path}: {e}")
        return False


def sincronizar_novas():
    """Executa sincronizacao de novas DUEs"""
    print("\n[SINCRONIZANDO NOVAS DUEs]")
    print("-" * 40)
    
    # 1. Atualizar NFs do SAP
    print("\n[1/2] Consultando SAP para NFs de exportacao...")
    if os.path.exists(SCRIPT_SAP):
        executar_script(SCRIPT_SAP)
    else:
        print(f"[AVISO] Script {SCRIPT_SAP} nao encontrado")
    
    # 2. Sincronizar novas DUEs
    print("\n[2/2] Sincronizando novas DUEs com Siscomex...")
    if os.path.exists(SCRIPT_SYNC_NOVAS):
        executar_script(SCRIPT_SYNC_NOVAS)
    else:
        print(f"[ERRO] Script {SCRIPT_SYNC_NOVAS} nao encontrado")


def atualizar_due_especifica(numero_due):
    """Atualiza uma DUE especifica"""
    print("\n[ATUALIZANDO DUE ESPECIFICA]")
    print("-" * 40)
    print(f"DUE: {numero_due}")
    print()
    
    try:
        from due_processor import consultar_due_completa, processar_dados_due
        from token_manager import token_manager
        from db_manager import db_manager
        from dotenv import load_dotenv
        import os
        
        load_dotenv('config.env')
        
        # Conectar ao banco
        if not db_manager.conectar():
            print("[ERRO] Nao foi possivel conectar ao banco de dados")
            return
        
        # Autenticar
        client_id = os.getenv('SISCOMEX_CLIENT_ID')
        client_secret = os.getenv('SISCOMEX_CLIENT_SECRET')
        
        if not client_id or not client_secret:
            print("[ERRO] Credenciais nao configuradas")
            db_manager.desconectar()
            return
        
        token_manager.configurar_credenciais(client_id, client_secret)
        if not token_manager.autenticar():
            print("[ERRO] Falha na autenticacao")
            db_manager.desconectar()
            return
        
        print("[OK] Autenticado!")
        
        # Consultar DUE completa
        print(f"[INFO] Consultando DUE...")
        dados_due = consultar_due_completa(numero_due, debug_mode=False)
        
        if not dados_due or (isinstance(dados_due, dict) and 'error' in dados_due):
            print(f"[ERRO] Nao foi possivel consultar DUE")
            db_manager.desconectar()
            return
        
        # Consultar atos concessorios
        print(f"[INFO] Consultando atos concessorios...")
        atos_suspensao = None
        atos_isencao = None
        exigencias_fiscais = None
        
        try:
            url_atos_susp = f"https://portalunico.siscomex.gov.br/due/api/ext/due/{numero_due}/drawback/suspensao/atos-concessorios"
            response = token_manager.session.get(url_atos_susp, headers=token_manager.obter_headers(), timeout=10)
            if response.status_code == 200:
                atos_suspensao = response.json()
                if atos_suspensao:
                    print(f"  - {len(atos_suspensao)} atos de suspensao")
        except:
            pass
        
        try:
            url_atos_isen = f"https://portalunico.siscomex.gov.br/due/api/ext/due/{numero_due}/drawback/isencao/atos-concessorios"
            response = token_manager.session.get(url_atos_isen, headers=token_manager.obter_headers(), timeout=10)
            if response.status_code == 200:
                atos_isencao = response.json()
                if atos_isencao:
                    print(f"  - {len(atos_isencao)} atos de isencao")
        except:
            pass
        
        try:
            url_exig = f"https://portalunico.siscomex.gov.br/due/api/ext/due/{numero_due}/exigencias-fiscais"
            response = token_manager.session.get(url_exig, headers=token_manager.obter_headers(), timeout=10)
            if response.status_code == 200:
                exigencias_fiscais = response.json()
                if exigencias_fiscais:
                    print(f"  - {len(exigencias_fiscais)} exigencias fiscais")
        except:
            pass
        
        # Processar dados
        print(f"[INFO] Processando dados...")
        dados_normalizados = processar_dados_due(
            dados_due,
            atos_concessorios=atos_suspensao,
            atos_isencao=atos_isencao,
            exigencias_fiscais=exigencias_fiscais,
            debug_mode=False
        )
        
        if dados_normalizados:
            # Salvar no banco
            print(f"[INFO] Salvando no banco...")
            if db_manager.inserir_due_completa(dados_normalizados):
                print(f"\n[OK] DUE {numero_due} atualizada com sucesso!")
                
                # Mostrar resumo
                print(f"\n[RESUMO]")
                total_registros = 0
                for tabela, registros in dados_normalizados.items():
                    if registros:
                        print(f"  - {tabela}: {len(registros)} registros")
                        total_registros += len(registros)
                print(f"\nTotal: {total_registros} registros")
            else:
                print(f"[ERRO] Erro ao salvar DUE")
        else:
            print(f"[ERRO] Erro ao processar dados")
        
        db_manager.desconectar()
        
    except Exception as e:
        print(f"[ERRO] {e}")
        import traceback
        traceback.print_exc()


def atualizar_drawback(dues_str=None, todas=False):
    """
    Atualiza apenas os atos concessorios de suspensao (drawback)
    
    Args:
        dues_str: String com numeros de DUE separados por virgula
        todas: Se True, atualiza todas DUEs que tem atos concessorios
    """
    print("\n[ATUALIZANDO ATOS CONCESSORIOS DE DRAWBACK]")
    print("-" * 40)
    
    try:
        from token_manager import token_manager
        from db_manager import db_manager
        from dotenv import load_dotenv
        
        load_dotenv('config.env')
        
        # Conectar ao banco
        if not db_manager.conectar():
            print("[ERRO] Nao foi possivel conectar ao banco de dados")
            return
        
        # Determinar DUEs a atualizar
        if todas:
            # Buscar todas DUEs que tem atos concessorios
            try:
                cur = db_manager.conn.cursor()
                cur.execute("SELECT DISTINCT numero_due FROM due_atos_concessorios_suspensao")
                dues = [row[0] for row in cur.fetchall()]
                if not dues:
                    print("[INFO] Nenhuma DUE com atos concessorios encontrada")
                    db_manager.desconectar()
                    return
                print(f"[INFO] {len(dues)} DUEs com atos concessorios")
            except Exception as e:
                print(f"[ERRO] Erro ao buscar DUEs: {e}")
                db_manager.desconectar()
                return
        elif dues_str:
            dues = [d.strip() for d in dues_str.split(',') if d.strip()]
            if not dues:
                print("[ERRO] Nenhuma DUE especificada")
                db_manager.desconectar()
                return
            print(f"[INFO] {len(dues)} DUEs para atualizar")
        else:
            print("[ERRO] Especifique DUEs ou use --todas")
            db_manager.desconectar()
            return
        
        # Autenticar
        client_id = os.getenv('SISCOMEX_CLIENT_ID')
        client_secret = os.getenv('SISCOMEX_CLIENT_SECRET')
        
        if not client_id or not client_secret:
            print("[ERRO] Credenciais nao configuradas")
            db_manager.desconectar()
            return
        
        token_manager.configurar_credenciais(client_id, client_secret)
        if not token_manager.autenticar():
            print("[ERRO] Falha na autenticacao")
            db_manager.desconectar()
            return
        
        print("[OK] Autenticado!")
        print()
        
        # Atualizar cada DUE
        atualizadas = 0
        erros = 0
        sem_atos = 0
        
        URL_BASE = "https://portalunico.siscomex.gov.br/due/api/ext/due"
        
        for i, numero_due in enumerate(dues, 1):
            if i % 25 == 0 or len(dues) <= 10:
                print(f"[PROGRESSO] {i}/{len(dues)} - {numero_due}")
            
            try:
                # Consultar atos de suspensao
                url = f"{URL_BASE}/{numero_due}/drawback/suspensao/atos-concessorios"
                response = token_manager.session.get(url, headers=token_manager.obter_headers(), timeout=10)
                
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
                            print(f"  [OK] {len(registros)} atos atualizados")
                    else:
                        sem_atos += 1
                        if len(dues) <= 10:
                            print(f"  [INFO] Nenhum ato encontrado")
                else:
                    erros += 1
                    if len(dues) <= 10:
                        print(f"  [ERRO] Status {response.status_code}")
                        
            except Exception as e:
                erros += 1
                if len(dues) <= 10:
                    print(f"  [ERRO] {str(e)[:50]}")
            
            import time
            time.sleep(0.2)
        
        db_manager.desconectar()
        
        # Resumo
        print("\n" + "-" * 40)
        print(f"[RESUMO]")
        print(f"  - DUEs processadas: {len(dues)}")
        print(f"  - Atualizadas com sucesso: {atualizadas}")
        print(f"  - Sem atos concessorios: {sem_atos}")
        print(f"  - Erros: {erros}")
        
    except Exception as e:
        print(f"[ERRO] {e}")
        import traceback
        traceback.print_exc()


def atualizar_existentes(force=False, limit=None):
    """Executa atualizacao de DUEs existentes"""
    print("\n[ATUALIZANDO DUEs EXISTENTES]")
    print("-" * 40)
    
    if os.path.exists(SCRIPT_SYNC_ATUALIZAR):
        args = []
        if force:
            args.append('--force')
        if limit:
            args.extend(['--limit', str(limit)])
        executar_script(SCRIPT_SYNC_ATUALIZAR, args)
    else:
        print(f"[ERRO] Script {SCRIPT_SYNC_ATUALIZAR} nao encontrado")


def sincronizacao_completa():
    """Executa sincronizacao completa (novas + atualizacao)"""
    print("\n[SINCRONIZACAO COMPLETA]")
    print("=" * 60)
    
    # 1. Sincronizar novas
    sincronizar_novas()
    
    # 2. Atualizar existentes
    atualizar_existentes()
    
    print("\n" + "=" * 60)
    print("[SINCRONIZACAO COMPLETA FINALIZADA]")
    print("=" * 60)


def gerar_script_agendamento():
    """Gera scripts para agendamento no Windows Task Scheduler"""
    print("\n[GERANDO SCRIPTS DE AGENDAMENTO]")
    print("-" * 40)
    
    pasta_scripts = 'scripts'
    os.makedirs(pasta_scripts, exist_ok=True)
    
    # Obter caminho absoluto do Python e do projeto
    python_path = sys.executable
    projeto_path = os.path.abspath(os.path.dirname(__file__))
    
    # Script para sincronizacao de novas (executar a cada hora comercial)
    script_novas = f'''@echo off
REM Sincronizacao de Novas DUEs
REM Sugestao: Executar a cada hora durante horario comercial (8h-18h)

cd /d "{projeto_path}"
"{python_path}" consulta_sap.py
"{python_path}" sync_novas.py

echo.
echo Sincronizacao de novas DUEs concluida!
'''
    
    caminho_novas = os.path.join(pasta_scripts, 'sync_novas.bat')
    with open(caminho_novas, 'w', encoding='utf-8') as f:
        f.write(script_novas)
    print(f"[OK] Criado: {caminho_novas}")
    
    # Script para atualizacao diaria (executar 1x por dia, ex: 6h da manha)
    script_atualizar = f'''@echo off
REM Atualizacao Diaria de DUEs
REM Sugestao: Executar 1x por dia as 6h da manha

cd /d "{projeto_path}"
"{python_path}" sync_atualizar.py

echo.
echo Atualizacao diaria de DUEs concluida!
'''
    
    caminho_atualizar = os.path.join(pasta_scripts, 'sync_atualizar.bat')
    with open(caminho_atualizar, 'w', encoding='utf-8') as f:
        f.write(script_atualizar)
    print(f"[OK] Criado: {caminho_atualizar}")
    
    # Script para sincronizacao completa
    script_completo = f'''@echo off
REM Sincronizacao Completa (Novas + Atualizacao)
REM Sugestao: Executar quando necessario ou 1x por dia

cd /d "{projeto_path}"
"{python_path}" consulta_sap.py
"{python_path}" sync_novas.py
"{python_path}" sync_atualizar.py

echo.
echo Sincronizacao completa concluida!
'''
    
    caminho_completo = os.path.join(pasta_scripts, 'sync_completo.bat')
    with open(caminho_completo, 'w', encoding='utf-8') as f:
        f.write(script_completo)
    print(f"[OK] Criado: {caminho_completo}")
    
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
    print(f"[OK] Criado: {caminho_instrucoes}")
    
    print(instrucoes)


def menu_interativo():
    """Exibe menu interativo"""
    while True:
        exibir_cabecalho()
        
        print("\n[OPCOES]")
        print("  1. Sincronizar novas DUEs (SAP + Siscomex)")
        print("  2. Atualizar DUEs existentes (> 24h)")
        print("  3. Sincronizacao completa (novas + atualizacao)")
        print("  4. Gerar scripts de agendamento")
        print("  5. Status do sistema")
        print("  0. Sair")
        
        print()
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
            print("\nAte logo!")
            break
        else:
            print("\n[AVISO] Opcao invalida!")
        
        print()
        input("Pressione Enter para continuar...")


def main():
    """Funcao principal"""
    parser = argparse.ArgumentParser(
        description='Gerenciador de Sincronizacao DUE',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Exemplos:
  python main.py              # Menu interativo
  python main.py --novas      # Sincronizar apenas novas DUEs
  python main.py --atualizar  # Atualizar apenas DUEs existentes
  python main.py --completo   # Sincronizacao completa
  python main.py --status     # Exibir status do sistema
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
