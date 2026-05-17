import math
from client import BinanceClient

class OrderManager:
    def __init__(self, binance_client):
        self.client = binance_client
        # Mínimo de 15.0 USDT para garantir aceitação e folga contra flutuações de mercado
        self.notional_minimo = 15.0 

    def get_symbol_filters(self, symbol):
        try:
            info = self.client.get_symbol_info(symbol)
            if not info:
                return {}
            filters = {}
            for f in info.get("filters", []):
                filters[f["filterType"]] = f
            return filters
        except Exception as e:
            print(f"❌ Erro ao buscar filtros da Binance: {e}")
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

            current_price = float(self.client.get_current_price(symbol))
            if not current_price or current_price == 0:
                print("❌ Erro: Preço não disponível ou zerado")
                return None

            min_qty = float(lot_filter["minQty"])
            step_size = float(lot_filter["stepSize"])

            # Descobre a precisão decimal estrita do ativo de forma matemática segura
            precision = int(round(-math.log10(step_size), 0)) if step_size < 1 else 0

            # Define o valor alvo em USDT para a operação baseado no config e nas regras
            if notional_filter:
                binance_min = float(notional_filter.get("minNotional") or notional_filter.get("minNotional", 11.0))
                notional_target = max(binance_min + 1.0, self.notional_minimo)
            else:
                notional_target = self.notional_minimo

            # Calcula quantidade garantindo arredondamento PARA CIMA (math.ceil)
            # Evita que o valor final em USDT fique abaixo do mínimo regulatório da Binance
            quantidade_crua = math.ceil((notional_target / current_price) / step_size) * step_size
            
            # BLINDAGEM DE PRECISÃO: Evita a dízima flutuante do Python que quebra a API da Binance
            quantidade = float(f"{quantidade_crua:.{precision}f}") if precision > 0 else float(int(quantidade_crua))

            # Garante quantidade mínima exigida pela exchange
            if quantidade < min_qty:
                quantidade = min_qty

            notional_final = quantidade * current_price

            print(f"📊 Cálculo ({side}): Notional={notional_final:.2f} USDT | "
                  f"Preço={current_price:.2f} USDT | "
                  f"Quantidade={quantidade:.{precision}f} | "
                  f"Precision={precision}")

            return {
                "quantity": quantidade,
                "notional": notional_final,
                "price": current_price,
                "notional_min": notional_target,
                "precision": precision
            }

        except Exception as e:
            print(f"❌ Erro ao calcular quantidade operacional: {e}")
            return None

    def validate_order(self, symbol, side, quantity):
        try:
            filters = self.get_symbol_filters(symbol)
            current_price = float(self.client.get_current_price(symbol))

            if not current_price:
                print("❌ Erro ao obter preço para validação")
                return False

            # Valida LOT_SIZE (mínimos e máximos da moeda)
            lot_filter = filters.get("LOT_SIZE", {})
            min_qty = float(lot_filter.get("minQty", 0.001))
            max_qty = float(lot_filter.get("maxQty", 9999999.0))

            if quantity < min_qty:
                print(f"❌ Quantidade {quantity} abaixo do mínimo permitido pela exchange {min_qty}")
                return False

            if quantity > max_qty:
                print(f"❌ Quantidade {quantity} acima do máximo permitido pela exchange {max_qty}")
                return False

            # Valida NOTIONAL (volume financeiro da ordem)
            notional_filter = filters.get("NOTIONAL") or filters.get("MIN_NOTIONAL") or {}
            min_notional = float(notional_filter.get("minNotional", 11.0))
            notional_real = quantity * current_price

            if notional_real < min_notional:
                print(f"❌ Notional {notional_real:.2f} USDT abaixo do mínimo da Binance {min_notional:.2f} USDT")
                return False

            # Valida saldos da conta real (Conversão explícita para FLOAT obrigatória)
            if side == "BUY":
                usdt_balance = float(self.client.get_asset_balance("USDT"))
                if usdt_balance < notional_real:
                    print(f"❌ Saldo Insuficiente na Binance! Necessário: {notional_real:.2f} USDT | Disponível: {usdt_balance:.2f} USDT")
                    return False

            elif side == "SELL":
                asset = symbol.replace("USDT", "")
                asset_balance = float(self.client.get_asset_balance(asset))
                if asset_balance < quantity:
                    print(f"❌ Saldo de {asset} insuficiente para venda! Necessário: {quantity:.6f} | Disponível: {asset_balance:.6f}")
                    return False

            return True

        except Exception as e:
            print(f"❌ Erro ao validar regras da ordem: {e}")
            return False

    def execute_order(self, symbol, side, quantity):
        try:
            order = self.client.create_order(symbol, side, quantity)
            return order
        except Exception as e:
            print(f"❌ Erro crítico ao executar ordem na API: {e}")
            return None
