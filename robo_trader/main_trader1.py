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
            
            if self.risk_manager.position_active:
                price_now = self.binance_client.get_current_price(self.risk_manager.current_symbol)
                banca_total += (self.risk_manager.entry_quantity * price_now)
            
            self.risk_manager.atualizar_banca(banca_total)

            ganho_usdt = self.risk_manager.get_ganho_atual()
            ganho_pct = self.risk_manager.get_percentual_ganho()
            meta_usdt = self.risk_manager.get_meta_diaria()
            
            print(f"\n" + "-"*60)
            print(f"💰 BANCA TOTAL: {banca_total:.2f} USDT | LIVRE: {usdt_livre:.2f} USDT")
            print(f"📈 LUCRO HOJE: {ganho_usdt:.2f} USDT ({ganho_pct:.2f}%)")
            print(f"🎯 META DIÁRIA: {meta_usdt:.2f} USDT | FALTA: {max(0, meta_usdt - ganho_usdt):.2f} USDT")
            print("-"*60)

            # 2. Verificação de Meta Diária
            if not self.risk_manager.pode_operar_hoje():
                agora = datetime.now()
                amanha = (agora + timedelta(days=1)).replace(hour=0, minute=1, second=0)
                segundos = (amanha - agora).total_seconds()
                print(f"🎯 META DIÁRIA ATINGIDA! Aguardando reset...")
                time.sleep(segundos)
                return True

            # 3. GESTÃO DE POSIÇÃO ATIVA (COM PROTEÇÃO DE TAXAS)
            if self.risk_manager.position_active:
                symbol = self.risk_manager.current_symbol
                price = self.binance_client.get_current_price(symbol)
                data = self.strategy.get_data(symbol, INTERVAL)
                signal = self.strategy.calculate_signal(data)
                
                pct_atual = ((price - self.risk_manager.entry_price) / self.risk_manager.entry_price) * 100
                stop, _ = self.risk_manager.check_stop_loss(price)
                take, _ = self.risk_manager.check_take_profit(price)
                
                print(f"👀 Monitorando {symbol}: Preço ${price:.4f} | Lucro Atual: {pct_atual:.2f}% | Sinal: {signal}")

                # Lógica de Saída
                pode_vender_por_sinal = (signal == "SELL" and pct_atual > 0.20)

                if stop or take or pode_vender_por_sinal:
                    reason = "STOP LOSS" if stop else "TAKE PROFIT" if take else f"SINAL SELL ({pct_atual:.2f}%)"
                    self._execute_sell(symbol, price, reason)
                return True

            # 4. SCANNER
            print(f"🔍 SCANNER ({MODO_ESTRATEGIA}): Analisando {len(SYMBOLS)} moedas...")
            for symbol in SYMBOLS:
                data = self.strategy.get_data(symbol, INTERVAL)
                if data is None: continue
                
                signal = self.strategy.calculate_signal(data)
                
                if signal == "BUY":
                    price = self.binance_client.get_current_price(symbol)
                    print(f"\n✅ COMPRA IDENTIFICADA: {symbol} a ${price}")
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
                
                # CALCULA STOP E TAKE PARA O CLIENTE
                stop_p = price * (1 - STOP_LOSS_PERCENT/100)
                take_p = price * (1 + TAKE_PROFIT_PERCENT/100)

                # ENVIAR SINAL COM STATUS 'new'
                self.signal_generator.generate_signal(
                    "BUY", calc["quantity"], price, symbol, 
                    status="new", 
                    stop_loss=stop_p, 
                    take_profit=take_p
                )
                
                self.logger.log_entry("BUY", symbol, calc["quantity"], price, calc["notional"], f"Modo: {MODO_ESTRATEGIA}")
                print(f"📡 Sinal de COMPRA (new) enviado ao Supabase.")

    def _execute_sell(self, symbol, price, reason):
        qty = self.risk_manager.entry_quantity
        if self.order_manager.validate_order(symbol, "SELL", qty):
            order = self.binance_client.create_order(symbol, "SELL", qty)
            if order:
                # ENVIAR SINAL COM STATUS 'closed' (Atualiza o ciclo)
                self.signal_generator.generate_signal("SELL", qty, price, symbol, status="closed")
                
                self.logger.log_entry("SELL", symbol, qty, price, qty*price, reason)
                self.risk_manager.clear_position()
                print(f"📡 Sinal de VENDA (closed) enviado ao Supabase.")

    def run_continuous(self):
        print("\n" + "="*60)
        print(f"🤖 ROBÔ SCANNER MESTRE - MODO: {MODO_ESTRATEGIA}")
        print(f"Ativos: {', '.join(SYMBOLS)}")
        print(f"Alvo TP: {TAKE_PROFIT_PERCENT}% | Stop SL: {STOP_LOSS_PERCENT}%")
        print("="*60 + "\n")
        
        while self.running:
            self.run_once()
            time.sleep(15)

if __name__ == "__main__":
    try:
        bot = TradingBotTrader()
        bot.run_continuous()
    except KeyboardInterrupt:
        print("\n⏹️ Robô desligado.")
