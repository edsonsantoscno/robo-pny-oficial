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

# Mecanismo de Trava Global (Lock) e caminho físico unificado com o docker-compose.yml
file_lock = threading.Lock()
STATE_FILE = Path("/app/trading_state_cliente.json")

# Inicializa o logger customizado do ecossistema cliente
logger = TradingLoggerCliente()

class CopyTraderCliente:
    def __init__(self):
        """Inicializa a infraestrutura base de escuta do ecossistema copiador."""
        self.binance_client = BinanceClient()
        self.order_manager = OrderManagerCliente(self.binance_client, logger)
        
        # Inicializa o risk manager com fallback seguro de banca inicial para evitar encerramento prematuro
        self.risk_manager = RiskManagerCliente(banca_inicial=100.0, logger=logger)
        
        # Inicializa o monitor paralelo de posições abertas
        self.stop_loss_monitor = StopLossMonitor(
            binance_client=self.binance_client,
            order_manager=self.order_manager,
            risk_manager=self.risk_manager,
            logger=logger,
            intervalo=5
        )
        
        # Conecta no cluster interno através do barramento do websocket-server
        self.websocket_url = f"ws://{WEBSOCKET_HOST}:{WEBSOCKET_PORT}?role=client"
        self.running = True

    def checar_se_pode_copiar(self):
        """Lê o arquivo de estado compartilhado com o Dashboard de forma thread-safe."""
        with file_lock:  
            try:
                STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
                if STATE_FILE.exists():
                    with open(STATE_FILE, 'r', encoding='utf-8') as f:
                        state = json.load(f)
                    return state.get("bot_active", True) and self.risk_manager.pode_operar_hoje()
                return True
            except Exception as e:
                logger.log_error(f"Erro ao validar travas de execução do cliente: {e}")
                return True

    async def processar_sinal(self, sinal_bruto):
        """Recebe as ordens de mercado disparadas pelo mestre e encaminha para cópia."""
        try:
            sinal = json.loads(sinal_bruto)
            operacao = sinal.get("operation_type") or sinal.get("action")
            symbol = sinal.get("symbol")
            preco_mestre = float(sinal.get("price", 0))
            
            if not operacao or not symbol:
                return

            logger.log_info(f"📡 Sinal recebido via WebSocket: {operacao} | {symbol} @ ${preco_mestre}")

            if not self.checar_se_pode_copiar():
                logger.log_info("💤 Operação descartada: Painel do cliente inativo ou Meta Diária atingida.")
                return

            # --- EXECUÇÃO DE COMPRA PROPORCIONAL (BUY) ---
            if operacao == "BUY" and not self.risk_manager.position_active:
                lote_percentual = 1.0
                with file_lock:  
                    try:
                        if STATE_FILE.exists():
                            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                                state = json.load(f)
                            lote_percentual = float(state.get("quantidade_percentual", 100)) / 100.0
                    except Exception:
                        lote_percentual = 1.0

                # Recarrega o saldo físico em tempo real antes de fracionar os lotes
                banca_real = float(self.binance_client.get_asset_balance("USDT"))
                if banca_real > 0:
                    self.risk_manager.banca_inicial = banca_real
                    self.risk_manager.banca_atual = banca_real

                calc = self.order_manager.calculate_quantity(symbol, quantity_percent=lote_percentual)
                if calc and self.order_manager.validate_order(symbol, "BUY", calc["quantity"]):
                    order = self.binance_client.create_order(symbol, "BUY", calc["quantity"])
                    if order:
                        sl_mestre = sinal.get("stop_loss")
                        tp_mestre = sinal.get("take_profit")
                        self.risk_manager.set_entry(symbol, calc["price"], calc["quantity"], sl=sl_mestre, tp=tp_mestre)
                        logger.log_info(f"✅ COMPRA EXECUTADA COM SUCESSO: {calc['quantity']} {symbol}")
                    else:
                        logger.log_error(f"❌ Falha ao executar ordem de compra para {symbol} na Binance.")

            # --- EXECUÇÃO DE LIQUIDAÇÃO DE OPERAÇÃO (SELL) ---
            elif operacao == "SELL" and self.risk_manager.position_active:
                if self.risk_manager.current_symbol == symbol:
                    qty = self.risk_manager.entry_quantity
                    if qty and self.order_manager.validate_order(symbol, "SELL", qty):
                        order = self.binance_client.create_order(symbol, "SELL", qty)
                        if order:
                            self.risk_manager.clear_position()
                            logger.log_info(f"✅ POSIÇÃO ENCERRADA COM SUCESSO EM {symbol} VIA CÓPIA MESTRE.")
                        else:
                            logger.log_error(f"❌ Falha ao executar ordem de venda para {symbol} na Binance.")
        except Exception as e:
            logger.log_error(f"Erro crítico ao processar e replicar sinal: {e}")

    async def escutar_sinais_mestre(self):
        """Mantém a conexão persistente e ativa ouvindo as transmissões do barramento central."""
        while self.running:
            try:
                logger.log_info(f"🔌 Conectando ao canal de transmissão do Mestre em {self.websocket_url}...")
                async with websockets.connect(self.websocket_url, ping_interval=20, ping_timeout=20) as websocket:
                    logger.log_info("✅ CONECTADO AO MESTRE! Ouvindo canal de sinais em tempo real...")
                    
                    # Inicializa o monitor em paralelo de travas financeiras de segurança
                    self.stop_loss_monitor.iniciar()
                    
                    async for message in websocket:
                        await self.processar_sinal(message)
            except (websockets.exceptions.ConnectionClosed, OSError) as network_err:
                logger.log_warning(f"⚠ Conexão indisponível ou perdida com o servidor mestre: {network_err}")
                self.stop_loss_monitor.parar()
                logger.log_info("⏳ Aguardando 10 segundos antes de tentar reconectar...")
                await asyncio.sleep(10)
            except Exception as e:
                logger.log_error(f"Erro imprevisto na malha de transmissão do cliente: {e}")
                await asyncio.sleep(5)

    def start(self):
        """Orquestra e aciona o loop eterno assíncrono."""
        try:
            asyncio.run(self.escutar_sinais_mestre())
        except KeyboardInterrupt:
            logger.log_info("⏹ Copy Trader desativado pelo operador.")
            self.stop_loss_monitor.parar()

if __name__ == "__main__":
    bot_cliente = CopyTraderCliente()
    bot_cliente.start()
