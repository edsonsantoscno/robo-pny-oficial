import os
import sys
from dotenv import load_dotenv
from binance.client import Client

# Suporte ao PyInstaller (Garante que o robô ache o .env se virar um .exe)
if getattr(sys, 'frozen', False):
    base_path = os.path.dirname(sys.executable)
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

# Carrega o .env específico do cliente (Deve estar na mesma pasta ou na raiz)
load_dotenv(os.path.join(base_path, ".env_cliente"))

API_KEY_CLIENTE = os.getenv("KEY_BINANCE_CLIENTE")
SECRET_KEY_CLIENTE = os.getenv("SECRET_BINANCE_CLIENTE")

# --- CONEXÃO SUPABASE (VPS Hostinger) ---
SUPABASE_URL = "https://base.mandacarurn.com.br"
# CORREÇÃO: Adicionado 'e' no início da chave JWT
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.ewogICJyb2xlIjogInNlcnZpY2Vfcm9sZSIsCiAgImlzcyI6ICJzdXBhYmFzZSIsCiAgImlhdCI6IDE3MTUwNTA4MDAsCiAgImV4cCI6IDE4NzI4MTcyMDAKfQ.QyAbsAIda4o4-BINI9l9i2wvJ0r9gjP4vlvZlRiggFk" 

# Configurações de Identidade
CLIENTE_NOME = "Cliente 1"
QUOTE_ASSET = "USDT"

# Arquivos de Registro
SIGNALS_FILE = os.path.join(base_path, "signals.json")
LOG_FILE = os.path.join(base_path, "trading_logs_cliente.txt")

def get_banca_inicial():
    """Busca o saldo USDT atual na Binance do Cliente"""
    if not API_KEY_CLIENTE or not SECRET_KEY_CLIENTE:
        print("⚠️ Chaves da Binance não encontradas no .env_cliente")
        return 10.0
        
    try:
        client = Client(API_KEY_CLIENTE, SECRET_KEY_CLIENTE)
        balance = client.get_asset_balance(asset='USDT')
        if balance:
            total_usdt = float(balance["free"])
            return total_usdt if total_usdt > 0 else 10.0
        return 10.0
    except Exception as e:
        print(f"❌ Erro ao capturar banca inicial: {e}")
        return 10.0

# Define a banca no momento da inicialização
BANCA_INICIAL = get_banca_inicial()

# --- PARÂMETROS DE CÓPIA ---
# 1.0 = 100% do saldo livre por operação
QUANTIDADE_PERCENTUAL = 1.0 

# Metas e Travas
META_DIARIA_PERCENT = 2.0
TAKE_PROFIT_META_PERCENT = 10.0 
COPY_TRADER_ATIVO = True
