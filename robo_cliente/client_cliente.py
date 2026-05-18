import os
import time
from binance.client import Client
from binance.enums import ORDER_TYPE_MARKET
# Importação do logger do cliente
from logger_cliente import TradingLoggerCliente # type: ignore

class BinanceClient:
    def __init__(self, logger: TradingLoggerCliente = None): # <-- CORREÇÃO AQUI: Adicionado logger
        # Leitura nativa e direta das variáveis de ambiente criptografadas da Stack do Portainer
        self.api_key = os.getenv("API_KEY") # <-- CORREÇÃO AQUI: Usar API_KEY genérica
        self.secret_key = os.getenv("API_SECRET") # <-- CORREÇÃO AQUI: Usar API_SECRET genérica
        self.recv_window = int(os.getenv("RECV_WINDOW", 10000))
        self.logger = logger if logger else TradingLoggerCliente() # <-- CORREÇÃO AQUI: Inicializa logger

        if not self.api_key or not self.secret_key:
            self.logger.warning("⚠️ AVISO OPERACIONAL: Chaves da Binance do Cliente não encontradas na memória da Stack.") # <-- CORREÇÃO AQUI

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
            self.logger.info(f"⏰ Relógio do Cliente sincronizado com a Binance. Offset atual: {self.client.timestamp_offset}ms") # <-- CORREÇÃO AQUI
        except Exception as e:
            self.logger.warning(f"⚠️ Falha ao sincronizar tempo com os servidores da API da Binance: {e}") # <-- CORREÇÃO AQUI

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
                    self.logger.warning(f"⚠️ Tentativa {tentativa}/{self.max_tentativas} falhou na rede do cliente: {e}") # <-- CORREÇÃO AQUI
                    self.logger.info(f"⏳ Aguardando {self.espera_entre_tentativas}s antes de retransmitir requisição...") # <-- CORREÇÃO AQUI
                    time.sleep(self.espera_entre_tentativas)
                else:
                    self.logger.error(f"❌ Todas as {self.max_tentativas} tentativas de comunicação da subconta falharam: {e}") # <-- CORREÇÃO AQUI
                    raise e

    def get_account_balance(self):
        """Busca os dados completos da conta do cliente"""
        def _get_balance():
            return self.client.get_account()
        return self._retry(_get_balance)

    def get_asset_balance(self, asset):
        """Busca o saldo de um ativo específico na conta do cliente"""
        def _get_asset_balance():
            balance = self.client.get_asset_balance(asset=asset)
            return float(balance['free'])
        return self._retry(_get_asset_balance)

    def get_current_price(self, symbol):
        """Busca o preço atual de um símbolo"""
        def _get_current_price():
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            return float(ticker['price'])
        return self._retry(_get_current_price)

    def get_symbol_info(self, symbol):
        """Busca informações e filtros de um símbolo"""
        def _get_symbol_info():
            return self.client.get_symbol_info(symbol=symbol)
        return self._retry(_get_symbol_info)

    def create_order(self, symbol, side, quantity):
        """Cria uma ordem de mercado"""
        def _create_order():
            order = self.client.create_order(
                symbol=symbol,
                side=side,
                type=ORDER_TYPE_MARKET,
                quantity=quantity,
                recvWindow=self.recv_window
            )
            self.logger.info(f"✅ Ordem {side} de {quantity} {symbol} executada. ID: {order['orderId']}") # <-- CORREÇÃO AQUI
            return order
        try:
            return self._retry(_create_order)
        except Exception as e:
            self.logger.error(f"❌ Falha ao criar ordem {side} para {symbol}: {e}") # <-- CORREÇÃO AQUI
            return None
