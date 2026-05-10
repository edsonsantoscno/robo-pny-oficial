# client_cliente.py
import os
import sys
from dotenv import load_dotenv
from binance.client import Client

# Suporte ao PyInstaller: localiza arquivos na pasta do executável
if getattr(sys, 'frozen', False):
    base_path = os.path.dirname(sys.executable)
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

load_dotenv(os.path.join(base_path, ".env_cliente"))

API_KEY_CLIENTE = os.getenv("KEY_BINANCE_CLIENTE")
SECRET_KEY_CLIENTE = os.getenv("SECRET_BINANCE_CLIENTE")

class BinanceClientCliente:
    def __init__(self):
        self.client = Client(API_KEY_CLIENTE, SECRET_KEY_CLIENTE)

    def get_account_balance(self):
        try:
            return self.client.get_account()
        except Exception as e:
            print(f"❌ Erro ao buscar saldo: {e}")
            return None

    def get_asset_balance(self, asset):
        try:
            account = self.get_account_balance()
            if account:
                for balance in account["balances"]:
                    if balance["asset"] == asset:
                        return float(balance["free"])
            return 0.0
        except Exception as e:
            print(f"❌ Erro ao buscar saldo do ativo {asset}: {e}")
            return 0.0

    def get_symbol_info(self, symbol):
        try:
            return self.client.get_symbol_info(symbol)
        except Exception as e:
            print(f"❌ Erro ao buscar info do símbolo: {e}")
            return None

    def get_current_price(self, symbol):
        try:
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            return float(ticker["price"])
        except Exception as e:
            print(f"❌ Erro ao buscar preço: {e}")
            return None

    def create_order(self, symbol, side, quantity):
        try:
            from binance.enums import ORDER_TYPE_MARKET
            order = self.client.create_order(
                symbol=symbol,
                side=side,
                type=ORDER_TYPE_MARKET,
                quantity=quantity
            )
            return order
        except Exception as e:
            print(f"❌ Erro ao criar ordem: {e}")
            return None