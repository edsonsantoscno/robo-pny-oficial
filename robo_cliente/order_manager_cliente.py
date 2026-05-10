class OrderManagerCliente:
    def __init__(self, binance_client):
        self.client = binance_client

    def get_symbol_filters(self, symbol):
        """Busca as regras da Binance para a moeda específica (precisão e mínimo)"""
        try:
            info = self.client.get_symbol_info(symbol)
            if not info: return {}
            filters = {f["filterType"]: f for f in info["filters"]}
            return filters
        except Exception as e:
            print(f"❌ Erro filtros cliente: {e}")
            return {}

    def calculate_quantity(self, symbol, quantity_percent=1.0):
        """
        Calcula quanto o cliente vai comprar baseado na banca dele.
        quantity_percent: 1.0 = 100% da banca livre, 0.5 = 50%, etc.
        """
        try:
            # 1. Busca filtros e preço atual
            filters = self.get_symbol_filters(symbol)
            current_price = float(self.client.get_symbol_ticker(symbol=symbol)['price'])
            
            # 2. Busca saldo disponível do cliente em USDT
            balance = self.client.get_asset_balance(asset='USDT')
            usdt_free = float(balance['free'])

            # 3. Calcula o valor que será usado (Banca Livre * Percentual configurado)
            notional_target = usdt_free * quantity_percent
            
            # Margem de segurança para taxas e arredondamentos
            notional_target = notional_target * 0.98 

            # 4. Verifica mínimo da Binance (Geralmente 5 ou 10 USDT)
            min_notional = 10.0
            if "NOTIONAL" in filters:
                min_notional = float(filters["NOTIONAL"]["minNotional"])
            elif "MIN_NOTIONAL" in filters:
                min_notional = float(filters["MIN_NOTIONAL"]["minNotional"])

            if notional_target < min_notional:
                print(f"⚠️ Saldo insuficiente para o mínimo da Binance ({min_notional} USDT)")
                return None

            # 5. Calcula quantidade bruta e ajusta precisão (decimais)
            lot_filter = filters.get("LOT_SIZE")
            step_size = float(lot_filter["stepSize"])
            
            quantidade_raw = notional_target / current_price
            
            # Arredondamento matemático correto para a Binance
            precision = len(str(step_size).split('.')[-1]) if '.' in str(step_size) else 0
            quantidade = round(int(quantidade_raw / step_size) * step_size, precision)

            print(f"📊 [CLIENTE] Alvo: {notional_target:.2f} USDT | Qtd: {quantidade} {symbol}")
            
            return {"quantity": quantidade, "price": current_price}

        except Exception as e:
            print(f"❌ Erro cálculo ordem cliente: {e}")
            return None
