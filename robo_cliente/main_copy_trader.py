import asyncio
import os
import json
import logging
import websockets
import sys
import threading
from pathlib import Path
from client_cliente import BinanceClient
from order_manager_cliente import OrderManagerCliente
from risk_manager_cliente import RiskManagerCliente
from stop_loss_monitor import StopLossMonitor # type: ignore
from logger_cliente import TradingLoggerCliente
from config_cliente import WEBSOCKET_HOST, WEBSOCKET_PORT # type: ignore

file_lock = threading.Lock()
STATE_FILE = Path("/app/trading_state_cliente.json")
logger = TradingLoggerCliente()

class CopyTraderCliente:
    def __init__(self):
        """Inicializa a infraestrutura de rede externa do copiador."""
        self.binance_client = BinanceClient()
        self.order_manager = OrderManagerCliente(self.binance_client, logger)
        self.risk_manager = RiskManagerCliente(banca_inicial=100.0, logger=logger)
        
        self.stop_loss_monitor = StopLossMonitor(
            binance_client=self.binance_client,
            order_manager=self.order_manager,
            risk_manager=self.risk_manager,
            logger=logger,
            intervalo=5
        )
        
        # Conexão externa via criptografia SSL (wss) apontando para o subdomínio na porta 443
        if WEBSOCKET_PORT == 443:
            self.websocket_url = f"wss://{WEBSOCKET_HOST}/?role=client"
        else:
            self.websocket_url = f"ws://{WEBSOCKET_HOST}:{WEBSOCKET_PORT}/?role=client"
            
        self.running = True

    def checar_se_pode_copiar(self):
        with file_lock:  
            try:
                if STATE_FILE.exists():
                    with open(STATE_FILE, 'r', encoding='utf-8') as f:
                        state = json.load(f)
                    return state.get("bot_active", True) and self.risk_manager.pode_operar_hoje()
                return True
            except Exception as e:
                logger.log_error(f"Erro ao validar travas: {e}")
                return True

    async def processar_sinal(self, sinal_bruto):
        try:
            sinal = json.loads(sinal_bruto)
            operacao = sinal.get("operation_type") or sinal.get("action")
            symbol = sinal.get("symbol")
            if not operacao or not symbol: return

            logger.log_info(f"📡 Sinal recebido via WebSocket: {operacao} | {symbol}")
            if not self.checar_se_pode_copiar(): return

            if operacao == "BUY" and not self.risk_manager.position_active:
                lote_percentual = 1.0
                calc = self.order_manager.calculate_quantity(symbol, quantity_percent=lote_percentual)
                if calc and self.order_manager.validate_order(symbol, "BUY", calc["quantity"]):
                    order = self.binance_client.create_order(symbol, "BUY", calc["quantity"])
                    if order:
                        self.risk_manager.set_entry(symbol, calc["price"], calc["quantity"], sl=sinal.get("stop_loss"), tp=sinal.get("take_profit"))
            elif operacao == "SELL" and self.risk_manager.position_active:
                if self.risk_manager.current_symbol == symbol:
                    qty = self.risk_manager.entry_quantity
                    if qty and self.order_manager.validate_order(symbol, "SELL", qty):
                        order = self.binance_client.create_order(symbol, "SELL", qty)
                        if order: self.risk_manager.clear_position()
        except Exception as e:
            logger.log_error(f"Erro ao processar sinal: {e}")

    async def escutar_sinais_mestre(self):
        while self.running:
            try:
                logger.log_info(f"🔌 Conectando ao subdomínio do SaaS em {self.websocket_url}...")
                async with websockets.connect(self.websocket_url, ping_interval=20, ping_timeout=20) as websocket:
                    logger.log_info("✅ CONECTADO AO SUBDOMÍNIO! Ouvindo canal de sinais...")
                    self.stop_loss_monitor.iniciar()
                    async for message in websocket:
                        await self.processar_sinal(message)
            except Exception as network_err:
                logger.log_warning(f"⚠ Queda ou indisponibilidade no subdomínio: {network_err}")
                self.stop_loss_monitor.parar()
                await asyncio.sleep(10)

    def start(self):
        try:
            asyncio.run(self.escutar_sinais_mestre())
        except KeyboardInterrupt:
            self.stop_loss_monitor.parar()

if __name__ == "__main__":
    bot_cliente = CopyTraderCliente()
    bot_cliente.start()
