import os
from pathlib import Path

# ============ CONFIGURAÇÕES DE DIRETÓRIOS E ARQUIVOS ============
BASE_DIR = Path(__file__).parent.parent
ROBO_TRADER_DIR = BASE_DIR / "robo_trader"
ROBO_CLIENTE_DIR = BASE_DIR / "robo_cliente"

# Arquivos de estado unificados para leitura e escrita no Docker
STATE_FILE = ROBO_TRADER_DIR / "trading_state.json"
SIGNALS_FILE = ROBO_CLIENTE_DIR / "signals.json"
LOG_FILE = ROBO_TRADER_DIR / "trading_logs.txt" # Ajustado para bater com a extensão .txt unificada

# ============ CONFIGURAÇÕES DO SERVIDOR FLASK ============
SECRET_KEY = os.getenv("SECRET_KEY", "sua_chave_secreta_aqui_2026")
DEBUG = True
HOST = "0.0.0.0"
PORT = 5000

# ============ CONFIGURAÇÕES DE API DE REDE ============
API_TIMEOUT = 30
MAX_RETRIES = 3

# ============ PARÂMETROS OPERACIONAIS DA BINANCE (SINCRO) ============
# Igualado perfeitamente com a lista de moedas ativa do config.py do robô mestre
BINANCE_SYMBOLS = [
    "SOLUSDT", "BTCUSDT", "ONDOUSDT", "RENDERUSDT", 
    "TAOUSDT", "LINKUSDT", "STXUSDT", "ARUSDT", "PENDLEUSDT"
]
BINANCE_INTERVAL = "15m"

# ============ CONFIGURAÇÕES DE VALORES PADRÃO (FALLBACKS) ============
STOP_LOSS_DEFAULT = 4.0
TAKE_PROFIT_DEFAULT = 2.0
META_DIARIA_PERCENT = 2.0
QUANTIDADE_PERCENTUAL_DEFAULT = 100

# ============ INTELIGÊNCIAS DISPONÍVEIS NO DROPDOWN ============
STRATEGIES = ["EMA_ONLY", "EMA_SCALPER", "RSI", "PNY", "ALL"] # Ajustado para bater com o nome 'EMA_SCALPER' do robô
STRATEGY_DEFAULT = "PNY"
