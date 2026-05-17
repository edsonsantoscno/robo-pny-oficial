import asyncio
import os
import json
import logging
import time
import threading
import websockets
from pathlib import Path
from client import BinanceClient # type: ignore
from order_manager_cliente import OrderManagerCliente
from risk_manager_cliente import RiskManagerCliente
from logger_cliente import TradingLoggerCliente
from config import LOG_FILE, WEBSOCKET_HOST, WEBSOCKET_PORT # type: ignore

# Configuração de Logs para leitura do Dashboard do Cliente
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()]
)
logger = logging.getLogger("CopyTraderCliente")

# Garante o isolamento do arquivo de estado dinâmico compartilhado
BASE_DIR = Path(__file__).parent
STATE_FILE = BASE_DIR / "trading_state_cliente.json"


class StopLossMonitor:
    """
    Thread paralela de alta velocidade que verifica stop loss e take profit
    de forma isolada do ciclo de rede do WebSocket.
    """
    def __init__(self, binance_client, order_manager, risk_manager, logger_ref, intervalo=5):
        self.binance_client = binance_client
        self.order_manager = order_manager
        self.risk_manager = risk_manager
        self.logger = logger_ref
        self.intervalo = intervalo
        self._stop_event = threading.Event()
        self._thread = None

    def iniciar(self):
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._monitorar, daemon=True)
        self._thread.start()
        logger.info(f"🔍 Monitor de Stop Loss iniciado (verificação a cada {self.intervalo}s)")

    def parar(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join()
        logger.info("🔍 Monitor de Stop Loss encerrado")

    def _monitorar(self):
        while not self._stop_event.is_set():
            try:
                if self.risk_manager.position_active and self.risk_manager.current_symbol:
                    symbol = self.risk_manager.current_symbol
                    current_price = self.binance_client.get_current_price(symbol)

                    if current_price is None:
                        time.sleep(self.intervalo)
                        continue

                    # Validação estrita de Stop Loss
                    should_stop, loss_percent = self.risk_manager.check_stop_loss(current_price)
                    if should_stop:
                        print(f"\n{'='*60}\n🛑 [MONITOR CLIENTE] STOP LOSS ACIONADO EM {symbol}!\n{'='*60}")
                        self._executar_saida_emergencia(symbol, current_price, f"STOP LOSS -{loss_percent:.2f}%")
                        continue

                    # Validação estrita de Take Profit
                    should_take, lucro_usdt = self.risk_manager.check_take_profit(current_price)
                    if should_take:
                        print(f"\n{'='*60}\n🎯 [MONITOR CLIENTE] TAKE PROFIT ATINGIDO EM {symbol}!\n{'='*60}")
                        self._executar_saida_emergencia(symbol, current_price, f"TAKE PROFIT +${lucro_usdt:.2f}")

            except Exception as e:
                logger.error(f"Erro no monitor de risco: {e}")

            time.sleep(self.intervalo)

    def _executar_saida_emergencia(self, symbol, price, motivo):
        qty = self.risk_manager.entry_quantity
        if qty and self.order_manager.validate_order(symbol, "SELL", qty):
            order = self.binance_client.create_order(symbol, "SELL", qty)
            if order:
                self.logger.log_stop(f"Liquidação de emergência em {symbol} por {motivo}", 0.0)
                self.risk_manager.clear_position()


class CopyTraderCliente:
    def __init__(self):
        self.binance_client = BinanceClient()
        self.order_manager = OrderManagerCliente(self.binance_client)
        
        banca_inicial_real = float(self.binance_client.get_asset_balance("USDT"))
        self.risk_manager = RiskManagerCliente(banca_inicial=banca_inicial_real)
        self.logger = TradingLoggerCliente()
        
        self.stop_loss_monitor = StopLossMonitor(
            self.binance_client, self.order_manager, self.risk_manager, self.logger, intervalo=5
        )
        self.websocket_url = f"ws://{WEBSOCKET_HOST}:{WEBSOCKET_PORT}"
        self.running = True

    def checar_se_pode_copiar(self):
        try:
            if STATE_FILE.exists():
                with open(STATE_FILE, 'r') as f:
                    state = json.load(f)
                return state.get("bot_active", True) and self.risk_manager.pode_operar_hoje()
        except Exception as e:
            logger.error(f"Erro nas travas de cópia: {e}")
        return True

    async def processar_sinal(self, sinal_bruto):
        try:
            sinal = json.loads(sinal_bruto)
            operacao = sinal.get("operation_type")
            symbol = sinal.get("symbol")
            preco_mestre = float(sinal.get("price", 0))
            
            logger.info(f"📡 Sinal recebido via WebSocket: {operacao} | {symbol} @ ${preco_mestre}")

            if not self.checar_se_pode_copiar():
                logger.info("💤 Operação ignorada: Painel inativo ou Meta Diária batida.")
                return

            # --- EXECUÇÃO DE COMPRA PROPORCIONAL ---
            if operacao == "BUY" and not self.risk_manager.position_active:
                try:
                    with open(STATE_FILE, 'r') as f:
                        state = json.load(f)
                    lote_percentual = float(state.get("quantidade_percentual", 100)) / 100.0
                except Exception:
                    lote_percentual = 1.0

                calc = self.order_manager.calculate_quantity(symbol, quantity_percent=lote_percentual)
                
                if calc and self.order_manager.validate_order(symbol, "BUY", calc["quantity"]):
                    order = self.binance_client.create_order(symbol, "BUY", calc["quantity"])
                    if order:
                        self.risk_manager.set_entry(symbol, calc["price"], calc["quantity"], sl=4.0, tp=2.0)
                        self.logger.log_entry("BUY", symbol, calc["quantity"], calc["price"], calc["notional"], "Cópia Mestre")
                
            # --- EXECUÇÃO DE VENDA SINCRONIZADA ---
            elif operacao == "SELL" and self.risk_manager.position_active:
                if self.risk_manager.current_symbol == symbol:
                    qty = self.risk_manager.entry_quantity
                    if qty and self.order_manager.validate_order(symbol, "SELL", qty):
                        order = self.binance_client.create_order(symbol, "SELL", qty)
                        if order:
                            self.logger.log_entry("SELL", symbol, qty, preco_mestre, qty*preco_mestre, "Sinal Mestre (SELL)")
                            self.risk_manager.clear_position()

        except Exception as e:
            logger.error(f"Erro ao processar sinal do WebSocket: {e}")

    async def escutar_sinais_mestre(self):
        while self.running:
            try:
                logger.info(f"🔌 Conectando ao WebSocket mestre em {self.websocket_url}...")
                async with websockets.connect(self.websocket_url, ping_interval=20, ping_timeout=20) as websocket:
                    logger.info("✅ Conexão ativa! Ouvindo sinais de trading...")
                    self.stop_loss_monitor.iniciar()

                    async for message in websocket:
                        await self.processar_sinal(message)
                        
            except (websockets.exceptions.ConnectionClosed, OSError):
                logger.warning("⚠️ Conexão perdida com o servidor mestre.")
                self.stop_loss_monitor.parar()
                await asyncio.sleep(10)

    def start(self):
        try:
            asyncio.run(self.scutar_sinais_mestre())
        except KeyboardInterrupt:
            self.stop_loss_monitor.parar()


if __name__ == "__main__":
    bot_cliente = CopyTraderCliente()
    bot_cliente.start()
