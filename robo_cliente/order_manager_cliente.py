import math
from client_cliente import BinanceClient
from logger_cliente import TradingLoggerCliente

class OrderManagerCliente:
    def __init__(self, binance_client, logger: TradingLoggerCliente):
        """Inicializa o gerenciador de ordens proporcional da subconta do cliente."""
        self.client = binance_client
        self.logger = logger

    def get_symbol_filters(self, symbol):
        """Busca as regras e filtros regulatórios da Binance para a moeda específica (precisão e mínimo)."""
        try:
            info = self.client.get_symbol_info(symbol)
            if not info:
                self.logger.log_warning(f"⚠ [CLIENTE] Não foi possível obter informações do símbolo {symbol}.")
                return {}
            filters = {f["filterType"]: f for f in info.get("filters", [])}
            return filters
        except Exception as e:
            self.logger.log_error(f"❌ Erro ao buscar filtros regulatórios do cliente para {symbol}: {e}")
            return {}

    def calculate_quantity(self, symbol, quantity_percent=1.0):
        """
        Calcula quanto o cliente vai comprar baseado na banca livre real dele.
        quantity_percent: 1.0 = 100% da banca livre, 0.5 = 50%, etc.
        """
        try:
            # 1. Busca filtros e preço atual usando os métodos protegidos do cliente
            filters = self.get_symbol_filters(symbol)
            current_price = float(self.client.get_current_price(symbol))
            if not current_price or current_price == 0:
                self.logger.log_error(f"❌ [CLIENTE] Erro: Preço atual de {symbol} indisponível.")
                return None

            # 2. Captura o saldo livre real em USDT do cliente
            usdt_free = float(self.client.get_asset_balance("USDT"))

            # 3. Calcula o valor financeiro alvo em USDT alocado para a operação
            notional_target = usdt_free * float(quantity_percent)

            # Margem de segurança de 2% para cobrir taxas de corretagem da Binance e slippage
            notional_target = notional_target * 0.98

            # 4. CORREÇÃO #2: Suporte unificado para minNotional (Spot) e notional (Futures)
            min_notional = 10.0
            notional_filter = filters.get("NOTIONAL") or filters.get("MIN_NOTIONAL")
            if notional_filter:
                min_notional = float(notional_filter.get("minNotional") or notional_filter.get("notional") or 11.0)

            if notional_target < min_notional:
                self.logger.log_warning(f"⚠ [CLIENTE] Saldo proporcional ({notional_target:.2f} USDT) abaixo do mínimo da Binance ({min_notional} USDT)")
                return None

            # 5. Calcula quantidade bruta e ajusta a precisão decimal (LOT_SIZE)
            lot_filter = filters.get("LOT_SIZE")
            if not lot_filter:
                self.logger.log_error(f"❌ [CLIENTE] Filtro LOT_SIZE não encontrado para {symbol}.")
                return None

            min_qty = float(lot_filter["minQty"])
            step_size = float(lot_filter["stepSize"])

            # Descobre o número exato de casas decimais permitidas de forma matemática segura
            precision = int(round(-math.log10(step_size), 0)) if step_size < 1 else 0

            # Calcula a quantidade respeitando as frações de lote (stepSize) da exchange
            quantidade_raw = (notional_target / current_price)
            quantidade_ajustada = math.floor(quantidade_raw / step_size) * step_size

            # CORREÇÃO #1: Truncagem matemática limpa + round(). Elimina micro-dízimas flutuantes na RAM
            quantidade = round(quantidade_ajustada, precision)

            # Validação final de lote mínimo da moeda
            if quantidade < min_qty:
                quantidade = min_qty

            notional_final = quantidade * current_price

            self.logger.log_info(f"📊 [CLIENTE] Alvo: {notional_final:.2f} USDT | Preço: {current_price:.4f} | Qtd Ajustada: {quantidade}")
            
            return {
                "quantity": quantidade,
                "price": current_price,
                "notional": notional_final
            }
        except Exception as e:
            self.logger.log_error(f"❌ Erro operacional no cálculo de ordens do cliente: {e}")
            return None

    def validate_order(self, symbol, side, quantity):
        """Valida se a subconta do cliente possui os saldos reais físicos necessários para a execução."""
        try:
            if quantity <= 0:
                self.logger.log_warning(f"⚠ [CLIENTE] Quantidade para validação de ordem é zero ou negativa: {quantity}")
                return False

            current_price = float(self.client.get_current_price(symbol))
            notional_real = quantity * current_price

            if side == "BUY":
                usdt_balance = float(self.client.get_asset_balance("USDT"))
                # Aplica margem técnica de 0.2% para garantir saldo suficiente para pagar a taxa da exchange
                if usdt_balance < (notional_real * 1.002):
                    self.logger.log_error(f"❌ [CLIENTE] Saldo insuficiente para compra! Necessário com taxas: {(notional_real * 1.002):.2f} USDT | Disponível: {usdt_balance:.2f} USDT")
                    return False
            elif side == "SELL":
                asset = symbol.replace("USDT", "")
                asset_balance = float(self.client.get_asset_balance(asset))
                if asset_balance < quantity:
                    self.logger.log_error(f"❌ [CLIENTE] Ativo insuficiente para venda! Necessário: {quantity:.6f} {asset} | Disponível: {asset_balance:.6f} {asset}")
                    return False

            self.logger.log_info(f"✅ [CLIENTE] Ordem de {side} para {symbol} com {quantity} validada.")
            return True
        except Exception as e:
            self.logger.log_error(f"❌ Erro ao validar ordem do cliente: {e}")
            return False
