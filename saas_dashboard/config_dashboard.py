import os
from pathlib import Path

# ============ CONFIGURAÇÕES DE DIRETÓRIOS E ARQUIVOS ============
BASE_DIR = Path(__file__).parent.parent
# Caminhos ajustados para os novos volumes mapeados
ROBO_TRADER_DIR = BASE_DIR / "data" / "robo_trader" # <-- CORREÇÃO AQUI
ROBO_CLIENTE_DIR = BASE_DIR / "data" / "robo_cliente" # <-- CORREÇÃO AQUI

# Arquivos de estado unificados para leitura e escrita no Docker
STATE_FILE_MESTRE = ROBO_TRADER_DIR / "trading_state.json" # <-- NOVO
STATE_FILE_CLIENTE = ROBO_CLIENTE_DIR / "trading_state_cliente.json" # <-- NOVO
SIGNALS_FILE = ROBO_TRADER_DIR / "latest_signal.json" # <-- CORREÇÃO AQUI: Aponta para o latest_signal.json do mestre
LOG_FILE_MESTRE = BASE_DIR / "data" / "logs" / "trading_logs.txt" # <-- NOVO
LOG_FILE_CLIENTE = BASE_DIR / "data" / "logs" / "trading_logs_cliente.txt" # <-- NOVO

# ============ CONFIGURAÇÕES DO SERVIDOR FLASK ============
SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "sua_chave_secreta_aqui_2026") # <-- CORREÇÃO AQUI: Ler de env
DEBUG = os.getenv("FLASK_DEBUG", "True").lower() in ('true', '1', 't') # <-- CORREÇÃO AQUI: Ler de env
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
