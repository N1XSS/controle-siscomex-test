import os
import sys
import requests
import time
import json
import pickle
from datetime import datetime, timedelta, timezone
import threading
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from dotenv import load_dotenv

load_dotenv()

# Configurar encoding para Windows
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass  # Se não conseguir reconfigurar, continua normalmente

# Configuracoes da API
URL_AUTH = "https://portalunico.siscomex.gov.br/portal/api/autenticar/chave-acesso"
TOKEN_CACHE_FILE = "token_cache.pkl"

class SharedTokenManager:
    """
    Gerenciador de tokens compartilhado - OTIMIZADO PARA PROCESSAMENTO EM LOTE
    
    OTIMIZAÇÕES IMPLEMENTADAS:
    • Singleton pattern para compartilhamento entre threads
    • Cache persistente com validade de 60min (padrão Siscomex)
    • Margem de segurança de 2min para evitar expirações durante processamento
    • Pool de conexões HTTP reutilizáveis
    • Parsing inteligente do timestamp de expiração (x-csrf-expiration em ms)
    • Debug detalhado dos headers de autenticação
    • Método status_token() para monitoramento
    • Controle de intervalo mínimo de 60s entre autenticações (regra Siscomex)
    • Reutilização inteligente de tokens válidos
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.set_token = None
        self.csrf_token = None
        self.expiracao = None
        self.session = None
        self.client_id = None
        self.client_secret = None
        self.ultima_autenticacao = None  # Controle de intervalo mínimo de 60s
        
        self._setup_session()
        self._carregar_token_cache()  # Carregar token do cache se existe
        self._initialized = True
    
    def _setup_session(self):
        """Configura sessao HTTP"""
        self.session = requests.Session()
        
        # Configurar retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        
        # Configurar adapter com pool de conexoes
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=20,
            pool_maxsize=20
        )
        
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def configurar_credenciais(self, client_id, client_secret):
        """Configura as credenciais para autenticacao"""
        self.client_id = client_id
        self.client_secret = client_secret
    
    def token_valido(self):
        """Verifica se o token ainda e valido - SEM LOCK para evitar deadlock"""
        if not (self.set_token and self.csrf_token and self.expiracao):
            return False
        
        # Verificar se o token ainda não expirou (sem margem excessiva)
        # Usar apenas 2 minutos de margem para maximizar uso do token
        agora = datetime.utcnow()
        margem_seguranca = timedelta(minutes=2)  # Reduzido de 5 para 2 minutos
        
        return agora < (self.expiracao - margem_seguranca)
    
    def obter_headers(self):
        """Retorna headers para requisicoes - SEM LOCK"""
        return {
            'Authorization': self.set_token,
            'X-CSRF-Token': self.csrf_token,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    def autenticar(self, forcar_nova_auth=False):
        """Autentica e obtem novos tokens - OTIMIZADO PARA EVITAR AUTENTICAÇÕES DESNECESSÁRIAS"""
        # Usar lock apenas quando necessário
        with self._lock:
            # REGRA PRINCIPAL: Se token ainda é válido, NUNCA fazer nova autenticação
            if not forcar_nova_auth and self.token_valido():
                tempo_restante = (self.expiracao - datetime.utcnow()).total_seconds() / 60
                print(f"✅ REUTILIZANDO token existente! Válido por mais {tempo_restante:.1f} min")
                return True
            
            # Se chegou aqui, token realmente precisa ser renovado
            agora = datetime.utcnow()
            if self.expiracao:
                tempo_real = (self.expiracao - agora).total_seconds() / 60
                if tempo_real > 0:
                    print(f"🔄 Renovando token antecipadamente (margem segurança): {tempo_real:.1f} min restantes")
                else:
                    print(f"🔄 Token REALMENTE expirado há {abs(tempo_real):.1f} min - nova autenticação necessária")
            else:
                print(f"🔄 Primeira autenticação ou token inválido")
            
            if not self.client_id or not self.client_secret:
                print("❌ Credenciais não configuradas")
                return False
            
            # REGRA SISCOMEX: Intervalo mínimo de 60 segundos entre autenticações
            if self.ultima_autenticacao:
                tempo_desde_ultima = (agora - self.ultima_autenticacao).total_seconds()
                if tempo_desde_ultima < 60:
                    tempo_restante = 60 - tempo_desde_ultima
                    print(f"⏳ Aguardando {tempo_restante:.1f}s (intervalo mínimo de 60s entre autenticações - regra Siscomex)...")
                    time.sleep(tempo_restante)
            
            print("🔑 Autenticando com Siscomex API...")
            
            try:
                headers_auth = {
                    'Client-Id': self.client_id,
                    'Client-Secret': self.client_secret,
                    'Role-Type': 'IMPEXP',
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                }
                
                # Timeout menor para evitar travamento
                response_auth = self.session.post(URL_AUTH, json={}, headers=headers_auth, timeout=15)
                
                # Verificar rate limiting (422)
                if response_auth.status_code == 422:
                    print("⏳ Rate limiting detectado (422) - aguardando 60s (intervalo mínimo Siscomex)...")
                    time.sleep(60)  # Intervalo mínimo de 60 segundos conforme regra Siscomex
                    # Verificar novamente se já passou 60s desde última autenticação
                    if self.ultima_autenticacao:
                        tempo_desde_ultima = (datetime.utcnow() - self.ultima_autenticacao).total_seconds()
                        if tempo_desde_ultima < 60:
                            tempo_restante = 60 - tempo_desde_ultima
                            print(f"⏳ Aguardando mais {tempo_restante:.1f}s para respeitar intervalo mínimo...")
                            time.sleep(tempo_restante)
                    # Tentar novamente
                    print("🔄 Tentando autenticação novamente...")
                    response_auth = self.session.post(URL_AUTH, json={}, headers=headers_auth, timeout=15)
                
                if response_auth.status_code == 401:
                    print("❌ Credenciais inválidas (401)")
                    return False
                elif response_auth.status_code == 403:
                    print("❌ Acesso negado (403) - verificar permissões")
                    return False
                
                response_auth.raise_for_status()
                
                # Debug: mostrar headers recebidos
                headers_debug = {k.lower(): v for k, v in response_auth.headers.items() 
                               if any(x in k.lower() for x in ['token', 'csrf', 'expir'])}
                print(f"🔍 Headers de autenticação recebidos: {headers_debug}")
            
                self.set_token = response_auth.headers.get('set-token') or response_auth.headers.get('Set-Token')
                self.csrf_token = response_auth.headers.get('x-csrf-token') or response_auth.headers.get('X-CSRF-Token')
                
                if not (self.set_token and self.csrf_token):
                    print("❌ Tokens não encontrados nos headers")
                    return False
                
                # Calcular expiracao
                expiracao_timestamp = response_auth.headers.get('x-csrf-expiration') or response_auth.headers.get('X-CSRF-Expiration')
                if expiracao_timestamp:
                    try:
                        # Converter de milissegundos para datetime UTC
                        timestamp_ms = int(expiracao_timestamp)
                        self.expiracao = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).replace(tzinfo=None)
                        
                        # Calcular tempo restante até expiração
                        tempo_restante = (self.expiracao - datetime.utcnow()).total_seconds() / 60
                        
                        print(f"✅ Token obtido! Válido por {tempo_restante:.1f} min")
                        
                    except (ValueError, TypeError) as e:
                        print(f"⚠️ Erro ao processar timestamp de expiração '{expiracao_timestamp}': {e}")
                        self.expiracao = datetime.utcnow() + timedelta(minutes=60)
                        print(f"✅ Usando expiração padrão 60min")
                else:
                    # Fallback: 60 minutos (padrão do Siscomex)
                    self.expiracao = datetime.utcnow() + timedelta(minutes=60)
                    print(f"✅ Token sem timestamp - usando padrão 60min")
                
                # Atualizar timestamp da última autenticação (regra Siscomex: intervalo mínimo de 60s)
                self.ultima_autenticacao = datetime.utcnow()
                
                # Salvar token no cache após autenticação bem-sucedida
                self._salvar_token_cache()
                
                return True
                
            except requests.exceptions.Timeout:
                print("❌ Timeout na autenticação - API pode estar lenta")
                return False
            except requests.exceptions.ConnectionError:
                print("❌ Erro de conexão com a API")
                return False
            except requests.exceptions.HTTPError as e:
                print(f"❌ Erro HTTP na autenticação: {e}")
                if hasattr(e, 'response') and e.response is not None:
                    print(f"   Status Code: {e.response.status_code}")
                    print(f"   Response: {e.response.text[:200]}")
                return False
            except Exception as e:
                print(f"❌ Erro inesperado na autenticação: {e}")
                return False
    
    def _salvar_token_cache(self):
        """Salva token atual em cache persistente"""
        if self.set_token and self.csrf_token and self.expiracao:
            try:
                cache_data = {
                    'set_token': self.set_token,
                    'csrf_token': self.csrf_token,
                    'expiracao': self.expiracao.isoformat(),
                    'cached_at': datetime.utcnow().isoformat(),
                    'ultima_autenticacao': self.ultima_autenticacao.isoformat() if self.ultima_autenticacao else None
                }
                with open(TOKEN_CACHE_FILE, 'wb') as f:
                    pickle.dump(cache_data, f)
                print(f"💾 Token salvo em cache: {TOKEN_CACHE_FILE}")
            except Exception as e:
                print(f"⚠️  Erro ao salvar cache do token: {e}")
    
    def _carregar_token_cache(self):
        """Carrega token do cache se válido"""
        try:
            if os.path.exists(TOKEN_CACHE_FILE):
                with open(TOKEN_CACHE_FILE, 'rb') as f:
                    cache_data = pickle.load(f)
                
                # Verificar se cache não está muito antigo (máximo 90 minutos = 60min + margem)
                cached_at = datetime.fromisoformat(cache_data['cached_at'])
                if (datetime.utcnow() - cached_at).total_seconds() > 5400:  # 90 minutos
                    print("🗑️  Cache do token muito antigo (>90min) - ignorando")
                    os.remove(TOKEN_CACHE_FILE)
                    return
                
                # Restaurar dados do token
                self.set_token = cache_data['set_token']
                self.csrf_token = cache_data['csrf_token']
                self.expiracao = datetime.fromisoformat(cache_data['expiracao'])
                
                # Restaurar timestamp da última autenticação (se existir no cache)
                if 'ultima_autenticacao' in cache_data and cache_data['ultima_autenticacao']:
                    try:
                        self.ultima_autenticacao = datetime.fromisoformat(cache_data['ultima_autenticacao'])
                    except (ValueError, TypeError):
                        self.ultima_autenticacao = None
                
                if self.token_valido():
                    tempo_restante = (self.expiracao - datetime.utcnow()).total_seconds() / 60
                    print(f"🔄 Token carregado do cache! Válido por mais {tempo_restante:.1f} minutos")
                else:
                    print("🗑️  Token do cache expirado - removendo")
                    os.remove(TOKEN_CACHE_FILE)
                    self.set_token = None
                    self.csrf_token = None
                    self.expiracao = None
                    self.ultima_autenticacao = None
            else:
                print("📝 Nenhum cache de token encontrado")
        except Exception as e:
            print(f"⚠️  Erro ao carregar cache do token: {e}")
            # Limpar dados inválidos
            if os.path.exists(TOKEN_CACHE_FILE):
                os.remove(TOKEN_CACHE_FILE)
    
    def status_token(self):
        """Retorna status atual do token para debugging"""
        if not (self.set_token and self.csrf_token and self.expiracao):
            return "Token não inicializado"
        
        agora = datetime.utcnow()
        tempo_real_restante = (self.expiracao - agora).total_seconds() / 60
        
        if tempo_real_restante <= 0:
            return f"Token EXPIRADO há {abs(tempo_real_restante):.1f} minutos"
        elif self.token_valido():
            return f"Token VÁLIDO por mais {tempo_real_restante:.1f} minutos"
        else:
            return f"Token em MARGEM DE SEGURANÇA ({tempo_real_restante:.1f} min restantes)"

# Instancia global compartilhada
token_manager = SharedTokenManager()