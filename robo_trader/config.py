import os
from pathlib import Path

# ============ CONFIGURAÇÕES DE DIRETÓRIOS E ARQUIVOS ============
BASE_DIR = Path(__file__).parent
LOG_FILE = BASE_DIR / "trading_logs.txt"
SIGNALS_FILE = BASE_DIR / "signals.json"

# ============ CONFIGURAÇÕES DO SERVIDOR WEBSOCKET ============
WEBSOCKET_HOST = "0.0.0.0"
WEBSOCKET_PORT = 8765  # Certifique-se de que é a mesma porta mapeada no docker-compose

# ============ SEGURANÇA: VARIÁVEIS DE AMBIENTE DA VPS/PORTAINER ============
# Remove o load_dotenv() e lê de forma nativa e ultra-segura da memória da Stack
API_KEY = os.getenv("KEY_BINANCE")
SECRET_KEY = os.getenv("SECRET_BINANCE")

# Credenciais Supabase lidas da nuvem de forma dinâmica (Com fallback seguro)
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://base.mandacarurn.com.br")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.ewogICJyb2xlIjogInNlcnZpY2Vfcm9sZSIsCiAgImlzcyI6ICJzdXBhYmFzZSIsCiAgImlhdCI6IDE3MTUwNTA4MDAsCiAgImV4cCI6IDE4NzI4MTcyMDAKfQ.QyAbsAIda4o4-BINI9l9i2wvJ0r9gjP4vlvZlRiggFk")

# ============ SELETOR DE ESTRATÉGIA E ATIVOS ============
MODO_ESTRATEGIA = "PNY" 
INTERVAL = "15m"

# Scanner otimizado com ativos de alta liquidez e volatilidade para o Príncipe de NY
SYMBOLS = [
    "SOLUSDT", "BTCUSDT", "ONDOUSDT", "RENDERUSDT", 
    "TAOUSDT", "LINKUSDT", "STXUSDT", "ARUSDT", "PENDLEUSDT"
]

# ============ CONFIGURAÇÃO TÉCNICA BINANCE ============
RECV_WINDOW = 10000

# BANCA PADRÃO DE REFERÊNCIA OPERACIONAL
# Removemos a função get_banca_inicial() deste arquivo para evitar travamentos de rede (Rate Limits).
# O robô mestre (main_trader.py) agora lê e atualiza o saldo real dinamicamente no loop.
BANCA_INICIAL = 199.44 

# ============ GESTÃO DE RISCO COMERCIAL ============
STOP_LOSS_PERCENT   = 4.0   # Limite de perda máxima por operação
TAKE_PROFIT_PERCENT = 2.0   # Alvo de ganho gráfico por operação
META_DIARIA_PERCENT = 2.00  # Meta de crescimento diário da banca (ex: 2%)
TAKE_PROFIT_META_PERCENT = 2.0 
NOTIONAL_BUFFER     = 2.0

# ============ PARÂMETROS AVANÇADOS DAS ESTRATÉGIAS (MOTORES PANDAS-TA) ============

# 1. Setup ORIGINAL (RSI + MACD)
RSI_PERIOD, RSI_BUY_THRESHOLD, RSI_SELL_THRESHOLD = 5, 25, 80
MACD_FAST, MACD_SLOW, MACD_SIGNAL = 8, 21, 5

# 2. Setup EMA_ONLY (Cruzamento Triplo de Tendência)
EMA_ONLY_FAST    = 20   
EMA_ONLY_SLOW    = 50   
EMA_ONLY_PERIOD  = 100  

# 3. Setup EMA_SCALPER (Cruzamento Rápido de Médias)
EMA_SCALPER_FAST = 9
EMA_SCALPER_SLOW = 21

# 4. SETUP PRÍNCIPE DE NY (PNY - Cruzamento de Volatilidade e Exaustão)
PNY_BB_PERIOD = 20
PNY_BB_STD = 2.0
PNY_STOCH_K = 10
PNY_STOCH_D = 3
PNY_STOCH_THRESHOLD_LOW = 25  
PNY_STOCH_THRESHOLD_HIGH = 75 

# 5. SETUP ADICIONAL DE REVERSÃO: TOPO/FUNDO (RSI_EMA)
RSI_TOP_BOTTOM_PERIOD = 14
RSI_LEVEL_LOW = 35  
RSI_LEVEL_HIGH = 65 
