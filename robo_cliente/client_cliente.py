import os
import time
from binance.client import Client
from binance.enums import ORDER_TYPE_MARKET
from binance.exceptions import BinanceAPIException
from logger_cliente import TradingLoggerCliente  # type: ignore

class BinanceClient:
    def __init__(self, logger: TradingLoggerCliente = None):
        """
        Inicializa o SDK oficial da Binance para a conta do Cliente.
        Lê de forma nativa e direta as variáveis de ambiente da Stack do Portainer.
        """
        self.logger = logger if logger else TradingLoggerCliente()
        
        # Sincronização dos nomes das chaves de API com as variáveis oficiais da Stack
        self.api_key = os.getenv("KEY_BINANCE") or os.getenv("API_KEY")
        self.secret_key = os.getenv("SECRET_BINANCE") or os.getenv("API_SECRET")
        self.recv_window = int(os.getenv("RECV_WINDOW", 10000))

        # CORREÇÃO #2: Impede a injeção de parâmetros vazios para blindar o contêiner contra crash fatal
        if not self.api_key or not self.secret_key:
            self.logger.log_error("❌ ERRO CRÍTICO: Chaves da Binance do Cliente não localizadas na memória da Stack. Inicialização suspensa!")
            self.client = None
        else:
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
        if not self.client:
            return
        try:
            server_time = self.client.get_server_time()
            self.client.timestamp_offset = server_time['serverTime'] - int(time.time() * 1000)
            # CORREÇÃO #1: Nome do método ajustado de .info() para .log_info() conforme a biblioteca logger_cliente.py
            self.logger.log_info(f"⏰ Relógio do Cliente sincronizado com a Binance. Offset atual: {self.client.timestamp_offset} ms")
        except Exception as e:
            self.logger.log_warning(f"⚠ Falha ao sincronizar tempo com os servidores da API da Binance: {e}")

    def _retry(self, func, ignore_bad_requests=False):
        """Motor de redundância: repete a operação em caso de oscilações de rede ou timeout."""
        if not self.client:
            raise Exception("SDK da Binance não inicializado devido à falta de credenciais na Stack.")

        for tentativa in range(1, self.max_tentativas + 1):
            try:
                return func()
            except BinanceAPIException as e:
                # CORREÇÃO #3: Não repete requisições com parâmetros regulatórios falhos (Evita banimento de IP da VPS por SPAM)
                if ignore_bad_requests and e.code in [-1013, -1111, -2010, -2011]:
                    self.logger.log_error(f"❌ Rejeição imediata da Binance na subconta do cliente (Retentativa Abortada): {e.message}")
                    raise e

                # Se o erro for estritamente de dessincronização de relógio VPS, força o re-sync imediato
                if "code=-1021" in str(e):
                    self._sync_time()

                if tentativa < self.max_tentativas:
                    self.logger.log_warning(f"⚠ Tentativa {tentativa}/{self.max_tentativas} falhou na rede do cliente: {e.message}")
                    self.logger.log_info(f"⏳ Aguardando {self.espera_entre_tentativas}s antes de retransmitir requisição...")
                    time.sleep(self.espera_entre_tentativas)
                else:
                    self.logger.log_error(f"❌ Todas as {self.max_tentativas} tentativas de comunicação da subconta falharam: {e.message}")
                    raise e
            except Exception as ex:
                self.logger.log_warning(f"⚠ Instabilidade genérica na rede do cliente (Tentativa {tentativa}/{self.max_tentativas}): {ex}")
                if tentativa == self.max_tentativas:
                    raise ex
                time.sleep(self.espera_entre_tentativas)

    def get_account_balance(self):
        """Busca os dados completos da conta do cliente"""
        return self._retry(lambda: self.client.get_account(recvWindow=self.recv_window))

    def get_asset_balance(self, asset):
        """Busca o saldo de um ativo específico na conta do cliente"""
        try:
            # Captura a conta inteira respeitando as janelas de tolerância e retentativas de rede
            account = self.get_account_balance()
            if account:
                for balance in account.get("balances", []):
                    if balance["asset"] == asset:
                        return float(balance["free"])
            return 0.0
        except Exception as e:
            self.logger.log_error(f"❌ Erro ao rastrear saldo em carteira do cliente para o ativo {asset}: {e}")
            return 0.0

    def get_current_price(self, symbol):
        """Busca o preço atual de um símbolo"""
        return self._retry(lambda: float(self.client.get_symbol_ticker(symbol=symbol)["price"]))

    def get_symbol_info(self, symbol):
        """Busca informações e filtros de um símbolo"""
        return self._retry(lambda: self.client.get_symbol_info(symbol=symbol))

    def create_order(self, symbol, side, quantity):
        """Cria uma ordem de mercado na subconta do cliente aplicando proteção de SPAM."""
        def _create_order():
            order = self.client.create_order(
                symbol=symbol,
                side=side,
                type=ORDER_TYPE_MARKET,
                quantity=quantity,
                recvWindow=self.recv_window
            )
            self.logger.log_info(f"✅ Ordem {side} de {quantity} {symbol} executada na subconta. ID: {order['orderId']}")
            return order

        try:
            return self._retry(_create_order, ignore_bad_requests=True)
        except Exception as e:
            self.logger.log_error(f"❌ Falha ao criar ordem {side} para {symbol} na conta do cliente: {e}")
            return None
