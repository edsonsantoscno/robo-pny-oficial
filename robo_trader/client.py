import os
import time
import logging
from binance.client import Client
from binance.enums import ORDER_TYPE_MARKET
from binance.exceptions import BinanceAPIException

# Configuração básica de logs no console do terminal Docker
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

class BinanceClient:
    def __init__(self, api_key=None, api_secret=None):
        """
        Inicializa o SDK oficial da Binance.
        Puxa as chaves via parâmetros ou direto da memória da VPS (Docker/Portainer).
        """
        # Fallback de leitura de segurança direto das variáveis de ambiente da Stack
        self.api_key = api_key or os.getenv("KEY_BINANCE") or os.getenv("BINANCE_API_KEY")
        self.api_secret = api_secret or os.getenv("SECRET_BINANCE") or os.getenv("BINANCE_API_SECRET")
        
        if not self.api_key or not self.api_secret:
            logging.warning("⚠ Chaves de API não fornecidas ou ausentes nas variáveis de ambiente.")

        self.client = Client(self.api_key, self.api_secret)
        self.max_tentativas = 3
        self.espera_entre_tentativas = 10

    def _retry(self, func, ignore_bad_requests=False):
        """
        Motor de redundância: repete a operação em caso de oscilações de conexão de rede.
        Evita loop e SPAM em erros regulatórios da exchange (Fix #1).
        """
        for tentativa in range(1, self.max_tentativas + 1):
            try:
                return func()
            except BinanceAPIException as e:
                # CORREÇÃO: Não retenta erros lógicos ou de validação (ex: lote inválido, sem saldo ou par inexistente)
                # Códigos: -1013 (LOT_SIZE/MIN_NOTIONAL), -1111 (PRECISION), -2010/2011 (ACCOUNT_BALANCE/CANCEL_REJECT)
                if ignore_bad_requests and e.code in [-1013, -1111, -2010, -2011]:
                    logging.error(f"❌ Rejeição regulatória imediata da Binance (Retentativa Abortada): {e.message}")
                    raise e
                
                logging.warning(f"⚠ Erro detectado na API (Tentativa {tentativa}/{self.max_tentativas}): {e.message}. Aguardando reconexão...")
                if tentativa == self.max_tentativas:
                    logging.error("❌ Limite de retentativas atingido. Operação abortada por segurança.")
                    raise e
                time.sleep(self.espera_entre_tentativas)
            except Exception as ex:
                logging.warning(f"⚠ Instabilidade de rede genérica (Tentativa {tentativa}/{self.max_tentativas}): {ex}")
                if tentativa == self.max_tentativas:
                    raise ex
                time.sleep(self.espera_entre_tentativas)

    def create_order(self, symbol, side, quantity):
        """Envia ordem a mercado (MARKET) com tratamento de erro e proteção de SPAM."""
        return self._retry(
            lambda: self.client.create_order(
                symbol=symbol,
                side=side,
                type=ORDER_TYPE_MARKET,
                quantity=quantity
            ),
            ignore_bad_requests=True  # CORREÇÃO: Bloqueia reenvio cíclico de ordens com parâmetros inválidos
        )

    def get_account_balance(self):
        """Busca os dados completos da conta na Binance passando a janela de tolerância temporal."""
        recv_win = int(os.getenv("RECV_WINDOW", 10000))
        return self._retry(lambda: self.client.get_account(recvWindow=recv_win))

    def get_asset_balance(self, asset):
        """Filtra e retorna o saldo livre em carteira de um ativo específico (ex: 'USDT')."""
        try:
            account = self.get_account_balance()
            if account:
                for balance in account.get("balances", []):
                    if balance["asset"] == asset:
                        return float(balance["free"])
            return 0.0
        except Exception as e:
            logging.error(f"❌ Erro ao filtrar saldo em carteira para o ativo {asset}: {e}")
            return 0.0

    def get_klines(self, symbol, interval, limit=100):
        """Puxa o histórico de velas (candles) para o motor do pandas-ta analisar."""
        return self._retry(lambda:
            self.client.get_klines(symbol=symbol, interval=interval, limit=limit)
        )

    def get_symbol_info(self, symbol):
        """Busca os dados regulatórios, regras de tick e filtros de lote de uma moeda."""
        return self._retry(lambda:
            self.client.get_symbol_info(symbol)
        )

    def get_current_price(self, symbol):
        """Retorna o preço mais recente de mercado (Ticker) convertido para float."""
        return self._retry(lambda:
            float(self.client.get_symbol_ticker(symbol=symbol)["price"])
        )

    def get_notional_minimum(self, symbol):
        """Busca o valor mínimo em dólares (Notional) exigido pela Binance para operar a moeda."""
        try:
            symbol_info = self.get_symbol_info(symbol)
            if symbol_info:
                for f in symbol_info.get("filters", []):
                    if f["filterType"] in ["NOTIONAL", "MIN_NOTIONAL"]:
                        return float(f.get("minNotional") or f.get("notional") or 10.0)
            return 10.0
        except Exception as e:
            logging.error(f"❌ Erro ao rastrear notional mínimo regulatório: {e}")
            return 10.0
