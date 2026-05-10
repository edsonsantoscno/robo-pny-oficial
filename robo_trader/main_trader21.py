import time
from datetime import datetime, timedelta
from config import *
from client import BinanceClient
from strategy import AgressiveStrategy
from order_manager import OrderManager
from risk_manager import RiskManager
from logger import TradingLogger
from signal_generator import SignalGenerator

class TradingBotTrader:
    def __init__(self):
        self.binance_client = BinanceClient()
        self.strategy = AgressiveStrategy(self.binance_client)
        self.order_manager = OrderManager(self.binance_client)
        self.risk_manager = RiskManager(BANCA_INICIAL, take_profit_meta_percent=TAKE_PROFIT_META_PERCENT)
        self.logger = TradingLogger()
        self.signal_generator = SignalGenerator()
        self.running = True

    def run_once(self):
        try:
            # 1. Atualização Financeira e Cálculo de Banca
            usdt_livre = self.binance_client.get_asset_balance("USDT")
            banca_total = usdt_livre
            
            # Se estiver posicionado, soma o valor atual do ativo à banca total
            if self.risk_manager.position_active:
                price_now = self.binance_client.get_current_price(self.risk_manager.current_symbol)
                banca_total += (self.risk_manager.entry_quantity * price_now)
            
            self.risk_manager.atualizar_banca(banca_total)

            # --- MONITOR DE SALDO E META (NOVO) ---
            ganho_usdt = self.risk_manager.get_ganho_atual()
            ganho_pct = self.risk_manager.get_percentual_ganho()
            meta_usdt = self.risk_manager.get_meta_diaria()
            
            print(f"\n" + "-"*60)
            print(f"💰 BANCA TOTAL: {banca_total:.2f} USDT | LIVRE: {usdt_livre:.2f} USDT")
            print(f"📈 LUCRO HOJE: {ganho_usdt:.2f} USDT ({ganho_pct:.2f}%)")
            print(f"🎯 META DIÁRIA: {meta_usdt:.2f} USDT | FALTA: {max(0, meta_usdt - ganho_usdt):.2f} USDT")
            print("-"*60)

            # 2. Verificação de Meta Diária e Auto-Reset
            if not self.risk_manager.pode_operar_hoje():
                agora = datetime.now()
                amanha = (agora + timedelta(days=1)).replace(hour=0, minute=1, second=0)
                segundos = (amanha - agora).total_seconds()
                print(f"🎯 META DIÁRIA ATINGIDA! Dormindo {int(segundos/3600)}h até o reset...")
                time.sleep(segundos)
                self.risk_manager.daily_target_reached = False
                self.risk_manager.banca_inicial = self.binance_client.get_asset_balance("USDT")
                return True

            # 3. GESTÃO DE POSIÇÃO ATIVA
            if self.risk_manager.position_active:
                symbol = self.risk_manager.current_symbol
                price = self.binance_client.get_current_price(symbol)
                data = self.strategy.get_data(symbol, INTERVAL)
                signal = self.strategy.calculate_signal(data)
                
                stop, _ = self.risk_manager.check_stop_loss(price)
                take, _ = self.risk_manager.check_take_profit(price)
                
                print(f"👀 Monitorando {symbol}: Preço ${price:.2f} | Sinal: {signal}")

                if stop or take or signal == "SELL":
                    reason = "STOP LOSS" if stop else "TAKE PROFIT" if take else "SINAL SELL"
                    self._execute_sell(symbol, price, reason)
                return True

            # 4. SCANNER: Busca oportunidade nas moedas da lista
            print(f"🔍 SCANNER: Analisando {len(SYMBOLS)} moedas...")
            for symbol in SYMBOLS:
                data = self.strategy.get_data(symbol, INTERVAL)
                if data is None: continue
                
                signal = self.strategy.calculate_signal(data)
                
                if signal == "BUY":
                    price = self.binance_client.get_current_price(symbol)
                    print(f"\n✅ SINAL DE COMPRA IDENTIFICADO: {symbol}")
                    self._execute_buy(symbol, price)
                    break 

            return True

        except Exception as e:
            print(f"❌ Erro no ciclo: {e}")
            return False

    def _execute_buy(self, symbol, price):
        calc = self.order_manager.calculate_quantity(symbol)
        if calc and self.order_manager.validate_order(symbol, "BUY", calc["quantity"]):
            order = self.binance_client.create_order(symbol, "BUY", calc["quantity"])
            if order:
                self.risk_manager.set_entry(symbol, price, calc["quantity"])
                # Envia sinal para o Supabase (Copy Trader)
                self.signal_generator.generate_signal("BUY", calc["quantity"], price, symbol)
                self.logger.log_entry("BUY", symbol, calc["quantity"], price, calc["notional"], "Estratégia Scanner")

    def _execute_sell(self, symbol, price, reason):
        qty = self.risk_manager.entry_quantity
        if self.order_manager.validate_order(symbol, "SELL", qty):
            order = self.binance_client.create_order(symbol, "SELL", qty)
            if order:
                # Envia sinal para o Supabase (Copy Trader)
                self.signal_generator.generate_signal("SELL", qty, price, symbol)
                self.logger.log_entry("SELL", symbol, qty, price, qty*price, reason)
                self.risk_manager.clear_position()

    def run_continuous(self):
        print("\n" + "="*60)
        print("🤖 ROBÔ SCANNER MESTRE - AGRESSIVO")
        print(f"Ativos: {', '.join(SYMBOLS)}")
        print(f"Meta: {META_DIARIA_PERCENT}% | SL: {STOP_LOSS_PERCENT}% | TP: {TAKE_PROFIT_PERCENT}%")
        print("="*60 + "\n")
        
        while self.running:
            self.run_once()
            time.sleep(15) # Ciclo de 15 segundos

if __name__ == "__main__":
    try:
        bot = TradingBotTrader()
        bot.run_continuous()
    except KeyboardInterrupt:
        print("\n⏹️ Robô desligado pelo usuário.")
