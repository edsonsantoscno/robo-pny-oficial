import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
ROBO_TRADER_DIR = BASE_DIR / "robo_trader"
ROBO_CLIENTE_DIR = BASE_DIR / "robo_cliente"
STATE_DIR = BASE_DIR / "state"
LOGS_DIR = BASE_DIR / "logs"

STATE_FILE_MESTRE = STATE_DIR / "trading_state.json"
STATE_FILE_CLIENTE = STATE_DIR / "trading_state_cliente.json"
LATEST_SIGNAL_FILE = STATE_DIR / "latest_signal.json"

LOG_FILE_MESTRE = LOGS_DIR / "trading_logs.txt"
LOG_FILE_CLIENTE = LOGS_DIR / "trading_logs_cliente.txt"

SECRET_KEY = os.getenv("SECRET_KEY", "sua_chave_secreta_aqui_2026")
DEBUG = True
HOST = "0.0.0.0"
PORT = 5000

API_TIMEOUT = 30
MAX_RETRIES = 3

BINANCE_SYMBOLS = [
    "SOLUSDT", "BTCUSDT", "ONDOUSDT", "RENDERUSDT",
    "TAOUSDT", "LINKUSDT", "STXUSDT", "ARUSDT", "PENDLEUSDT"
]
BINANCE_INTERVAL = "15m"

STOP_LOSS_DEFAULT = 4.0
TAKE_PROFIT_DEFAULT = 2.0
META_DIARIA_PERCENT = 2.0
QUANTIDADE_PERCENTUAL_DEFAULT = 100

STRATEGIES = ["EMA_ONLY", "EMA_SCALPER", "RSI", "PNY", "ALL"]
STRATEGY_DEFAULT = "PNY"
