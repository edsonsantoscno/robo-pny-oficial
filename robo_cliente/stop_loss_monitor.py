import threading
import time
from logger_cliente import TradingLoggerCliente

class StopLossMonitor:
    def __init__(self, binance_client, order_manager, risk_manager, logger: TradingLoggerCliente, intervalo=5):
        self.binance_client = binance_client
        self.order_manager = order_manager
        self.risk_manager = risk_manager
        self.logger = logger
        self.intervalo = intervalo
        self._stop_event = threading.Event()
        self._thread = None

    def iniciar(self):
        """Inicia a thread de monitoramento em segundo plano de forma assíncrona."""
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._monitorar, daemon=True)
        self._thread.start()
        self.logger.log_info(f"🔍 [CLIENTE] Monitor de Stop Loss ativo (Verificando a cada {self.intervalo}s)")

    def parar(self):
        """Para a thread de monitoramento de forma segura."""
        self._stop_event.set()
        if self._thread:
            self._thread.join()
        self.logger.log_info("🔍 [CLIENTE] Monitor de Stop Loss encerrado")

    def _monitorar(self):
        """Loop contínuo thread-safe de escaneamento de posições abertas na subconta."""
        while not self._stop_event.is_set():
            try:
                if self.risk_manager.position_active and self.risk_manager.current_symbol:
                    symbol = self.risk_manager.current_symbol
                    current_price = self.binance_client.get_current_price(symbol)
                    
                    if current_price is None:
                        # CORREÇÃO #1: Garante a pausa para evitar loop infinito e estouro de CPU na VPS
                        time.sleep(self.intervalo)
                        continue

                    should_stop, loss_percent = self.risk_manager.check_stop_loss(current_price)
                    if should_stop:
                        self.logger.log_warning(f"\n{'='*60}")
                        self.logger.log_warning(f"🛑 [MONITOR CLIENTE] STOP LOSS ACIONADO PARA {symbol}!")
                        self.logger.log_warning(f"Preço de entrada: {self.risk_manager.entry_price:.4f} USDT")
                        self.logger.log_warning(f"Preço atual: {current_price:.4f} USDT")
                        self.logger.log_warning(f"Perda calculada: {loss_percent:.2f}%")
                        self.logger.log_warning(f{'='*60}\n")

                        # EXECUÇÃO DE ORDEM REAL NA BINANCE DO CLIENTE
                        qty = self.risk_manager.entry_quantity
                        if qty and self.order_manager.validate_order(symbol, "SELL", qty):
                            order = self.binance_client.create_order(symbol, "SELL", qty)
                            if order:
                                # CORREÇÃO #2: Sincronizado com os métodos existentes na biblioteca logger_cliente.py
                                self.logger.log_warning(
                                    f"🛑 STOP LOSS EXECUTADO EM {symbol} | Preço: {current_price:.4f} USDT | Perda: {loss_percent:.2f}%"
                                )
                                # Limpa o estado dinâmico local e grava no JSON do Dashboard
                                self.risk_manager.clear_position()
                            else:
                                self.logger.log_error(f"❌ [ERRO CRÍTICO] Falha ao executar venda de Stop Loss para {symbol} na Binance.")
                        else:
                            self.logger.log_error(f"❌ [ERRO DE VALIDAÇÃO] Quantidade inválida para executar Stop Loss em {symbol}.")
            except Exception as e:
                self.logger.log_error(f"❌ Erro operacional no monitor de stop loss do cliente: {e}")
            
            # Pausa padrão obrigatória ao final de cada ciclo de verificação
            time.sleep(self.intervalo)
