# main_trader.py
import time
from datetime import datetime, timedelta
from binance.enums import SIDE_BUY, SIDE_SELL
from client import BinanceClient
from strategy import MovingAverageStrategy
from order_manager import OrderManager
from risk_manager import RiskManager
from logger import TradingLogger
from signal_generator import SignalGenerator
from config import SYMBOL, ASSET, INTERVAL, BANCA_INICIAL, TAKE_PROFIT_META_PERCENT, STOP_LOSS_PERCENT

class TradingBotTrader:
    def __init__(self, banca_inicial=BANCA_INICIAL):
        self.binance_client = BinanceClient()
        self.strategy = MovingAverageStrategy(self.binance_client)
        self.order_manager = OrderManager(self.binance_client)
        self.risk_manager = RiskManager(banca_inicial, take_profit_meta_percent=TAKE_PROFIT_META_PERCENT)
        self.logger = TradingLogger()
        self.signal_generator = SignalGenerator()
        self.running = True

        self._verificar_estado_inicial()

    def _verificar_estado_inicial(self):
        try:
            sol_balance = self.binance_client.get_asset_balance(ASSET)
            if sol_balance > 0.001 and not self.risk_manager.position_active:
                current_price = self.binance_client.get_current_price(SYMBOL)
                print(f"⚠️  Detectado {sol_balance:.8f} {ASSET} em carteira sem posição registrada.")
                print(f"⚠️  Registrando posição com preço atual {current_price:.2f} USDT para evitar compra dupla.")
                self.risk_manager.set_entry(current_price, sol_balance)
        except Exception as e:
            print(f"❌ Erro ao verificar estado inicial: {e}")

    def atualizar_banca(self):
        try:
            usdt_balance = self.binance_client.get_asset_balance("USDT")

            if self.risk_manager.position_active:
                sol_balance = self.binance_client.get_asset_balance(ASSET)
                if sol_balance > 0:
                    current_price = self.binance_client.get_current_price(SYMBOL)
                    if current_price:
                        total = usdt_balance + (sol_balance * current_price)
                        self.risk_manager.atualizar_banca(total)
                        return total

            self.risk_manager.atualizar_banca(usdt_balance)
            return usdt_balance

        except Exception as e:
            print(f"❌ Erro ao atualizar banca: {e}")
            return None

    def run_once(self):
        try:
            banca_atual = self.atualizar_banca()
            self.risk_manager.check_meta_diaria()

            if not self.risk_manager.pode_operar_hoje():
                ganho = self.risk_manager.get_ganho_atual()
                percentual = self.risk_manager.get_percentual_ganho()
                self.logger.log_meta_atingida(ganho, percentual)

                agora = datetime.now()
                amanha = (agora + timedelta(days=1)).replace(
                    hour=0, minute=1, second=0, microsecond=0
                )
                segundos_restantes = (amanha - agora).total_seconds()
                horas = int(segundos_restantes // 3600)
                minutos = int((segundos_restantes % 3600) // 60)

                print(f"\n{'='*60}")
                print(f"🎯 META DIÁRIA ATINGIDA!")
                print(f"Ganho: +{ganho:.2f} USDT (+{percentual:.2f}%)")
                print(f"Robô dormindo por {horas}h {minutos}min até 00:01.")
                print(f"{'='*60}\n")

                time.sleep(segundos_restantes)
                return True

            data = self.strategy.get_data(SYMBOL, INTERVAL)
            if data is None:
                print("❌ Erro ao buscar dados.")
                return False

            signal = self.strategy.calculate_signal(data)

            if self.risk_manager.position_active:
                current_price = self.binance_client.get_current_price(SYMBOL)

                should_stop, loss_percent = self.risk_manager.check_stop_loss(current_price)
                if should_stop:
                    self.logger.log_stop(
                        f"STOP LOSS -{STOP_LOSS_PERCENT}% | Preço: {current_price:.2f} USDT",
                        loss_percent
                    )
                    print(f"\n{'='*60}")
                    print(f"🛑 STOP LOSS ACIONADO!")
                    print(f"Preço de entrada: {self.risk_manager.entry_price:.2f} USDT")
                    print(f"Preço atual: {current_price:.2f} USDT")
                    print(f"Perda: {loss_percent:.2f}%")
                    print(f"{'='*60}\n")
                    self._execute_sell(reason=f"Stop Loss -{STOP_LOSS_PERCENT}%")
                    return True

                should_take, lucro_usdt = self.risk_manager.check_take_profit(current_price)
                if should_take:
                    alvo = self.risk_manager.get_take_profit_usdt()
                    print(f"\n{'='*60}")
                    print(f"🎯 TAKE PROFIT ATINGIDO!")
                    print(f"Alvo por operação: +{alvo:.2f} USDT (10% da meta diária)")
                    print(f"Lucro atual: +{lucro_usdt:.2f} USDT")
                    print(f"{'='*60}\n")
                    self._execute_sell(reason="Take Profit 10% meta diária")
                    return True

            if signal == "BUY" and not self.risk_manager.position_active:
                self._execute_buy()
            elif signal == "SELL" and self.risk_manager.position_active:
                self._execute_sell(reason="Média rápida (9) < Média lenta (21)")

            ganho = self.risk_manager.get_ganho_atual()
            percentual = self.risk_manager.get_percentual_ganho()
            meta = self.risk_manager.get_meta_diaria()
            alvo_op = self.risk_manager.get_take_profit_usdt()

            print(f"\n📊 STATUS DA BANCA:")
            print(f"Banca inicial: {self.risk_manager.banca_inicial:.2f} USDT")
            print(f"Banca atual: {banca_atual:.2f} USDT")
            print(f"Ganho: {ganho:.2f} USDT ({percentual:.2f}%)")
            print(f"Meta diária: +{meta:.2f} USDT (+2%)")
            print(f"Alvo por operação: +{alvo_op:.2f} USDT (10% da meta)")
            print(f"Faltam: {meta - ganho:.2f} USDT para meta\n")

            return True

        except Exception as e:
            print(f"❌ Erro no ciclo: {e}")
            return False

    def run_continuous(self):
        print("=" * 60)
        print("🤖 ROBÔ TRADER INICIADO")
        print(f"Símbolo: {SYMBOL}")
        print(f"Intervalo: {INTERVAL}")
        print(f"Estratégia: Média Rápida (9) x Média Lenta (21)")
        print(f"Banca inicial: {self.risk_manager.banca_inicial:.2f} USDT")
        print(f"Meta diária: +2% ({self.risk_manager.get_meta_diaria():.2f} USDT)")
        print(f"Alvo por operação: +{self.risk_manager.get_take_profit_usdt():.2f} USDT (10% da meta)")
        print(f"Stop Loss por operação: -{STOP_LOSS_PERCENT}% do preço de entrada")
        print("=" * 60 + "\n")

        while self.running:
            try:
                self.run_once()
                time.sleep(60)
            except KeyboardInterrupt:
                print("\n\n⏹️  Robô parado pelo usuário.")
                self.running = False
            except Exception as e:
                print(f"❌ Erro na execução contínua: {e}")
                time.sleep(60)

    def _execute_buy(self):
        try:
            sol_balance = self.binance_client.get_asset_balance(ASSET)
            if sol_balance > 0.001:
                print(f"⚠️  Compra bloqueada: já existe {sol_balance:.8f} {ASSET} em carteira.")
                self.risk_manager.set_entry(
                    self.binance_client.get_current_price(SYMBOL), sol_balance
                )
                return

            calc_result = self.order_manager.calculate_quantity(SYMBOL)
            if calc_result is None:
                print("❌ Erro ao calcular quantidade")
                return

            quantity = calc_result["quantity"]

            if not self.order_manager.validate_order(SYMBOL, "BUY", quantity):
                print("❌ Ordem de compra não validada")
                return

            current_price = self.binance_client.get_current_price(SYMBOL)
            notional = quantity * current_price
            alvo_op = self.risk_manager.get_take_profit_usdt()
            stop_price = current_price * (1 - STOP_LOSS_PERCENT / 100)

            order = self.order_manager.execute_order(SYMBOL, SIDE_BUY, quantity)

            if order:
                self.logger.log_entry(
                    "BUY", SYMBOL, quantity, current_price, notional,
                    f"Média rápida (9) > Média lenta (21) | Alvo: +{alvo_op:.2f} USDT"
                )
                self.risk_manager.set_entry(current_price, quantity)
                self.signal_generator.generate_signal(
                    operation_type="BUY",
                    quantity=quantity,
                    price=current_price,
                    notional=notional,
                    stop_loss_percent=-STOP_LOSS_PERCENT,
                    take_profit_percent=None
                )
                print(f"\n✅ COMPRA EXECUTADA")
                print(f"Quantidade: {quantity:.8f} {ASSET}")
                print(f"Preço: {current_price:.2f} USDT")
                print(f"Notional: {notional:.2f} USDT")
                print(f"Stop Loss: {stop_price:.2f} USDT (-{STOP_LOSS_PERCENT}%)")
                print(f"Take Profit alvo: +{alvo_op:.2f} USDT\n")
            else:
                print("❌ Erro ao executar compra")

        except Exception as e:
            print(f"❌ Erro ao executar compra: {e}")

    def _execute_sell(self, reason="Média rápida (9) < Média lenta (21)"):
        try:
            quantity = self.binance_client.get_asset_balance(ASSET)
            if quantity <= 0:
                print("❌ Nenhuma quantidade disponível para vender")
                return

            symbol_info = self.binance_client.get_symbol_info(SYMBOL)
            if symbol_info:
                for f in symbol_info["filters"]:
                    if f["filterType"] == "LOT_SIZE":
                        step_size = float(f["stepSize"])
                        quantity = int(quantity / step_size) * step_size
                        quantity = round(quantity, 8)
                        break

            if not self.order_manager.validate_order(SYMBOL, "SELL", quantity):
                print("❌ Ordem de venda não validada")
                return

            current_price = self.binance_client.get_current_price(SYMBOL)
            notional = quantity * current_price

            if self.risk_manager.entry_price and self.risk_manager.entry_price > 0:
                ganho_operacao = ((current_price - self.risk_manager.entry_price) / self.risk_manager.entry_price) * 100
                lucro_usdt = (current_price - self.risk_manager.entry_price) * quantity
            else:
                ganho_operacao = 0.0
                lucro_usdt = 0.0

            order = self.order_manager.execute_order(SYMBOL, SIDE_SELL, quantity)

            if order:
                self.logger.log_entry(
                    "SELL", SYMBOL, quantity, current_price, notional,
                    f"{reason} | Ganho: {ganho_operacao:+.2f}% ({lucro_usdt:+.2f} USDT)"
                )
                self.risk_manager.clear_entry()
                self.signal_generator.generate_signal(
                    operation_type="SELL",
                    quantity=quantity,
                    price=current_price,
                    notional=notional,
                    stop_loss_percent=-STOP_LOSS_PERCENT,
                    take_profit_percent=None
                )
                print(f"\n✅ VENDA EXECUTADA")
                print(f"Quantidade: {quantity:.8f} {ASSET}")
                print(f"Preço: {current_price:.2f} USDT")
                print(f"Notional: {notional:.2f} USDT")
                print(f"Ganho da operação: {ganho_operacao:+.2f}% ({lucro_usdt:+.2f} USDT)\n")
            else:
                print("❌ Erro ao executar venda")

        except Exception as e:
            print(f"❌ Erro ao executar venda: {e}")

if __name__ == "__main__":
    bot = TradingBotTrader(banca_inicial=BANCA_INICIAL)
    bot.run_continuous()