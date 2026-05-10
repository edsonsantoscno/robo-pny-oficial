# stop_loss_monitor.py
import threading
import time
from config_cliente import SYMBOL, STOP_LOSS_PERCENT

class StopLossMonitor:
    def __init__(self, binance_client, risk_manager, logger, intervalo=5):
        self.binance_client = binance_client
        self.risk_manager = risk_manager
        self.logger = logger
        self.intervalo = intervalo
        self._stop_event = threading.Event()
        self._thread = None

    def iniciar(self):
        """Inicia a thread de monitoramento"""
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._monitorar, daemon=True)
        self._thread.start()
        print(f"🔍 Monitor de Stop Loss iniciado (verificação a cada {self.intervalo}s)")

    def parar(self):
        """Para a thread de monitoramento"""
        self._stop_event.set()
        if self._thread:
            self._thread.join()
        print("🔍 Monitor de Stop Loss encerrado")

    def _monitorar(self):
        while not self._stop_event.is_set():
            try:
                if self.risk_manager.position_active:
                    current_price = self.binance_client.get_current_price(SYMBOL)

                    if current_price is None:
                        time.sleep(self.intervalo)
                        continue

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
                        self.risk_manager.clear_entry()

            except Exception as e:
                print(f"❌ Erro no monitor de stop loss: {e}")

            time.sleep(self.intervalo)