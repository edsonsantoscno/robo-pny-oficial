import math
# Importação corrigida para o BinanceClient do cliente
from client_cliente import BinanceClient # type: ignore

class OrderManagerCliente:
    def __init__(self, binance_client: BinanceClient): # Adicionado type hint
        self.client = binance_client

    def get_symbol_filters(self, symbol):
        """Busca as regras e filtros regulatórios da Binance para a moeda específica (precisão e mínimo)"""
        try:
            info = self.client.get_symbol_info(symbol)
            if not info: return {}
            filters = {f["filterType"]: f for f in info.get("filters", [])}
            return filters
        except Exception as e:
            print(f"❌ Erro ao buscar filtros regulatórios do cliente para {symbol}: {e}")
            return {}

    def calculate_quantity(self, symbol, quantity_percent=1.0):
        """
        Calcula quanto o cliente vai comprar baseado na banca livre real dele.
        quantity_percent: 1.0 = 100% da banca livre, 0.5 = 50%, etc.
        """
        try:
            # 1. Busca filtros e preço atual usando os métodos encapsulados e protegidos do seu cliente
            filters = self.get_symbol_filters(symbol)
            current_price = float(self.client.get_current_price(symbol))

            if not current_price or current_price == 0:
                print(f"❌ [CLIENTE] Erro: Preço atual de {symbol} indisponível.")
                return None

            # 2. CORREÇÃO CRÍTICA: O get_asset_balance já retorna um FLOAT puro do seu client.py
            usdt_free = float(self.client.get_asset_balance("USDT"))

            # 3. Calcula o valor financeiro alvo em USDT que será alocado para a operação
            notional_target = usdt_free * float(quantity_percent)

            # Margem de segurança de 2% para cobrir taxas de corretagem da Binance e derrapagem (Slippage)
            notional_target = notional_target * 0.98

            # 4. Verifica o volume mínimo exigido pela Binance para o par (Geralmente 5 ou 10 USDT)
            min_notional = 10.0
            notional_filter = filters.get("NOTIONAL") or filters.get("MIN_NOTIONAL")
            if notional_filter:
                min_notional = float(notional_filter.get("minNotional", 11.0))

            if notional_target < min_notional:
                print(f"⚠️ [CLIENTE] Saldo proporcional ({notional_target:.2f} USDT) abaixo do mínimo da Binance ({min_notional} USDT)")
                return None

            # 5. Calcula quantidade bruta e ajusta a precisão decimal (LOT_SIZE) de forma matemática estrita
            lot_filter = filters.get("LOT_SIZE")
            if not lot_filter:
                print(f"❌ [CLIENTE] Filtro LOT_SIZE não encontrado para {symbol}.")
                return None

            min_qty = float(lot_filter["minQty"])
            step_size = float(lot_filter["stepSize"])

            # Descobre o número exato de casas decimais permitidas usando base logarítmica segura
            precision = int(round(-math.log10(step_size), 0)) if step_size < 1 else 0

            # Calcula a quantidade respeitando as frações de lote (stepSize) da exchange
            quantidade_raw = (notional_target / current_price)
            quantidade_ajustada = math.floor(quantidade_raw / step_size) * step_size

            # BLINDAGEM DE PRECISÃO: Elimina a dízima flutuante do Python que causa rejeição por LOT_SIZE
            quantidade = float(f"{quantidade_ajustada:.{precision}f}") if precision > 0 else float(int(quantidade_ajustada))

            # Validação final de lote mínimo da moeda
            if quantidade < min_qty:
                quantidade = min_qty

            notional_final = quantidade * current_price
            print(f"📊 [CLIENTE] Alvo: {notional_final:.2f} USDT | Preço: {current_price:.4f} | Qtd Ajustada: {quantidade:.{precision}f}")

            return {
                "quantity": quantidade,
                "price": current_price,
                "notional": notional_final
            }

        except Exception as e:
            print(f"❌ Erro operacional no cálculo de ordens do cliente: {e}")
            return None

    def validate_order(self, symbol, side, quantity):
        """Valida se a subconta do cliente possui os saldos reais físicos necessários para a execução"""
        try:
            if quantity <= 0: return False
            current_price = float(self.client.get_current_price(symbol))
            notional_real = quantity * current_price

            if side == "BUY":
                usdt_balance = float(self.client.get_asset_balance("USDT"))
                if usdt_balance < notional_real:
                    print(f"❌ [CLIENTE] Saldo insuficiente para compra! Necessário: {notional_real:.2f} USDT | Disponível: {usdt_balance:.2f} USDT")
                    return False
            elif side == "SELL":
                asset = symbol.replace("USDT", "")
                asset_balance = float(self.client.get_asset_balance(asset))
                if asset_balance < quantity:
                    print(f"❌ [CLIENTE] Ativo insuficiente para venda! Necessário: {quantity:.6f} {asset} | Disponível: {asset_balance:.6f} {asset}")
                    return False
            return True
        except Exception as e:
            print(f"❌ Erro ao validar ordem do cliente: {e}")
            return False
