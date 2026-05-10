# config.py
import os
from dotenv import load_dotenv
from binance.client import Client

load_dotenv()

API_KEY = os.getenv("KEY_BINANCE")
SECRET_KEY = os.getenv("SECRET_BINANCE")

SYMBOL = "SOLUSDT"
ASSET = "SOL"
QUOTE_ASSET = "USDT"
INTERVAL = "15m"

def get_banca_inicial():
    try:
        client = Client(API_KEY, SECRET_KEY)
        account = client.get_account()
        total_usdt = 0.0
        for balance in account["balances"]:
            if balance["asset"] == "USDT":
                total_usdt = float(balance["free"])
                break
        return total_usdt if total_usdt > 0 else 10.0
    except Exception as e:
        print(f"Erro ao buscar saldo automático: {e}")
        return 10.0

BANCA_INICIAL = get_banca_inicial()

# Stop Loss e Take Profit por operação
STOP_LOSS_PERCENT   = 1.0   # 0.3% abaixo do preço de entrada
TAKE_PROFIT_PERCENT = 1.5   # 0.5% acima do preço de entrada

META_DIARIA_PERCENT      = 0.5
TAKE_PROFIT_META_PERCENT = 1.0
NOTIONAL_BUFFER          = 2.0

# RSI
RSI_PERIOD         = 5
RSI_BUY_THRESHOLD  = 25   # compra abaixo de 55 (moderado)
RSI_SELL_THRESHOLD = 80   # venda acima de 70

# MACD
MACD_FAST   = 5  #12
MACD_SLOW   = 13  #26
MACD_SIGNAL = 4   #9

LOG_FILE     = "trading_logs_trader.txt"
SIGNALS_FILE = "signals.json"