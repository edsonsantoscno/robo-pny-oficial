import time
from binance.client import Client
from binance.enums import ORDER_TYPE_MARKET
from config import API_KEY, SECRET_KEY, RECV_WINDOW

class BinanceClient:
    def __init__(self):
        # Inicializa o cliente sem o recvWindow no requests_params para evitar erro de Session
        self.client = Client(
            API_KEY,
            SECRET_KEY,
            requests_params={"timeout": 30}
        )
        # Sincroniza o relógio na inicialização
        self._sync_time()
        self.max_tentativas          = 3
        self.espera_entre_tentativas = 10

    def _sync_time(self):
        """Sincroniza o offset de tempo com o servidor da Binance"""
        try:
            server_time = self.client.get_server_time()
            self.client.timestamp_offset = server_time['serverTime'] - int(time.time() * 1000)
            print(f"⏰ Relógio sincronizado com a Binance. Offset: {self.client.timestamp_offset}ms")
        except Exception as e:
            print(f"⚠️ Falha ao sincronizar tempo: {e}")

    def _retry(self, func):
        for tentativa in range(1, self.max_tentativas + 1):
            try:
                return func()
            except Exception as e:
                # Se o erro for de sincronização de tempo, tenta re-sincronizar
                if "code=-1021" in str(e):
                    self._sync_time()
                
                if tentativa < self.max_tentativas:
                    print(f"⚠️  Tentativa {tentativa}/{self.max_tentativas} falhou: {e}")
                    print(f"⏳ Aguardando {self.espera_entre_tentativas}s antes de tentar novamente...")
                    time.sleep(self.espera_entre_tentativas)
                else:
                    print(f"❌ Todas as {self.max_tentativas} tentativas falharam: {e}")
                    raise e

    def get_account_balance(self):
        # Passa recvWindow diretamente na chamada
        return self._retry(lambda: self.client.get_account(recvWindow=RECV_WINDOW))

    def get_asset_balance(self, asset):
        try:
            account = self.get_account_balance()
            if account:
                for balance in account["balances"]:
                    if balance["asset"] == asset:
                        return float(balance["free"])
            return 0.0
        except Exception as e:
            print(f"Erro ao buscar saldo do ativo {asset}: {e}")
            return 0.0

    def get_klines(self, symbol, interval, limit=100):
        return self._retry(lambda:
            self.client.get_klines(symbol=symbol, interval=interval, limit=limit)
        )

    def get_symbol_info(self, symbol):
        return self._retry(lambda:
            self.client.get_symbol_info(symbol)
        )

    def get_current_price(self, symbol):
        return self._retry(lambda:
            float(self.client.get_symbol_ticker(symbol=symbol)["price"])
        )

    def create_order(self, symbol, side, quantity):
        # Passa recvWindow diretamente na criação da ordem
        return self._retry(lambda:
            self.client.create_order(
                symbol=symbol,
                side=side,
                type=ORDER_TYPE_MARKET,
                quantity=quantity,
                recvWindow=RECV_WINDOW
            )
        )

    def get_notional_minimum(self, symbol):
        try:
            symbol_info = self.get_symbol_info(symbol)
            if symbol_info:
                for f in symbol_info["filters"]:
                    if f["filterType"] == "NOTIONAL":
                        return float(f["minNotional"])
            return 10.0
        except Exception as e:
            print(f"Erro ao buscar notional mínimo: {e}")
            return 10.0
