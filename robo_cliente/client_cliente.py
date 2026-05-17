import os
import time
from binance.client import Client
from binance.enums import ORDER_TYPE_MARKET

class BinanceClient:
    def __init__(self):
        # Leitura nativa e direta das variáveis de ambiente criptografadas da Stack do Portainer
        self.api_key = os.getenv("KEY_BINANCE_CLIENTE")
        self.secret_key = os.getenv("SECRET_BINANCE_CLIENTE")
        self.recv_window = int(os.getenv("RECV_WINDOW", 10000))

        if not self.api_key or not self.secret_key:
            print("⚠️ AVISO OPERACIONAL: Chaves da Binance do Cliente não encontradas na memória da Stack.")

        # Inicializa o cliente oficial da Binance isolado com tempo limite de resposta de rede
        self.client = Client(
            self.api_key,
            self.secret_key,
            requests_params={"timeout": 30}
        )
        
        # Sincroniza o relógio interno imediatamente na inicialização (Evita erro -1021)
        self._sync_time()
        self.max_tentativas = 3
        self.espera_entre_tentativas = 10

    def _sync_time(self):
        """Sincroniza o offset de tempo com o servidor oficial da Binance"""
        try:
            server_time = self.client.get_server_time()
            self.client.timestamp_offset = server_time['serverTime'] - int(time.time() * 1000)
            print(f"⏰ Relógio do Cliente sincronizado com a Binance. Offset atual: {self.client.timestamp_offset}ms")
        except Exception as e:
            print(f"⚠️ Falha ao sincronizar tempo com os servidores da API da Binance: {e}")

    def _retry(self, func):
        """Motor de redundância: repete a operação em caso de oscilações de rede ou timeout."""
        for tentativa in range(1, self.max_tentativas + 1):
            try:
                return func()
            except Exception as e:
                # Se o erro for estritamente de dessincronização de relógio VPS, força o re-sync imediato
                if "code=-1021" in str(e):
                    self._sync_time()
                
                if tentativa < self.max_tentativas:
                    print(f"⚠️ Tentativa {tentativa}/{self.max_tentativas} falhou na rede do cliente: {e}")
                    print(f"⏳ Aguardando {self.espera_entre_tentativas}s antes de retransmitir requisição...")
                    time.sleep(self.espera_entre_tentativas)
                else:
                    print(f"❌ Todas as {self.max_tentativas} tentativas de comunicação da subconta falharam: {e}")
                    raise e

    def get_account_balance(self):
        """Busca os dados completos da conta do cliente na Binance passando o recvWindow diretamente"""
        return self._retry(lambda: self.client.get_account(recvWindow=self.recv_window))

    def get_asset_balance(self, asset):
        """Filtra e retorna o saldo livre real em carteira de um ativo específico (ex: 'USDT')"""
        try:
            account = self.get_account_balance()
            if account:
                for balance in account.get("balances", []):
                    if balance["asset"] == asset:
                        return float(balance["free"])
            return 0.0
        except Exception as e:
            print(f"Erro ao filtrar saldo em carteira para o ativo do cliente {asset}: {e}")
            return 0.0

    def get_klines(self, symbol, interval, limit=100):
        """Puxa o histórico de velas (candles) para o motor do pandas-ta analisar se necessário"""
        return self._retry(lambda:
            self.client.get_klines(symbol=symbol, interval=interval, limit=limit)
        )

    def get_symbol_info(self, symbol):
        """Busca os dados regulatórios e filtros de lote (LOT_SIZE) de uma moeda na exchange"""
        return self._retry(lambda:
            self.client.get_symbol_info(symbol)
        )

    def get_current_price(self, symbol):
        """Retorna o preço mais recente de mercado (Ticker) convertido de forma segura para float"""
        return self._retry(lambda:
            float(self.client.get_symbol_ticker(symbol=symbol)["price"])
        )

    def create_order(self, symbol, side, quantity):
        """Envia uma ordem a mercado (MARKET) de compra ou venda clonada com proteção de recvWindow"""
        return self._retry(lambda:
            self.client.create_order(
                symbol=symbol,
                side=side,
                type=ORDER_TYPE_MARKET,
                quantity=quantity,
                recvWindow=self.recv_window
            )
        )

    def get_notional_minimum(self, symbol):
        """Busca o valor mínimo em dólares (Notional) exigido pela Binance para o par operado"""
        try:
            symbol_info = self.get_symbol_info(symbol)
            if symbol_info:
                for f in symbol_info.get("filters", []):
                    if f["filterType"] == "NOTIONAL":
                        return float(f["minNotional"])
            return 10.0
        except Exception as e:
            print(f"Erro ao rastrear notional mínimo regulatório da subconta: {e}")
            return 10.0
