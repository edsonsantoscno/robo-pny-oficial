import os
import time
from dotenv import load_dotenv
from binance.client import Client

load_dotenv()

API_KEY = os.getenv("KEY_BINANCE")
SECRET_KEY = os.getenv("SECRET_BINANCE")

# Credenciais Supabase (Hostinger)
SUPABASE_URL = "https://base.mandacarurn.com.br" 
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.ewogICJyb2xlIjogInNlcnZpY2Vfcm9sZSIsCiAgImlzcyI6ICJzdXBhYmFzZSIsCiAgImlhdCI6IDE3MTUwNTA4MDAsCiAgImV4cCI6IDE4NzI4MTcyMDAKfQ.QyAbsAIda4o4-BINI9l9i2wvJ0r9gjP4vlvZlRiggFk"

# --- SELETOR DE ESTRATÉGIA ---
MODO_ESTRATEGIA = "PNY" 

# --- AJUSTE PARA SCANNER ---
SYMBOLS = ["SOLUSDT", "BTCUSDT", "ONDOUSDT", "RENDERUSDT", 
           "TAOUSDT", "LINKUSDT", "STXUSDT", "ARUSDT", "PENDLEUSDT"]
INTERVAL = "15m"

# --- CONFIGURAÇÃO TÉCNICA BINANCE ---
RECV_WINDOW = 10000

def get_banca_inicial():
    try:
        # Inicializa o cliente básico
        client = Client(API_KEY, SECRET_KEY)
        
        # Sincroniza o tempo local com o servidor da Binance (Corrige erro -1021)
        server_time = client.get_server_time()
        client.timestamp_offset = server_time['serverTime'] - int(time.time() * 1000)
        
        # O saldo é obtido passando a recvWindow diretamente na chamada
        account = client.get_account(recvWindow=RECV_WINDOW)
        total_usdt = 0.0
        for balance in account["balances"]:
            if balance["asset"] == "USDT":
                total_usdt = float(balance["free"])
                break
        return total_usdt if total_usdt > 0 else 10.0
    except Exception as e:
        print(f"⚠️ Erro ao obter saldo/sincronizar: {e}")
        return 10.0

BANCA_INICIAL = get_banca_inicial()

# --- GESTÃO DE RISCO ---
STOP_LOSS_PERCENT   = 4.0   
TAKE_PROFIT_PERCENT = 2.0   
META_DIARIA_PERCENT = 2.00 
TAKE_PROFIT_META_PERCENT = 2.0 
NOTIONAL_BUFFER     = 2.0

# --- PARÂMETROS DAS ESTRATÉGIAS ---

# 1. Setup ORIGINAL (RSI + MACD)
RSI_PERIOD, RSI_BUY_THRESHOLD, RSI_SELL_THRESHOLD = 5, 25, 80
MACD_FAST, MACD_SLOW, MACD_SIGNAL = 8, 21, 5

# 2. Setup EMA_ONLY (Estrutura Tripla Moderada)
EMA_ONLY_FAST    = 20   
EMA_ONLY_SLOW    = 50   
EMA_ONLY_PERIOD  = 100  

# 3. Setup EMA_SCALPER (Agressivo)
EMA_SCALPER_FAST = 9
EMA_SCALPER_SLOW = 21

# --- 4. SETUP PNY (Príncipe de NY) ---
PNY_BB_PERIOD = 20
PNY_BB_STD = 2.0
PNY_STOCH_K = 10
PNY_STOCH_D = 3
PNY_STOCH_THRESHOLD_LOW = 25  
PNY_STOCH_THRESHOLD_HIGH = 75 

# --- 5. SETUP TOPO/FUNDO (RSI_EMA) ---
RSI_TOP_BOTTOM_PERIOD = 14
RSI_LEVEL_LOW = 35  
RSI_LEVEL_HIGH = 65 

LOG_FILE = "trading_logs.txt"
SIGNALS_FILE = "signals.json"
