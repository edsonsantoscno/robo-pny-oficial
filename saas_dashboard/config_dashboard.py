# saas_dashboard/config_dashboard.py
import os
from pathlib import Path

# Caminho base
BASE_DIR = Path(__file__).parent.parent
ROBO_TRADER_DIR = BASE_DIR / "robo_trader"
ROBO_CLIENTE_DIR = BASE_DIR / "robo_cliente"

# Arquivos de estado
STATE_FILE = ROBO_TRADER_DIR / "trading_state.json"
SIGNALS_FILE = ROBO_CLIENTE_DIR / "signals.json"
LOGS_FILE = ROBO_TRADER_DIR / "trading_logs.txt"

# Configurações Flask
SECRET_KEY = "sua_chave_secreta_aqui_2026"
DEBUG = True
HOST = "0.0.0.0"
PORT = 5000

# Configurações de API
API_TIMEOUT = 30
MAX_RETRIES = 3

# Configurações de Binance
BINANCE_SYMBOLS = ["SOLUSDT", "BTCUSDT", "ETHUSDT", "RENDERUSDT", "PENDLEUSDT"]
BINANCE_INTERVAL = "15m"

# Configurações de Risco
STOP_LOSS_DEFAULT = 4.0
TAKE_PROFIT_DEFAULT = 2.0
META_DIARIA_PERCENT = 2.0
QUANTIDADE_PERCENTUAL_DEFAULT = 100

# Estratégias disponíveis
STRATEGIES = ["EMA_ONLY", "EMA_SCALP", "RSI", "PNY", "ALL"]
STRATEGY_DEFAULT = "PNY"