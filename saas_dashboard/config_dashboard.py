import os
from pathlib import Path

# ============ CONFIGURAÇÕES DE CAMINHOS UNIFICADOS ============
BASE_DIR = Path(__file__).parent.parent

# Diretórios principais do ecossistema
ROBO_TRADER_DIR = BASE_DIR / "robo_trader"
ROBO_CLIENTE_DIR = BASE_DIR / "robo_cliente"

# Centralização dos caminhos físicos de comunicação interna
STATE_FILE_MESTRE = ROBO_TRADER_DIR / "trading_state.json"
STATE_FILE_CLIENTE = ROBO_CLIENTE_DIR / "trading_state_cliente.json"
LATEST_SIGNAL_FILE = ROBO_CLIENTE_DIR / "signals.json"
LOG_FILE_MESTRE = ROBO_TRADER_DIR / "trading_logs.txt"
LOG_FILE_CLIENTE = ROBO_CLIENTE_DIR / "trading_logs_cliente.txt"
# ============ SEGURANÇA E PRODUÇÃO (VPS HOSTINGER) ============
# Fallback dinâmico e seguro: se não houver variável no .env, gera um hash seguro aleatório
SECRET_KEY = os.environ.get("FLASK_SECRET_KEY") or os.environ.get("SECRET_KEY") or os.urandom(24).hex()
DEBUG = os.environ.get("FLASK_DEBUG", "False").lower() in ("true", "1", "t")
HOST = "0.0.0.0"
PORT = int(os.environ.get("FLASK_PORT", 5000))

# Parâmetros de conexão com a API da Binance
API_TIMEOUT = 30
MAX_RETRIES = 3
# ============ CONFIGURAÇÕES DA API DA BINANCE ============
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

# ============ CONFIGURAÇÕES DE ESTRATÉGIAS SINCRONIZADAS ============
# Corrigido para bater exatamente com as validações de rota do app.py
STRATEGIES = ["EMA_ONLY", "EMA_SCALP", "RSI", "PNY"]
STRATEGY_DEFAULT = "PNY"
