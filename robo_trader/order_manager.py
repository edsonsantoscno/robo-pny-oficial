# order_manager.py
import math
from client import BinanceClient

class OrderManager:
    def __init__(self, binance_client):
        self.client = binance_client
        # Aumentado para 15.0 para garantir aceitação em pares como BTC/ETH
        # e aproveitar melhor sua banca de 190 USDT.
        self.notional_minimo = 15.0 

    def get_symbol_filters(self, symbol):
        try:
            info = self.client.get_symbol_info(symbol)
            if not info:
                return {}
            filters = {}
            for f in info["filters"]:
                filters[f["filterType"]] = f
            return filters
        except Exception as e:
            print(f"❌ Erro ao buscar filtros: {e}")
            return {}

    def calculate_quantity(self, symbol, side="BUY"):
        try:
            filters = self.get_symbol_filters(symbol)

            if not filters:
                print("❌ Erro: Filtros do símbolo não disponíveis")
                return None

            lot_filter = filters.get("LOT_SIZE")
            notional_filter = filters.get("NOTIONAL") or filters.get("MIN_NOTIONAL")

            if not lot_filter:
                print("❌ Erro: Filtro LOT_SIZE não encontrado")
                return None

            current_price = self.client.get_current_price(symbol)
            if not current_price or current_price == 0:
                print("❌ Erro: Preço não disponível")
                return None

            min_qty = float(lot_filter["minQty"])
            step_size = float(lot_filter["stepSize"])

            # Descobre a precisão decimal necessária para o ativo
            precision = int(round(-math.log10(step_size), 0)) if step_size < 1 else 0

            # Define o valor alvo em USDT para a operação
            if notional_filter:
                binance_min = float(notional_filter.get("minNotional", 11.0))
                notional_target = max(binance_min + 1.0, self.notional_minimo)
            else:
                notional_target = self.notional_minimo

            # Calcula quantidade garantindo arredondamento PARA CIMA (math.ceil)
            # Isso evita que o valor final em USDT fique abaixo do mínimo da Binance
            quantidade = math.ceil((notional_target / current_price) / step_size) * step_size
            quantidade = round(quantidade, precision)

            # Garante quantidade mínima exigida pelo exchange
            if quantidade < min_qty:
                quantidade = min_qty

            notional_final = quantidade * current_price

            print(f"📊 Cálculo ({side}): Notional={notional_final:.2f} USDT | "
                  f"Preço={current_price:.2f} USDT | "
                  f"Quantidade={quantidade:.8f} | "
                  f"Step={step_size}")

            return {
                "quantity": quantidade,
                "notional": notional_final,
                "price": current_price,
                "notional_min": notional_target
            }

        except Exception as e:
            print(f"❌ Erro ao calcular quantidade: {e}")
            return None

    def validate_order(self, symbol, side, quantity):
        try:
            filters = self.get_symbol_filters(symbol)
            current_price = self.client.get_current_price(symbol)

            if not current_price:
                print("❌ Erro ao obter preço para validação")
                return False

            # Valida LOT_SIZE
            lot_filter = filters.get("LOT_SIZE", {})
            min_qty = float(lot_filter.get("minQty", 0.001))
            max_qty = float(lot_filter.get("maxQty", 9999999))

            if quantity < min_qty:
                print(f"❌ Quantidade {quantity} abaixo do mínimo {min_qty}")
                return False

            if quantity > max_qty:
                print(f"❌ Quantidade {quantity} acima do máximo {max_qty}")
                return False

            # Valida NOTIONAL
            notional_filter = filters.get("NOTIONAL") or filters.get("MIN_NOTIONAL") or {}
            min_notional = float(notional_filter.get("minNotional", 11.0))
            notional_real = quantity * current_price

            if notional_real < min_notional:
                print(f"❌ Notional {notional_real:.2f} USDT abaixo do mínimo {min_notional:.2f} USDT")
                return False

            # Valida saldo
            if side == "BUY":
                usdt_balance = self.client.get_asset_balance("USDT")
                if usdt_balance < notional_real:
                    print(f"❌ Saldo insuficiente. Necessário: {notional_real:.2f} USDT, Disponível: {usdt_balance:.2f} USDT")
                    return False

            elif side == "SELL":
                asset = symbol.replace("USDT", "")
                asset_balance = self.client.get_asset_balance(asset)
                if asset_balance < quantity:
                    print(f"❌ Ativo insuficiente. Necessário: {quantity:.8f}, Disponível: {asset_balance:.8f}")
                    return False

            return True

        except Exception as e:
            print(f"❌ Erro ao validar ordem: {e}")
            return False

    def execute_order(self, symbol, side, quantity):
        try:
            order = self.client.create_order(symbol, side, quantity)
            return order
        except Exception as e:
            print(f"❌ Erro ao executar ordem: {e}")
            return None
