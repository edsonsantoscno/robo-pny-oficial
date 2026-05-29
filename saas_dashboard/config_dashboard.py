import os
from pathlib import Path

# ============ CONFIGURAÇÕES DE CAMINHOS UNIFICADOS ============
BASE_DIR = Path(__file__).parent.parent

# Diretórios principais do ecossistema
ROBO_TRADER_DIR = BASE_DIR / "robo_trader"
ROBO_CLIENTE_DIR = BASE_DIR / "robo_cliente"

# ATENÇÃO: Centralizando os caminhos nas pastas corretas para evitar desencontro de dados entre Robôs e Painel
STATE_FILE_MESTRE = ROBO_TRADER_DIR / "trading_state.json"
STATE_FILE_CLIENTE = ROBO_CLIENTE_DIR / "trading_state_cliente.json"
LATEST_SIGNAL_FILE = ROBO_CLIENTE_DIR / "signals.json"  # Sincronizado com signals do cliente

LOG_FILE_MESTRE = ROBO_TRADER_DIR / "trading_logs.txt"
LOG_FILE_CLIENTE = ROBO_CLIENTE_DIR / "trading_logs_cliente.txt"

# ============ SEGURANÇA E PRODUÇÃO (VPS HOSTINGER) ============
SECRET_KEY = os.getenv("SECRET_KEY", "prod_strong_key_pny_2026_secure_hash")
DEBUG = os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1", "t")
HOST = "0.0.0.0"
PORT = int(os.getenv("FLASK_PORT", 5000))

# ============ CONFIGURAÇÕES DA API DA BINANCE ============
API_TIMEOUT = 30
MAX_RETRIES = 3

# Pares de moedas monitorados pelo Robô Master
BINANCE_SYMBOLS = [
    "SOLUSDT", "BTCUSDT", "ONDOUSDT", "RENDERUSDT",
    "TAOUSDT", "LINKUSDT", "STXUSDT", "ARUSDT", "PENDLEUSDT"
]
BINANCE_INTERVAL = "15m"

# ============ GERENCIAMENTO DE RISCO PADRÃO (FALLBACKS) ============
STOP_LOSS_DEFAULT = 4.0
TAKE_PROFIT_DEFAULT = 2.0
META_DIARIA_PERCENT = 2.0
QUANTIDADE_PERCENTUAL_DEFAULT = 100

# ============ CONFIGURAÇÕES DE ESTRATÉGIAS ============
STRATEGIES = ["EMA_ONLY", "EMA_SCALPER", "RSI", "PNY", "ALL"]
STRATEGY_DEFAULT = "PNY"
