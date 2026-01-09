import os
import pandas as pd
import requests
import time
import json
from datetime import datetime, timedelta
import warnings
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from token_manager import token_manager
warnings.filterwarnings('ignore')

# Carregar variaveis de ambiente
load_dotenv()

# Configuracoes da API TABX (Tabelas de Suporte)
URL_TABX_BASE = "https://portalunico.siscomex.gov.br/tabx/api/ext"

def listar_tabelas_disponivel():
    """Lista todas as tabelas disponiveis na API TABX"""
    try:
        # Verificar e renovar token se necessário
        if not token_manager.renovar_token_se_necessario():
            return None
        
        # Verificar se pode executar listagem de tabelas (limite: 1000/hora)
        funcionalidade = "listar_tabelas"
        pode_executar, motivo = token_manager.pode_executar_funcionalidade(funcionalidade, limite_por_hora=1000)
        
        if not pode_executar:
            print(f"⚠️  {motivo}")
            return None
        
        url_tabelas = f"{URL_TABX_BASE}/tabela"
        print(f"Consultando tabelas disponiveis: {url_tabelas}")
        
        response = token_manager.session.get(url_tabelas, headers=token_manager.obter_headers(), timeout=10)
        
        # Registrar execução da funcionalidade
        token_manager.registrar_execucao_funcionalidade(funcionalidade)
        
        # Verificar rate limiting
        if token_manager.verificar_rate_limit(response, funcionalidade):
            return None
        
        if response.status_code == 401:
            print("Token expirado ao listar tabelas")
            return None
        
        response.raise_for_status()
        tabelas = response.json()
        
        print(f"{len(tabelas)} tabelas encontradas")
        return tabelas
        
    except Exception as e:
        print(f"Erro ao listar tabelas: {e}")
        return None

def consultar_metadados_tabela(nome_tabela):
    """Consulta metadados de uma tabela especifica"""
    try:
        # Verificar e renovar token se necessário
        if not token_manager.renovar_token_se_necessario():
            return {"error": "token_expirado"}
        
        # Verificar se pode executar consulta de metadados (limite: 1000/hora)
        funcionalidade = "consulta_metadados"
        pode_executar, motivo = token_manager.pode_executar_funcionalidade(funcionalidade, limite_por_hora=1000)
        
        if not pode_executar:
            return {"error": "rate_limit", "motivo": motivo}
        
        url_metadados = f"{URL_TABX_BASE}/tabela/{nome_tabela}/metadado"
        
        response = token_manager.session.get(url_metadados, headers=token_manager.obter_headers(), timeout=8)
        
        # Registrar execução da funcionalidade
        token_manager.registrar_execucao_funcionalidade(funcionalidade)
        
        # Verificar rate limiting
        if token_manager.verificar_rate_limit(response, funcionalidade):
            return {"error": "rate_limit"}
        
        if response.status_code == 401:
            return {"error": "token_expirado"}
        
        if response.status_code == 404:
            print(f"Tabela {nome_tabela} nao encontrada")
            return None
            
        response.raise_for_status()
        metadados = response.json()
        
        return metadados
        
    except Exception as e:
        print(f"Erro ao consultar metadados da tabela {nome_tabela}: {e}")
        return None

def consultar_dados_tabela(nome_tabela, metadados=None, nivel=1):
    """Consulta dados completos de uma tabela com nivel 1 (incluindo estrangeiras)"""
    try:
        # Verificar e renovar token se necessário
        if not token_manager.renovar_token_se_necessario():
            return {"error": "token_expirado"}
        
        # Verificar se pode executar consulta de dados (limite: 1000/hora)
        funcionalidade = "consulta_dados_tabela"
        pode_executar, motivo = token_manager.pode_executar_funcionalidade(funcionalidade, limite_por_hora=1000)
        
        if not pode_executar:
            return {"error": "rate_limit", "motivo": motivo}
        
        url_dados = f"{URL_TABX_BASE}/tabela/{nome_tabela}?nivel={nivel}"
        
        # Se metadados estao disponiveis, solicitar todos os campos explicitamente
        if metadados and metadados.get('campos'):
            campos_retorno = []
            for campo in metadados.get('campos', []):
                campos_retorno.append({
                    "nomeTabela": nome_tabela,
                    "nome": campo.get('nome', '')
                })
            
            if campos_retorno:
                import urllib.parse
                campos_json = json.dumps(campos_retorno)
                campos_encoded = urllib.parse.quote(campos_json)
                url_dados += f"&camposRetorno={campos_encoded}"
                print(f"  Solicitando {len(campos_retorno)} campos especificos para {nome_tabela}")
        
        response = token_manager.session.get(url_dados, headers=token_manager.obter_headers(), timeout=15)
        
        # Registrar execução da funcionalidade
        token_manager.registrar_execucao_funcionalidade(funcionalidade)
        
        # Verificar rate limiting
        if token_manager.verificar_rate_limit(response, funcionalidade):
            return {"error": "rate_limit"}
        
        if response.status_code == 401:
            return {"error": "token_expirado"}
        
        if response.status_code == 404:
            print(f"Dados da tabela {nome_tabela} nao encontrados")
            return None
            
        response.raise_for_status()
        dados = response.json()
        
        return dados
        
    except Exception as e:
        print(f"Erro ao consultar dados da tabela {nome_tabela}: {e}")
        return None

def processar_tabela_individual(tabela_info):
    """Processa uma tabela individual - funcao para ThreadPoolExecutor"""
    nome_tabela = tabela_info.get('nome', '')
    
    if not nome_tabela:
        return None
    
    print(f"Processando tabela: {nome_tabela}")
    
    # Consultar metadados
    metadados = consultar_metadados_tabela(nome_tabela)
    if isinstance(metadados, dict) and metadados.get("error") == "rate_limit":
        return {"error": "rate_limit", "tabela": nome_tabela}
    if isinstance(metadados, dict) and metadados.get("error") == "token_expirado":
        return {"error": "token_expirado", "tabela": nome_tabela}
    
    # Consultar dados (passando metadados para obter todos os campos)
    dados = consultar_dados_tabela(nome_tabela, metadados)
    if isinstance(dados, dict) and dados.get("error") == "rate_limit":
        return {"error": "rate_limit", "tabela": nome_tabela}
    if isinstance(dados, dict) and dados.get("error") == "token_expirado":
        return {"error": "token_expirado", "tabela": nome_tabela}
    
    if not dados or not metadados:
        return None
    
    return {
        "nome_tabela": nome_tabela,
        "metadados": metadados,
        "dados": dados,
        "info": tabela_info
    }

def normalizar_dados_tabela(resultado_tabela):
    """Normaliza os dados de uma tabela para CSV estruturado"""
    nome_tabela = resultado_tabela["nome_tabela"]
    metadados = resultado_tabela["metadados"]
    dados_response = resultado_tabela["dados"]
    
    # Estrutura para armazenar dados normalizados
    dados_normalizados = {
        f"tabela_{nome_tabela.lower()}": [],
        f"tabela_{nome_tabela.lower()}_metadados": []
    }
    
    # 1. Salvar metadados da tabela
    if metadados and metadados.get('campos'):
        for campo in metadados.get('campos', []):
            meta_row = {
                'nome_tabela': nome_tabela,
                'campo_nome': campo.get('nome', ''),
                'campo_tipo': campo.get('tipo', ''),
                'campo_tamanho': campo.get('tamanho', 0),
                'campo_obrigatorio': campo.get('obrigatorio', False),
                'campo_chave_negocio': campo.get('chaveNegocio', False),
                'campo_estrangeiro': campo.get('campoEstrangeiro', False),
                'tabela_estrangeira': campo.get('nomeTabelaEstrangeira', ''),
                'campo_descricao': campo.get('descricao', ''),
                'campo_rotulo': campo.get('rotulo', ''),
                'possui_dominio': campo.get('possuiDominio', False)
            }
            dados_normalizados[f"tabela_{nome_tabela.lower()}_metadados"].append(meta_row)
    
    # 2. Processar dados da tabela principal
    if dados_response and dados_response.get('dados'):
        for registro in dados_response.get('dados', []):
            if registro.get('campos'):
                data_row = {'nome_tabela': nome_tabela}
                
                # Processar campos do registro
                for campo in registro.get('campos', []):
                    nome_campo = campo.get('nome', '')
                    valor_campo = campo.get('valor', '')
                    
                    # Limpar nome do campo para usar como coluna
                    nome_coluna = nome_campo.lower().replace(' ', '_')
                    data_row[nome_coluna] = valor_campo
                    
                    # Se ha dados de tabela estrangeira, adicionar com prefixo
                    dados_estrangeira = campo.get('dadosTabelaEstrangeira')
                    if dados_estrangeira and dados_estrangeira.get('dados'):
                        for reg_estrangeiro in dados_estrangeira.get('dados', []):
                            for campo_est in reg_estrangeiro.get('campos', []):
                                nome_est = f"{dados_estrangeira.get('nomeTabela', '').lower()}_{campo_est.get('nome', '').lower()}"
                                data_row[nome_est] = campo_est.get('valor', '')
                
                dados_normalizados[f"tabela_{nome_tabela.lower()}"].append(data_row)
    
    return dados_normalizados

def salvar_tabelas_suporte(dados_consolidados, pasta='dados/tabelas-suporte'):
    """Salva todas as tabelas de suporte em CSVs estruturados"""
    
    # Garantir que a pasta existe
    if not os.path.exists(pasta):
        os.makedirs(pasta)
    
    print(f"\nSalvando tabelas de suporte em: {pasta}")
    print("-" * 60)
    
    total_tabelas = 0
    total_registros = 0
    
    for nome_estrutura, dados in dados_consolidados.items():
        if dados:  # So salvar se houver dados
            arquivo = os.path.join(pasta, f"{nome_estrutura}.csv")
            df = pd.DataFrame(dados)
            df.to_csv(arquivo, sep=';', index=False, encoding='utf-8-sig')
            print(f"   {nome_estrutura}.csv -> {len(df)} registros")
            total_tabelas += 1
            total_registros += len(df)
        else:
            print(f"   {nome_estrutura}.csv -> Sem dados")
    
    print("-" * 60)
    print(f"Total: {total_tabelas} arquivos CSV com {total_registros:,} registros")
    
    # Criar arquivo de resumo
    criar_resumo_tabelas_suporte(dados_consolidados, pasta)

def criar_resumo_tabelas_suporte(dados_consolidados, pasta):
    """Cria arquivo de resumo das tabelas de suporte"""
    resumo = []
    
    # Agrupar por tabela principal
    tabelas_principais = set()
    for nome_estrutura in dados_consolidados.keys():
        if not nome_estrutura.endswith('_metadados'):
            tabela_principal = nome_estrutura.replace('tabela_', '')
            tabelas_principais.add(tabela_principal)
    
    for tabela in sorted(tabelas_principais):
        dados_tabela = dados_consolidados.get(f"tabela_{tabela}", [])
        metadados_tabela = dados_consolidados.get(f"tabela_{tabela}_metadados", [])
        
        if dados_tabela or metadados_tabela:
            resumo.append({
                'nome_tabela': tabela.upper(),
                'registros_dados': len(dados_tabela),
                'campos_metadados': len(metadados_tabela),
                'arquivo_dados': f"tabela_{tabela}.csv",
                'arquivo_metadados': f"tabela_{tabela}_metadados.csv"
            })
    
    if resumo:
        arquivo_resumo = os.path.join(pasta, "resumo_tabelas_suporte.csv")
        df_resumo = pd.DataFrame(resumo)
        df_resumo.to_csv(arquivo_resumo, sep=';', index=False, encoding='utf-8-sig')
        print(f"Resumo salvo em: resumo_tabelas_suporte.csv")

def baixar_tabelas_suporte(client_id, client_secret, max_workers=8):
    """Baixa todas as tabelas de suporte do Siscomex TABX"""
    
    print("=" * 70)
    print("DOWNLOAD TABELAS DE SUPORTE SISCOMEX TABX")
    print("=" * 70)
    print(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("Funcionalidades:")
    print("   • Download de todas as tabelas de suporte")
    print("   • Metadados completos com relacionamentos")
    print("   • Estruturacao em CSVs normalizados")
    print("   • Processamento paralelo otimizado")
    print("=" * 70)
    
    # Configurar credenciais no token manager compartilhado
    token_manager.configurar_credenciais(client_id, client_secret)
    
    # Autenticacao
    if not token_manager.autenticar():
        print("Falha na autenticacao")
        return
    
    # Listar tabelas disponiveis
    tabelas = listar_tabelas_disponivel()
    if not tabelas:
        print("Nao foi possivel obter lista de tabelas")
        return
    
    print(f"\n{len(tabelas)} tabelas encontradas para download")
    
    # Confirmar processamento
    resposta = input("Deseja continuar com o download? (s/n): ").lower()
    if resposta != 's':
        print("Download cancelado")
        return
    
    # Dados consolidados
    dados_consolidados = {}
    
    # Processar tabelas em paralelo
    tokens_expirados = []
    resultados_processados = 0
    rate_limit_atingido = False
    
    print(f"\nProcessando {len(tabelas)} tabelas em paralelo...")
    print("=" * 60)
    
    # Processar em lotes paralelos
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submeter todas as tarefas
        future_to_tabela = {
            executor.submit(processar_tabela_individual, tabela): tabela['nome'] 
            for tabela in tabelas
        }
        
        # Processar resultados conforme ficam prontos
        for future in as_completed(future_to_tabela):
            nome_tabela = future_to_tabela[future]
            resultados_processados += 1
            
            try:
                resultado = future.result()
                
                # Verificar se rate limit foi atingido - PARAR IMEDIATAMENTE
                if isinstance(resultado, dict) and resultado.get("error") == "rate_limit":
                    print(f"\n❌ RATE LIMIT ATINGIDO na tabela {nome_tabela} - PARANDO PROCESSAMENTO")
                    rate_limit_atingido = True
                    break
                
                # Verificar se token expirou
                if isinstance(resultado, dict) and resultado.get("error") == "token_expirado":
                    tokens_expirados.append(nome_tabela)
                    print(f"[{resultados_processados:3d}/{len(tabelas)}] Token expirado: {nome_tabela}")
                elif resultado:
                    # Normalizar dados da tabela
                    dados_normalizados = normalizar_dados_tabela(resultado)
                    
                    # Consolidar nos dados principais
                    for estrutura, dados in dados_normalizados.items():
                        if estrutura not in dados_consolidados:
                            dados_consolidados[estrutura] = []
                        dados_consolidados[estrutura].extend(dados)
                    
                    print(f"[{resultados_processados:3d}/{len(tabelas)}] OK: {nome_tabela} -> {len(dados_normalizados[f'tabela_{nome_tabela.lower()}'])} registros")
                else:
                    print(f"[{resultados_processados:3d}/{len(tabelas)}] Sem dados: {nome_tabela}")
                    
            except Exception as e:
                print(f"[{resultados_processados:3d}/{len(tabelas)}] Erro: {nome_tabela} -> {str(e)[:30]}")
            
            # Progress feedback a cada 10 processados
            if resultados_processados % 10 == 0:
                percentual = (resultados_processados / len(tabelas)) * 100
                print(f"    Progresso: {percentual:.1f}%")
    
    # Se rate limit foi atingido, não reprocessar
    if rate_limit_atingido:
        print("\n❌ PROCESSAMENTO INTERROMPIDO POR RATE LIMIT")
        print("   Aguarde até o próximo período para continuar")
        return
    
    # Reprocessar tabelas com token expirado se houver
    if tokens_expirados:
        print(f"\nReprocessando {len(tokens_expirados)} tabelas com token expirado...")
        if token_manager.autenticar():
            for nome_tabela in tokens_expirados:
                tabela_info = next((t for t in tabelas if t.get('nome') == nome_tabela), {})
                if tabela_info:
                    resultado = processar_tabela_individual(tabela_info)
                    if resultado:
                        dados_normalizados = normalizar_dados_tabela(resultado)
                        for estrutura, dados in dados_normalizados.items():
                            if estrutura not in dados_consolidados:
                                dados_consolidados[estrutura] = []
                            dados_consolidados[estrutura].extend(dados)
                        print(f"    OK: {nome_tabela} -> Reprocessado com sucesso")
                time.sleep(0.3)  # Pequeno delay
    
    print("=" * 60)
    
    # Salvar resultados
    if dados_consolidados:
        salvar_tabelas_suporte(dados_consolidados)
        
        print(f"\nESTATISTICAS FINAIS:")
        print("-" * 50)
        
        tabelas_salvas = len([k for k in dados_consolidados.keys() if not k.endswith('_metadados')])
        total_registros = sum(len(v) for k, v in dados_consolidados.items() if not k.endswith('_metadados'))
        
        print(f"Total de tabelas baixadas: {tabelas_salvas}")
        print(f"Total de registros: {total_registros:,}")
        print(f"Processamento concluido com sucesso!")
        
    else:
        print("Nenhum dado foi baixado")
    
    print("\n" + "=" * 70)
    print("DOWNLOAD FINALIZADO")
    print("=" * 70)

def main():
    """Funcao principal"""
    # Verificar credenciais
    client_id = os.environ.get("SISCOMEX_CLIENT_ID")
    client_secret = os.environ.get("SISCOMEX_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        print("Credenciais do Siscomex nao encontradas nas variaveis de ambiente")
        print("Configure as variaveis SISCOMEX_CLIENT_ID e SISCOMEX_CLIENT_SECRET no arquivo .env")
        return
    
    # Executar download
    baixar_tabelas_suporte(client_id, client_secret)

if __name__ == "__main__":
    main()
