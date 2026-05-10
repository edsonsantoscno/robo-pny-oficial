# copy_trader.py
import json
import time
import threading
from client_cliente import BinanceClientCliente
from risk_manager_cliente import RiskManagerCliente
from logger_cliente import TradingLoggerCliente
from config_cliente import (
    SYMBOL, ASSET, SIGNALS_FILE, QUANTIDADE_PERCENTUAL,
    STOP_LOSS_PERCENT, META_DIARIA_PERCENT, COPY_TRADER_ATIVO,
    CLIENTE_NOME, BANCA_INICIAL, TAKE_PROFIT_META_PERCENT
)
from binance.enums import SIDE_BUY, SIDE_SELL


class StopLossMonitor:
    """
    Thread separada que verifica stop loss e take profit a cada 5 segundos,
    evitando que movimentos bruscos passem despercebidos no ciclo de 60s.
    """
    def __init__(self, binance_client, risk_manager, logger, copy_trader_ref, intervalo=5):
        self.binance_client = binance_client
        self.risk_manager = risk_manager
        self.logger = logger
        self.copy_trader_ref = copy_trader_ref
        self.intervalo = intervalo
        self._stop_event = threading.Event()
        self._thread = None

    def iniciar(self):
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._monitorar, daemon=True)
        self._thread.start()
        print(f"🔍 Monitor iniciado (stop loss e take profit a cada {self.intervalo}s)")

    def parar(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join()
        print("🔍 Monitor encerrado")

    def _monitorar(self):
        while not self._stop_event.is_set():
            try:
                if self.risk_manager.position_active:
                    current_price = self.binance_client.get_current_price(SYMBOL)

                    if current_price is None:
                        time.sleep(self.intervalo)
                        continue

                    # Verifica stop loss
                    should_stop, loss_percent = self.risk_manager.check_stop_loss(current_price)
                    if should_stop:
                        self.logger.log_stop(
                            f"STOP LOSS -{STOP_LOSS_PERCENT}% | Preço: {current_price:.2f} USDT",
                            loss_percent
                        )
                        print(f"\n{'='*60}")
                        print(f"🛑 [MONITOR] STOP LOSS ACIONADO!")
                        print(f"Preço de entrada: {self.risk_manager.entry_price:.2f} USDT")
                        print(f"Preço atual: {current_price:.2f} USDT")
                        print(f"Perda: {loss_percent:.2f}%")
                        print(f"{'='*60}\n")
                        self.copy_trader_ref._executar_venda_monitor(current_price, motivo="Stop Loss")
                        self.risk_manager.clear_entry()
                        time.sleep(self.intervalo)
                        continue

                    # Verifica take profit
                    should_take, lucro_usdt = self.risk_manager.check_take_profit(current_price)
                    if should_take:
                        alvo = self.risk_manager.get_take_profit_usdt()
                        print(f"\n{'='*60}")
                        print(f"🎯 [MONITOR] TAKE PROFIT ATINGIDO!")
                        print(f"Alvo por operação: +{alvo:.2f} USDT (10% da meta diária)")
                        print(f"Lucro atual: +{lucro_usdt:.2f} USDT")
                        print(f"{'='*60}\n")
                        self.copy_trader_ref._executar_venda_monitor(current_price, motivo="Take Profit")
                        self.risk_manager.clear_entry()

            except Exception as e:
                print(f"❌ Erro no monitor: {e}")

            time.sleep(self.intervalo)


class CopyTrader:
    def __init__(self):
        self.binance_client = BinanceClientCliente()
        self.risk_manager = RiskManagerCliente(
            BANCA_INICIAL,
            STOP_LOSS_PERCENT,
            META_DIARIA_PERCENT,
            TAKE_PROFIT_META_PERCENT
        )
        self.logger = TradingLoggerCliente()
        self.signals_file = SIGNALS_FILE
        self.last_signal_index = -1
        self.ativo = COPY_TRADER_ATIVO

        # Correção ponto 3: quantidade como atributo da instância
        self.quantidade_percentual = QUANTIDADE_PERCENTUAL

        # Correção ponto 4: monitor em thread separada (passa self para executar venda)
        self.stop_loss_monitor = StopLossMonitor(
            self.binance_client,
            self.risk_manager,
            self.logger,
            copy_trader_ref=self,
            intervalo=5
        )

    def pausar(self):
        self.ativo = False
        print(f"\n⏸️  Copy Trader pausado para {CLIENTE_NOME}\n")

    def retomar(self):
        self.ativo = True
        print(f"\n▶️  Copy Trader retomado para {CLIENTE_NOME}\n")

    def ajustar_quantidade(self, percentual):
        # Correção ponto 3: atualiza atributo da instância
        self.quantidade_percentual = percentual
        print(f"\n📊 Quantidade ajustada para {percentual*100:.0f}% para {CLIENTE_NOME}\n")

    def ajustar_risco(self, stop_loss, meta_diaria):
        self.risk_manager.stop_loss_percent = stop_loss
        self.risk_manager.meta_diaria_percent = meta_diaria
        print(f"\n✅ Limites atualizados: SL={stop_loss}%, Meta diária={meta_diaria}%\n")

    def ler_sinais(self):
        try:
            with open(self.signals_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return []
        except Exception as e:
            print(f"❌ Erro ao ler sinais: {e}")
            return []

    def processar_sinais(self):
        if not self.ativo:
            return

        try:
            banca_atual = self.binance_client.get_asset_balance("USDT")
            self.risk_manager.atualizar_banca(banca_atual)

            # Correção ponto 2: pode_operar_hoje() agora existe
            if not self.risk_manager.pode_operar_hoje():
                ganho = self.risk_manager.get_ganho_atual()
                percentual = self.risk_manager.get_percentual_ganho()
                print(f"⏸️  META DIÁRIA ATINGIDA! Ganho: +{ganho:.2f} USDT (+{percentual:.2f}%)")
                print(f"Aguardando 00:01 para retomar operações...")
                return

            signals = self.ler_sinais()
            if not signals:
                return

            if len(signals) > self.last_signal_index + 1:
                novo_sinal = signals[-1]
                self.last_signal_index = len(signals) - 1

                alvo_op = self.risk_manager.get_take_profit_usdt()

                print(f"\n{'='*60}")
                print(f"📥 NOVO SINAL RECEBIDO DO TRADER")
                print(f"{'='*60}")
                print(f"Operação: {novo_sinal['operation_type']}")
                print(f"Símbolo: {novo_sinal['symbol']}")
                print(f"Quantidade (trader): {novo_sinal['quantity']:.8f}")
                print(f"Preço: {novo_sinal['price']:.2f} USDT")
                print(f"Stop Loss: {novo_sinal['price'] * 0.95:.2f} USDT (-5%)")
                print(f"Take Profit alvo: +{alvo_op:.2f} USDT (10% da meta)")
                print(f"{'='*60}\n")

                if novo_sinal['operation_type'] == 'BUY':
                    self._executar_compra(novo_sinal)
                elif novo_sinal['operation_type'] == 'SELL':
                    self._executar_venda(motivo="Sinal do trader (SELL)")

            # Exibe status da banca
            ganho = self.risk_manager.get_ganho_atual()
            percentual_ganho = self.risk_manager.get_percentual_ganho()
            meta = self.risk_manager.get_meta_diaria()
            alvo_op = self.risk_manager.get_take_profit_usdt()

            print(f"\n📊 STATUS DA BANCA ({CLIENTE_NOME}):")
            print(f"Banca inicial: {self.risk_manager.banca_inicial:.2f} USDT")
            print(f"Banca atual: {banca_atual:.2f} USDT")
            print(f"Ganho: {ganho:.2f} USDT ({percentual_ganho:.2f}%)")
            print(f"Meta diária: +{meta:.2f} USDT (+{META_DIARIA_PERCENT}%)")
            print(f"Alvo por operação: +{alvo_op:.2f} USDT (10% da meta)")
            print(f"Faltam: {meta - ganho:.2f} USDT para meta\n")

        except Exception as e:
            print(f"❌ Erro ao processar sinais: {e}")

    def _executar_compra(self, sinal):
        try:
            quantidade_trader = sinal['quantity']
            # Correção ponto 3: usa self.quantidade_percentual
            quantidade_cliente = quantidade_trader * self.quantidade_percentual
            quantidade_cliente = round(quantidade_cliente, 8)

            usdt_balance = self.binance_client.get_asset_balance("USDT")
            current_price = self.binance_client.get_current_price(SYMBOL)
            notional_needed = quantidade_cliente * current_price

            if usdt_balance < notional_needed:
                print(f"❌ Saldo insuficiente. Necessário: {notional_needed:.2f} USDT, Disponível: {usdt_balance:.2f} USDT")
                return

            order = self.binance_client.create_order(SYMBOL, SIDE_BUY, quantidade_cliente)

            if order:
                alvo_op = self.risk_manager.get_take_profit_usdt()
                self.logger.log_entry(
                    "BUY", SYMBOL, quantidade_cliente, current_price,
                    f"Copiando trader ({self.quantidade_percentual*100:.0f}%) | Alvo: +{alvo_op:.2f} USDT"
                )
                # Armazena quantidade para cálculo de take profit em USDT
                self.risk_manager.set_entry(current_price, quantidade_cliente)
                print(f"✅ Compra executada: {quantidade_cliente:.8f} {ASSET} @ {current_price:.2f} USDT")
                print(f"Take Profit alvo: +{alvo_op:.2f} USDT")
            else:
                print(f"❌ Erro ao executar compra")

        except Exception as e:
            print(f"❌ Erro ao executar compra: {e}")

    def _executar_venda(self, motivo="Sinal do trader"):
        try:
            quantity = self.binance_client.get_asset_balance(ASSET)

            if quantity <= 0:
                print(f"❌ Nenhuma quantidade disponível para vender")
                return

            symbol_info = self.binance_client.get_symbol_info(SYMBOL)
            if symbol_info:
                for f in symbol_info["filters"]:
                    if f["filterType"] == "LOT_SIZE":
                        step_size = float(f["stepSize"])
                        quantity = int(quantity / step_size) * step_size
                        quantity = round(quantity, 8)
                        break

            order = self.binance_client.create_order(SYMBOL, SIDE_SELL, quantity)

            if order:
                current_price = self.binance_client.get_current_price(SYMBOL)
                ganho_operacao = ((current_price - self.risk_manager.entry_price) / self.risk_manager.entry_price) * 100
                lucro_usdt = (current_price - self.risk_manager.entry_price) * quantity

                self.logger.log_entry(
                    "SELL", SYMBOL, quantity, current_price,
                    f"{motivo} | Ganho: +{ganho_operacao:.2f}% (+{lucro_usdt:.2f} USDT)"
                )
                self.risk_manager.clear_entry()
                print(f"✅ Venda executada: {quantity:.8f} {ASSET} @ {current_price:.2f} USDT")
                print(f"Ganho da operação: +{ganho_operacao:.2f}% (+{lucro_usdt:.2f} USDT)")
            else:
                print(f"❌ Erro ao executar venda")

        except Exception as e:
            print(f"❌ Erro ao executar venda: {e}")

    def _executar_venda_monitor(self, current_price, motivo="Monitor"):
        """Chamado pela thread do monitor para executar venda imediata"""
        try:
            quantity = self.binance_client.get_asset_balance(ASSET)

            if quantity <= 0:
                return

            symbol_info = self.binance_client.get_symbol_info(SYMBOL)
            if symbol_info:
                for f in symbol_info["filters"]:
                    if f["filterType"] == "LOT_SIZE":
                        step_size = float(f["stepSize"])
                        quantity = int(quantity / step_size) * step_size
                        quantity = round(quantity, 8)
                        break

            order = self.binance_client.create_order(SYMBOL, SIDE_SELL, quantity)

            if order:
                if self.risk_manager.entry_price:
                    ganho_operacao = ((current_price - self.risk_manager.entry_price) / self.risk_manager.entry_price) * 100
                    lucro_usdt = (current_price - self.risk_manager.entry_price) * quantity
                    self.logger.log_entry(
                        "SELL", SYMBOL, quantity, current_price,
                        f"{motivo} | Ganho: {ganho_operacao:.2f}% ({lucro_usdt:+.2f} USDT)"
                    )
                print(f"✅ [{motivo}] Venda executada: {quantity:.8f} {ASSET} @ {current_price:.2f} USDT")

        except Exception as e:
            print(f"❌ Erro na venda pelo monitor: {e}")

    def run_continuous(self):
        print("=" * 60)
        print("🤖 COPY TRADER INICIADO")
        print(f"Cliente: {CLIENTE_NOME}")
        print(f"Símbolo: {SYMBOL}")
        print(f"Banca inicial: {self.risk_manager.banca_inicial:.2f} USDT")
        print(f"Meta diária: +{META_DIARIA_PERCENT}% ({self.risk_manager.get_meta_diaria():.2f} USDT)")
        print(f"Alvo por operação: +{self.risk_manager.get_take_profit_usdt():.2f} USDT (10% da meta)")
        print(f"Stop Loss: -{STOP_LOSS_PERCENT}% do preço de entrada")
        print(f"Quantidade: {self.quantidade_percentual*100:.0f}% do trader")
        print("=" * 60 + "\n")

        # Correção ponto 4: inicia thread de monitoramento
        self.stop_loss_monitor.iniciar()

        running = True
        while running:
            try:
                self.processar_sinais()
                time.sleep(60)
            except KeyboardInterrupt:
                print("\n\n⏹️  Copy Trader parado pelo usuário.")
                self.stop_loss_monitor.parar()
                running = False
            except Exception as e:
                print(f"❌ Erro na execução contínua: {e}")
                time.sleep(60)