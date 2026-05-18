import threading
import time
# Importação corrigida para o logger do cliente
from logger_cliente import TradingLoggerCliente

class StopLossMonitor:
    def __init__(self, binance_client, order_manager, risk_manager, logger: TradingLoggerCliente, intervalo=5):
        self.binance_client = binance_client
        self.order_manager = order_manager # Injetado para executar a venda real
        self.risk_manager = risk_manager
        self.logger = logger # Agora tipado para TradingLoggerCliente
        self.intervalo = intervalo
        self._stop_event = threading.Event()
        self._thread = None

    def iniciar(self):
        """Inicia a thread de monitoramento em segundo plano de forma assíncrona"""
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._monitorar, daemon=True)
        self._thread.start()
        print(f"🔍 [CLIENTE] Monitor de Stop Loss ativo (Verificando a cada {self.intervalo}s)")

    def parar(self):
        """Para a thread de monitoramento de forma segura"""
        self._stop_event.set()
        if self._thread:
            self._thread.join()
        print("🔍 [CLIENTE] Monitor de Stop Loss encerrado")

    def _monitorar(self):
        while not self._stop_event.is_set():
            try:
                # Monitora dinamicamente as informações caso haja posição aberta na subconta
                if self.risk_manager.position_active and self.risk_manager.current_symbol:

                    # CORREÇÃO CRÍTICA: Captura o símbolo real que o cliente está operando no momento
                    symbol = self.risk_manager.current_symbol
                    current_price = self.binance_client.get_current_price(symbol)

                    if current_price is None:
                        time.sleep(self.intervalo)
                        continue

                    should_stop, loss_percent = self.risk_manager.check_stop_loss(current_price)

                    if should_stop:
                        print(f"\n{'='*60}")
                        print(f"🛑 [MONITOR CLIENTE] STOP LOSS ACIONADO PARA {symbol}!")
                        print(f"Preço de entrada: {self.risk_manager.entry_price:.4f} USDT")
                        print(f"Preço atual: {current_price:.4f} USDT")
                        print(f"Perda calculada: {loss_percent:.2f}%")
                        print(f"{'='*60}\n")

                        # EXECUÇÃO DE ORDEM REAL NA BINANCE DO CLIENTE
                        qty = self.risk_manager.entry_quantity
                        if qty and self.order_manager.validate_order(symbol, "SELL", qty):
                            order = self.binance_client.create_order(symbol, "SELL", qty)
                            if order:
                                self.logger.log_stop(
                                    f"STOP LOSS EXECUTADO EM {symbol} | Preço: {current_price:.4f} USDT",
                                    loss_percent
                                )
                                # Limpa o estado apenas após a confirmação de venda bem-sucedida
                                self.risk_manager.clear_position()
                            else:
                                print(f"❌ [ERRO CRÍTICO] Falha ao executar venda de Stop Loss para {symbol} na Binance.")
                        else:
                            print(f"❌ [ERRO DE VALIDAÇÃO] Quantidade inválida para executar Stop Loss em {symbol}.")

            except Exception as e:
                print(f"❌ Erro operacional no monitor de stop loss do cliente: {e}")

            time.sleep(self.intervalo)
