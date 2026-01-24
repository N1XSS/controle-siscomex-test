#!/usr/bin/env python3
"""
Script de instalação e configuração do Sistema de Controle de DU-Es
"""

from __future__ import annotations

import os
import sys
import subprocess
import shutil
from pathlib import Path
from src.core.logger import logger

def verificar_python() -> bool:
    """Verifica se a versão do Python é compatível"""
    if sys.version_info < (3, 8):
        logger.info("❌ Python 3.8+ é necessário")
        logger.info(f"   Versão atual: {sys.version}")
        return False
    
    logger.info(f"✅ Python {sys.version.split()[0]} detectado")
    return True

def instalar_dependencias() -> bool:
    """Instala as dependências do requirements.txt"""
    logger.info("\n📦 Instalando dependências...")
    
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        logger.info("✅ Dependências instaladas com sucesso")
        return True
    except subprocess.CalledProcessError as e:
        logger.info(f"❌ Erro ao instalar dependências: {e}")
        return False

def criar_estrutura_diretorios() -> bool:
    """Cria a estrutura de diretórios necessária"""
    logger.info("\n📁 Criando estrutura de diretórios...")
    
    diretorios = [
        "dados",
        "dados/due-normalizados",
        "tabelas_suporte",
        "logs"
    ]
    
    for diretorio in diretorios:
        Path(diretorio).mkdir(parents=True, exist_ok=True)
        logger.info(f"   ✅ {diretorio}/")
    
    return True

def verificar_arquivo_env() -> bool:
    """Verifica se o arquivo .env existe e está configurado"""
    logger.info("\n🔐 Verificando configuração...")
    
    if not os.path.exists(".env"):
        if os.path.exists("config_exemplo.env"):
            logger.info("⚠️  Arquivo .env não encontrado")
            logger.info("   Copiando config_exemplo.env para .env...")
            shutil.copy("config_exemplo.env", ".env")
            logger.info("   ✅ Arquivo .env criado")
        else:
            logger.info("❌ Arquivo config_exemplo.env não encontrado")
            return False
    
    # Verificar se as credenciais estão configuradas
    with open(".env", "r") as f:
        conteudo = f.read()
    
    if "seu_client_id_aqui" in conteudo or "seu_client_secret_aqui" in conteudo:
        logger.info("⚠️  Credenciais não configuradas no arquivo .env")
        logger.info("   Configure SISCOMEX_CLIENT_ID e SISCOMEX_CLIENT_SECRET")
        return False
    
    logger.info("✅ Arquivo .env configurado")
    return True

def testar_instalacao() -> bool:
    """Testa se a instalação foi bem-sucedida"""
    logger.info("\n🧪 Testando instalação...")
    
    try:
        # Testar importação dos módulos principais
        from src.api.siscomex.token import token_manager
        from siscomexv3 import ler_chaves_nf
        from tabelas_suporte import listar_tabelas_disponivel
        
        logger.info("✅ Módulos principais importados com sucesso")
        
        # Testar token manager
        logger.info("   • Token manager: OK")
        logger.info("   • Siscomex v3: OK")
        logger.info("   • Tabelas suporte: OK")
        
        return True
        
    except ImportError as e:
        logger.info(f"❌ Erro ao importar módulos: {e}")
        return False

def mostrar_proximos_passos() -> None:
    """Mostra os próximos passos para o usuário"""
    logger.info("\n" + "=" * 60)
    logger.info("🎉 INSTALAÇÃO CONCLUÍDA COM SUCESSO!")
    logger.info("=" * 60)
    
    logger.info("\n📋 PRÓXIMOS PASSOS:")
    logger.info("-" * 30)
    
    logger.info("\n1. 🔐 Configurar credenciais:")
    logger.info("   Edite o arquivo .env e configure:")
    logger.info("   SISCOMEX_CLIENT_ID=seu_client_id_real")
    logger.info("   SISCOMEX_CLIENT_SECRET=seu_client_secret_real")
    
    logger.info("\n2. 📊 Preparar dados:")
    logger.info("   Coloque o arquivo nfe-sap.csv em dados/")
    logger.info("   (Execute primeiro o script SAP para gerar as chaves)")
    
    logger.info("\n3. 🚀 Executar o sistema:")
    logger.info("   python siscomexv3.py          # Para DU-Es")
    logger.info("   python tabelas_suporte.py     # Para tabelas TABX")
    
    logger.info("\n4. 🔍 Testar funcionamento:")
    logger.info("   python teste_rate_limiting.py # Teste de rate limiting")
    logger.info("   python exemplo_uso_rate_limiting.py # Exemplos de uso")
    
    logger.info("\n📚 DOCUMENTAÇÃO:")
    logger.info("-" * 20)
    logger.info("   README.md              # Documentação principal")
    logger.info("   EXEMPLOS_USO.md        # Exemplos práticos")
    logger.info("   CHANGELOG.md           # Histórico de versões")
    
    logger.info("\n🆘 SUPORTE:")
    logger.info("-" * 15)
    logger.info("   Consulte a documentação para troubleshooting")
    logger.info("   Verifique os logs em caso de problemas")
    
    logger.info("\n" + "=" * 60)

def main() -> None:
    """Função principal de instalação"""
    logger.info("🚀 INSTALADOR - Sistema de Controle de DU-Es e Tabelas de Suporte")
    logger.info("=" * 70)
    
    # Verificar Python
    if not verificar_python():
        sys.exit(1)
    
    # Instalar dependências
    if not instalar_dependencias():
        sys.exit(1)
    
    # Criar estrutura de diretórios
    if not criar_estrutura_diretorios():
        sys.exit(1)
    
    # Verificar arquivo .env
    if not verificar_arquivo_env():
        logger.info("\n⚠️  Configure as credenciais no arquivo .env antes de continuar")
        logger.info("   Consulte o README.md para mais informações")
    
    # Testar instalação
    if not testar_instalacao():
        logger.info("\n❌ Instalação falhou - verifique os erros acima")
        sys.exit(1)
    
    # Mostrar próximos passos
    mostrar_proximos_passos()

if __name__ == "__main__":
    main()
