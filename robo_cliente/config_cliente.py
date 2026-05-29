import os
from pathlib import Path

# ============ CONFIGURAÇÕES DE DIRETÓRIOS E ARQUIVOS NO DOCKER ============
# Força o caminho absoluto na raiz do container compartilhado (/app)
BASE_DIR = Path("/app")

# Arquivos de comunicação compartilhados via volumes do Docker Compose
LOG_FILE = BASE_DIR / "trading_logs_cliente.txt"
SIGNALS_FILE = BASE_DIR / "signals.json"

# ============ SEGURANÇA: VARIÁVEIS DE AMBIENTE DA VPS/PORTAINER ============
# Lê de forma nativa e ultra-segura da memória da Stack injetada pelo painel multitenant
API_KEY_CLIENTE = os.getenv("KEY_BINANCE") or os.getenv("API_KEY")
SECRET_KEY_CLIENTE = os.getenv("SECRET_BINANCE") or os.getenv("API_SECRET")

# CORREÇÃO TOTAL E DEFINITIVA: Apontando estritamente para o subdomínio correto do seu Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://supabase.mandacarurn.com.br")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# ============ CONFIGURAÇÕES DE IDENTIDADE DO SAAS ============
CLIENTE_NOME = os.getenv("CLIENTE_NOME", "Cliente Oficial 1")
QUOTE_ASSET = "USDT"

# ============ PARÂMETROS OPERACIONAIS DE CÓPIA PROPORCIONAL ============
# 1.0 = 100% do saldo livre da banca por operação (Ajustável online via Dashboard)
QUANTIDADE_PERCENTUAL = 1.0

# ============ METAS E TRAVAS DE RISCO COMERCIAL ============
META_DIARIA_PERCENT = 2.0        # Meta de ganho diário (Alinhado com o mestre)
TAKE_PROFIT_META_PERCENT = 10.0  # Alvo por operação (10% da meta diária em USDT)
COPY_TRADER_ATIVO = True

# BANCA PADRÃO DE REFERÊNCIA OPERACIONAL
BANCA_INICIAL = 199.44

# ============ CONFIGURAÇÕES DE WEBSOCKET FIXADAS COM ERRO ZERO ============
# Alinhado com o nome do container e porta global de transmissão do cluster Docker
WEBSOCKET_HOST = os.getenv("WS_HOST") or os.getenv("WEBSOCKET_HOST", "websocket-server")
WEBSOCKET_PORT = int(os.getenv("WS_PORT") or os.getenv("WEBSOCKET_PORT", 6001))
