import os
from pathlib import Path

# ============ CONFIGURAÇÕES DE DIRETÓRIOS E ARQUIVOS NO DOCKER ============
# Força o caminho absoluto na raiz do container compartilhado
BASE_DIR = Path(__file__).parent.parent
# LOG_FILE agora aponta para o volume centralizado de logs
LOG_FILE = BASE_DIR / "logs" / "trading_logs_cliente.txt" # <-- CORREÇÃO AQUI
# SIGNALS_FILE não é mais usado pelo cliente para receber sinais, mas mantido para consistência se necessário
SIGNALS_FILE = BASE_DIR / "robo_cliente" / "data" / "signals.json" # <-- CORREÇÃO AQUI

# ============ SEGURANÇA: VARIÁVEIS DE AMBIENTE DA VPS/PORTAINER ============
# Lê de forma nativa e ultra-segura da memória da Stack injetada pelo painel
API_KEY_CLIENTE = os.getenv("API_KEY") # <-- CORREÇÃO AQUI: Usar API_KEY genérica
SECRET_KEY_CLIENTE = os.getenv("API_SECRET") # <-- CORREÇÃO AQUI: Usar API_SECRET genérica

# Credenciais Supabase lidas da nuvem de forma dinâmica e protegida
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://base.mandacarurn.com.br")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# ============ CONFIGURAÇÕES DE IDENTIDADE DO SAAS ============
CLIENTE_NOME = os.getenv("CLIENTE_NOME", "Cliente Oficial 1")
QUOTE_ASSET = "USDT"

# ============ PARÂMETROS OPERACIONAIS DE CÓPIA PROPORCIONAL ============
# 1.0 = 100% do saldo livre da banca por operação (Ajustável online via Dashboard)
QUANTIDADE_PERCENTUAL = 1.0

# ============ METAS E TRAVAS DE RISCO COMERCIAL ============
META_DIARIA_PERCENT = 2.0       # Meta de ganho diário (Alinhado com o mestre)
TAKE_PROFIT_META_PERCENT = 10.0 # Alvo por operação (10% da meta diária em USDT)
COPY_TRADER_ATIVO = True

# BANCA PADRÃO DE REFERÊNCIA OPERACIONAL
# Removemos a função get_banca_inicial() deste arquivo para evitar travamentos de rede (Rate Limits).
# O robô do cliente (main_copy_trader.py) agora captura e atualiza o saldo real da corretora no loop.
BANCA_INICIAL = 199.44

# ============ CONFIGURAÇÕES DE WEBSOCKET ============
WEBSOCKET_HOST = os.getenv("WEBSOCKET_HOST", "localhost") # Default para localhost, mas será sobrescrito pelo Docker Compose
WEBSOCKET_PORT = int(os.getenv("WEBSOCKET_PORT", 8765))
