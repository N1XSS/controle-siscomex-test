import json
import os
import threading
import time
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

import pandas as pd
import requests
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Any

from src.core.constants import (
    DEFAULT_HTTP_TIMEOUT_SEC,
    ENV_CONFIG_FILE,
    HTTP_REQUEST_TIMEOUT_SEC,
    SISCOMEX_RATE_LIMIT_HOUR,
)
from src.core.logger import logger
from src.api.siscomex.token import token_manager
warnings.filterwarnings('ignore')

# Carregar variaveis de ambiente
load_dotenv(ENV_CONFIG_FILE)

# Configuracoes da API TABX (Tabelas de Suporte)
URL_TABX_BASE = "https://portalunico.siscomex.gov.br/tabx/api/ext"

def listar_tabelas_disponivel() -> list[dict[str, Any]] | None:
    """Lista todas as tabelas disponiveis na API TABX.
    
    Returns:
        Lista de tabelas ou None.
    """
    try:
        # Verificar e renovar token se necessário
        if not token_manager.renovar_token_se_necessario():
            return None
        
        # Verificar se pode executar listagem de tabelas (limite: 1000/hora)
        funcionalidade = "listar_tabelas"
        pode_executar, motivo = token_manager.pode_executar_funcionalidade(
            funcionalidade,
            limite_por_hora=SISCOMEX_RATE_LIMIT_HOUR,
        )
        
        if not pode_executar:
            logger.info(f"⚠️  {motivo}")
            return None
        
        url_tabelas = f"{URL_TABX_BASE}/tabela"
        logger.info(f"Consultando tabelas disponiveis: {url_tabelas}")
        
        response = token_manager.request(
            "GET",
            url_tabelas,
            headers=token_manager.obter_headers(),
            timeout=DEFAULT_HTTP_TIMEOUT_SEC,
        )
        
        # Registrar execução da funcionalidade
        token_manager.registrar_execucao_funcionalidade(funcionalidade)
        
        # Verificar rate limiting
        if token_manager.verificar_rate_limit(response, funcionalidade):
            return None
        
        if response.status_code == 401:
            logger.info("Token expirado ao listar tabelas")
            return None
        
        response.raise_for_status()
        tabelas = response.json()
        
        logger.info(f"{len(tabelas)} tabelas encontradas")
        return tabelas
        
    except Exception as e:
        logger.info(f"Erro ao listar tabelas: {e}")
        return None

def consultar_metadados_tabela(nome_tabela: str) -> dict[str, Any] | None:
    """Consulta metadados de uma tabela.
    
    Args:
        nome_tabela: Nome da tabela na API TABX.
    
    Returns:
        Metadados da tabela ou None.
    """
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
        
        response = token_manager.request(
            "GET",
            url_metadados,
            headers=token_manager.obter_headers(),
            timeout=DEFAULT_HTTP_TIMEOUT_SEC,
        )
        
        # Registrar execução da funcionalidade
        token_manager.registrar_execucao_funcionalidade(funcionalidade)
        
        # Verificar rate limiting
        if token_manager.verificar_rate_limit(response, funcionalidade):
            return {"error": "rate_limit"}
        
        if response.status_code == 401:
            return {"error": "token_expirado"}
        
        if response.status_code == 404:
            logger.info(f"Tabela {nome_tabela} nao encontrada")
            return None
            
        response.raise_for_status()
        metadados = response.json()
        
        return metadados
        
    except Exception as e:
        logger.info(f"Erro ao consultar metadados da tabela {nome_tabela}: {e}")
        return None

def consultar_dados_tabela(
    nome_tabela: str,
    metadados: dict[str, Any] | None = None,
    nivel: int = 1,
) -> dict[str, Any] | None:
    """Consulta dados de uma tabela TABX.

    Args:
        nome_tabela: Nome da tabela.
        metadados: Metadados existentes.
        nivel: Nivel de profundidade.

    Returns:
        Dados da tabela ou None.
    """
    try:
        if not token_manager.renovar_token_se_necessario():
            return {"error": "token_expirado"}

        funcionalidade = "consulta_dados_tabela"
        pode_executar, motivo = token_manager.pode_executar_funcionalidade(
            funcionalidade, limite_por_hora=1000
        )
        if not pode_executar:
            return {"error": "rate_limit", "motivo": motivo}

        url_dados = f"{URL_TABX_BASE}/tabela/{nome_tabela}?nivel={nivel}"
        if metadados and metadados.get("campos"):
            campos_retorno = [
                {"nomeTabela": nome_tabela, "nome": campo.get("nome", "")} 
                for campo in metadados.get("campos", [])
            ]
            response = token_manager.request(
                "POST",
                url_dados,
                headers=token_manager.obter_headers(),
                json={"campos": campos_retorno},
                timeout=HTTP_REQUEST_TIMEOUT_SEC,
            )
        else:
            response = token_manager.request(
                "GET",
                url_dados,
                headers=token_manager.obter_headers(),
                timeout=HTTP_REQUEST_TIMEOUT_SEC,
            )

        token_manager.registrar_execucao_funcionalidade(funcionalidade)
        if token_manager.verificar_rate_limit(response, funcionalidade):
            return {"error": "rate_limit"}
        if response.status_code == 401:
            return {"error": "token_expirado"}

        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.info(f"Erro ao consultar dados da tabela {nome_tabela}: {e}")
        return None

def processar_tabela_individual(tabela_info: dict[str, Any]) -> dict[str, Any] | None:
    """Processa uma tabela individual.
    
    Args:
        tabela_info: Descritor da tabela.
    
    Returns:
        Resultado processado ou None.
    """
    nome_tabela = tabela_info.get('nome', '')
    
    if not nome_tabela:
        return None
    
    logger.info(f"Processando tabela: {nome_tabela}")
    
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

def normalizar_dados_tabela(resultado_tabela: dict[str, Any]) -> dict[str, Any]:
    """Normaliza dados retornados.
    
    Args:
        resultado_tabela: Resultado bruto da tabela.
    
    Returns:
        Dados normalizados por estrutura.
    """
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

def salvar_tabelas_suporte(
    dados_consolidados: dict[str, Any],
    pasta: str = 'dados/tabelas-suporte',
) -> None:
    """
    DEPRECATED: Função removida. Use apenas PostgreSQL.

    Esta função foi removida porque o sistema agora usa exclusivamente PostgreSQL.
    Use db_manager para salvar tabelas de suporte no PostgreSQL.
    """
    raise NotImplementedError(
        "Salvamento de tabelas de suporte em CSV foi removido. "
        "O sistema agora usa exclusivamente PostgreSQL. "
        "Use db_manager.salvar_tabelas_suporte() ao invés desta função."
    )

def criar_resumo_tabelas_suporte(dados_consolidados: dict[str, Any], pasta: str) -> None:
    """
    DEPRECATED: Função removida. Use apenas PostgreSQL.

    Esta função foi removida porque o sistema agora usa exclusivamente PostgreSQL.
    """
    raise NotImplementedError(
        "Criação de resumo em CSV foi removida. "
        "Use queries SQL no PostgreSQL para gerar relatórios."
    )

def baixar_tabelas_suporte(
    client_id: str,
    client_secret: str,
    max_workers: int = 8,
) -> dict[str, Any] | None:
    """Baixa todas as tabelas de suporte.

    Args:
        client_id: Client ID do Siscomex.
        client_secret: Client Secret do Siscomex.
        max_workers: Numero de workers.

    Returns:
        Dados consolidados ou None.
    """
    logger.info("=" * 70)
    logger.info("DOWNLOAD TABELAS DE SUPORTE SISCOMEX TABX")
    logger.info("=" * 70)
    logger.info(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    logger.info("Funcionalidades:")
    logger.info("   • Download de todas as tabelas de suporte")
    logger.info("   • Metadados completos com relacionamentos")
    logger.info("   • Estruturacao em CSVs normalizados")
    logger.info("   • Processamento paralelo otimizado")
    logger.info("=" * 70)
    
    # Configurar credenciais no token manager compartilhado
    token_manager.configurar_credenciais(client_id, client_secret)
    
    # Autenticacao
    if not token_manager.autenticar():
        logger.info("Falha na autenticacao")
        return None
    
    # Listar tabelas disponiveis
    tabelas = listar_tabelas_disponivel()
    if not tabelas:
        logger.info("Nao foi possivel obter lista de tabelas")
        return None
    
    logger.info(f"\n{len(tabelas)} tabelas encontradas para download")
    
    # Confirmar processamento
    resposta = input("Deseja continuar com o download? (s/n): ").lower()
    if resposta != 's':
        logger.info("Download cancelado")
        return None
    
    # Dados consolidados
    dados_consolidados = {}
    
    # Processar tabelas em paralelo
    tokens_expirados = []
    resultados_processados = 0
    rate_limit_atingido = False
    
    logger.info(f"\nProcessando {len(tabelas)} tabelas em paralelo...")
    logger.info("=" * 60)
    
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
                    logger.info(f"\n❌ RATE LIMIT ATINGIDO na tabela {nome_tabela} - PARANDO PROCESSAMENTO")
                    rate_limit_atingido = True
                    break
                
                # Verificar se token expirou
                if isinstance(resultado, dict) and resultado.get("error") == "token_expirado":
                    tokens_expirados.append(nome_tabela)
                    logger.info(f"[{resultados_processados:3d}/{len(tabelas)}] Token expirado: {nome_tabela}")
                elif resultado:
                    # Normalizar dados da tabela
                    dados_normalizados = normalizar_dados_tabela(resultado)
                    
                    # Consolidar nos dados principais
                    for estrutura, dados in dados_normalizados.items():
                        if estrutura not in dados_consolidados:
                            dados_consolidados[estrutura] = []
                        dados_consolidados[estrutura].extend(dados)
                    
                    logger.info(f"[{resultados_processados:3d}/{len(tabelas)}] OK: {nome_tabela} -> {len(dados_normalizados[f'tabela_{nome_tabela.lower()}'])} registros")
                else:
                    logger.info(f"[{resultados_processados:3d}/{len(tabelas)}] Sem dados: {nome_tabela}")
                    
            except Exception as e:
                logger.info(f"[{resultados_processados:3d}/{len(tabelas)}] Erro: {nome_tabela} -> {str(e)[:30]}")
            
            # Progress feedback a cada 10 processados
            if resultados_processados % 10 == 0:
                percentual = (resultados_processados / len(tabelas)) * 100
                logger.info(f"    Progresso: {percentual:.1f}%")
    
    # Se rate limit foi atingido, não reprocessar
    if rate_limit_atingido:
        logger.info("\n❌ PROCESSAMENTO INTERROMPIDO POR RATE LIMIT")
        logger.info("   Aguarde até o próximo período para continuar")
        return
    
    # Reprocessar tabelas com token expirado se houver
    if tokens_expirados:
        logger.info(f"\nReprocessando {len(tokens_expirados)} tabelas com token expirado...")
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
                        logger.info(f"    OK: {nome_tabela} -> Reprocessado com sucesso")
                time.sleep(0.3)  # Pequeno delay
    
    logger.info("=" * 60)
    
    # Salvar resultados
    if dados_consolidados:
        salvar_tabelas_suporte(dados_consolidados)
        
        logger.info(f"\nESTATISTICAS FINAIS:")
        logger.info("-" * 50)
        
        tabelas_salvas = len([k for k in dados_consolidados.keys() if not k.endswith('_metadados')])
        total_registros = sum(len(v) for k, v in dados_consolidados.items() if not k.endswith('_metadados'))
        
        logger.info(f"Total de tabelas baixadas: {tabelas_salvas}")
        logger.info(f"Total de registros: {total_registros:,}")
        logger.info(f"Processamento concluido com sucesso!")
        
    else:
        logger.info("Nenhum dado foi baixado")
    
    logger.info("\n" + "=" * 70)
    logger.info("DOWNLOAD FINALIZADO")
    logger.info("=" * 70)
    return dados_consolidados

def main() -> None:
    """Funcao principal de download TABX."""
    # Verificar credenciais
    client_id = os.environ.get("SISCOMEX_CLIENT_ID")
    client_secret = os.environ.get("SISCOMEX_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        logger.info("Credenciais do Siscomex nao encontradas nas variaveis de ambiente")
        logger.info("Configure as variaveis SISCOMEX_CLIENT_ID e SISCOMEX_CLIENT_SECRET no arquivo .env")
        return
    
    # Executar download
    baixar_tabelas_suporte(client_id, client_secret)

if __name__ == "__main__":
    main()
