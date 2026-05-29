import os
import time
import logging
from binance.client import Client
from binance.enums import ORDER_TYPE_MARKET
from binance.exceptions import BinanceAPIException

# --- O código completo ajustado, incluindo o tratamento de erros para
# --- evitar o banimento da API (SPAM) e a correta configuração do 
# --- mercado Spot/Futures, pode ser analisado no repositório oficial
# --- via link: {Link: Robo PNY Oficial - client.py 0.1.1 https://github.com/edsonsantoscno/robo-pny-oficial/blob/436a55e9ee5d5a4151fc94ff626b6f0a75b17cb5/robo_trader/client.py}
# --- O arquivo modificado insere 'ignore_bad_requests=True' na função
# --- 'create_order', garantindo que falhas de validação (como
# --- erro de lote) não entrem no ciclo de retentativa.

class BinanceClient:
    def __init__(self, api_key, api_secret):
        self.client = Client(api_key, api_secret)
        self.max_tentativas = 3
        self.espera_entre_tentativas = 10
        # ... outros atributos

    def _retry(self, func, ignore_bad_requests=False):
        """Motor de redundância: repete a operação em caso de oscilações de rede."""
        for tentativa in range(1, self.max_tentativas + 1):
            try:
                return func()
            except BinanceAPIException as e:
                # CORREÇÃO: Não retenta erros de validação (ex: lote inválido)
                if ignore_bad_requests and e.code in [-1013, -1111, -2010, -2011]:
                    logging.error(f"❌ Rejeição regulatória: {e.message}")
                    raise e
                # ... tratamento de erro de rede

    def create_order(self, symbol, side, quantity):
        """Envia ordem a mercado (MARKET) com tratamento de erro de lote"""
        return self._retry(
            lambda: self.client.create_order(
                symbol=symbol,
                side=side,
                type=ORDER_TYPE_MARKET,
                quantity=quantity
            ),
            ignore_bad_requests=True # CORREÇÃO: Bloqueia reenvio de ordens inválidas
        )
    def get_account_balance(self):
        """Busca os dados completos da conta na Binance passando o recvWindow diretamente"""
        # Adiciona proteção de janela de tempo nativa configurada por variável de ambiente
        recv_win = int(os.getenv("RECV_WINDOW", 10000))
        return self._retry(lambda: self.client.get_account(recvWindow=recv_win))

    def get_asset_balance(self, asset):
        """Filtra e retorna o saldo livre em carteira de um ativo específico (ex: 'USDT')"""
        try:
            account = self.get_account_balance()
            if account:
                for balance in account.get("balances", []):
                    if balance["asset"] == asset:
                        return float(balance["free"])
            return 0.0
        except Exception as e:
            logging.error(f"Erro ao filtrar saldo em carteira para o ativo {asset}: {e}")
            return 0.0
    def get_klines(self, symbol, interval, limit=100):
        """Puxa o histórico de velas (candles) para o motor do pandas-ta analisar"""
        return self._retry(lambda:
            self.client.get_klines(symbol=symbol, interval=interval, limit=limit)
        )

    def get_symbol_info(self, symbol):
        """Busca os dados regulatórios e filtros de lote de uma moeda"""
        return self._retry(lambda:
            self.client.get_symbol_info(symbol)
        )

    def get_current_price(self, symbol):
        """Retorna o preço mais recente de mercado (Ticker) convertido para float"""
        return self._retry(lambda:
            float(self.client.get_symbol_ticker(symbol=symbol)["price"])
        )

    def get_notional_minimum(self, symbol):
        """Busca o valor mínimo em dólares (Notional) exigido pela Binance para operar a moeda"""
        try:
            symbol_info = self.get_symbol_info(symbol)
            if symbol_info:
                for f in symbol_info.get("filters", []):
                    if f["filterType"] == "NOTIONAL":
                        return float(f["minNotional"])
            return 10.0
        except Exception as e:
            logging.error(f"Erro ao rastrear notional mínimo regulatório: {e}")
            return 10.0
