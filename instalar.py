#!/usr/bin/env python3
"""
Script de instalação e configuração do Sistema de Controle de DU-Es
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def verificar_python():
    """Verifica se a versão do Python é compatível"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ é necessário")
        print(f"   Versão atual: {sys.version}")
        return False
    
    print(f"✅ Python {sys.version.split()[0]} detectado")
    return True

def instalar_dependencias():
    """Instala as dependências do requirements.txt"""
    print("\n📦 Instalando dependências...")
    
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependências instaladas com sucesso")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao instalar dependências: {e}")
        return False

def criar_estrutura_diretorios():
    """Cria a estrutura de diretórios necessária"""
    print("\n📁 Criando estrutura de diretórios...")
    
    diretorios = [
        "dados",
        "dados/due-normalizados",
        "tabelas_suporte",
        "logs"
    ]
    
    for diretorio in diretorios:
        Path(diretorio).mkdir(parents=True, exist_ok=True)
        print(f"   ✅ {diretorio}/")
    
    return True

def verificar_arquivo_env():
    """Verifica se o arquivo .env existe e está configurado"""
    print("\n🔐 Verificando configuração...")
    
    if not os.path.exists(".env"):
        if os.path.exists("config_exemplo.env"):
            print("⚠️  Arquivo .env não encontrado")
            print("   Copiando config_exemplo.env para .env...")
            shutil.copy("config_exemplo.env", ".env")
            print("   ✅ Arquivo .env criado")
        else:
            print("❌ Arquivo config_exemplo.env não encontrado")
            return False
    
    # Verificar se as credenciais estão configuradas
    with open(".env", "r") as f:
        conteudo = f.read()
    
    if "seu_client_id_aqui" in conteudo or "seu_client_secret_aqui" in conteudo:
        print("⚠️  Credenciais não configuradas no arquivo .env")
        print("   Configure SISCOMEX_CLIENT_ID e SISCOMEX_CLIENT_SECRET")
        return False
    
    print("✅ Arquivo .env configurado")
    return True

def testar_instalacao():
    """Testa se a instalação foi bem-sucedida"""
    print("\n🧪 Testando instalação...")
    
    try:
        # Testar importação dos módulos principais
        from token_manager import token_manager
        from siscomexv3 import ler_chaves_nf
        from tabelas_suporte import listar_tabelas_disponivel
        
        print("✅ Módulos principais importados com sucesso")
        
        # Testar token manager
        print("   • Token manager: OK")
        print("   • Siscomex v3: OK")
        print("   • Tabelas suporte: OK")
        
        return True
        
    except ImportError as e:
        print(f"❌ Erro ao importar módulos: {e}")
        return False

def mostrar_proximos_passos():
    """Mostra os próximos passos para o usuário"""
    print("\n" + "="*60)
    print("🎉 INSTALAÇÃO CONCLUÍDA COM SUCESSO!")
    print("="*60)
    
    print("\n📋 PRÓXIMOS PASSOS:")
    print("-" * 30)
    
    print("\n1. 🔐 Configurar credenciais:")
    print("   Edite o arquivo .env e configure:")
    print("   SISCOMEX_CLIENT_ID=seu_client_id_real")
    print("   SISCOMEX_CLIENT_SECRET=seu_client_secret_real")
    
    print("\n2. 📊 Preparar dados:")
    print("   Coloque o arquivo nfe-sap.csv em dados/")
    print("   (Execute primeiro o script SAP para gerar as chaves)")
    
    print("\n3. 🚀 Executar o sistema:")
    print("   python siscomexv3.py          # Para DU-Es")
    print("   python tabelas_suporte.py     # Para tabelas TABX")
    
    print("\n4. 🔍 Testar funcionamento:")
    print("   python teste_rate_limiting.py # Teste de rate limiting")
    print("   python exemplo_uso_rate_limiting.py # Exemplos de uso")
    
    print("\n📚 DOCUMENTAÇÃO:")
    print("-" * 20)
    print("   README.md              # Documentação principal")
    print("   EXEMPLOS_USO.md        # Exemplos práticos")
    print("   CHANGELOG.md           # Histórico de versões")
    
    print("\n🆘 SUPORTE:")
    print("-" * 15)
    print("   Consulte a documentação para troubleshooting")
    print("   Verifique os logs em caso de problemas")
    
    print("\n" + "="*60)

def main():
    """Função principal de instalação"""
    print("🚀 INSTALADOR - Sistema de Controle de DU-Es e Tabelas de Suporte")
    print("="*70)
    
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
        print("\n⚠️  Configure as credenciais no arquivo .env antes de continuar")
        print("   Consulte o README.md para mais informações")
    
    # Testar instalação
    if not testar_instalacao():
        print("\n❌ Instalação falhou - verifique os erros acima")
        sys.exit(1)
    
    # Mostrar próximos passos
    mostrar_proximos_passos()

if __name__ == "__main__":
    main()



