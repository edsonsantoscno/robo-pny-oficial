import asyncio
import os
import json
import logging
import websockets
import sys
from pathlib import Path
from client_cliente import BinanceClient
from order_manager_cliente import OrderManagerCliente
from risk_manager_cliente import RiskManagerCliente
from stop_loss_monitor import StopLossMonitor # type: ignore
from logger_cliente import TradingLoggerCliente # Importação do logger customizado
from config_cliente import WEBSOCKET_HOST, WEBSOCKET_PORT # type: ignore

# Garante o isolamento do arquivo de estado dinâmico compartilhado
BASE_DIR = Path(__file__).parent
STATE_FILE = BASE_DIR / "data" / "trading_state_cliente.json" # Caminho corrigido para usar a pasta 'data'
STATE_FILE = BASE_DIR / "trading_state_cliente.json"

# Inicializa o logger customizado
logger = TradingLoggerCliente()

class CopyTraderCliente:
    def __init__(self):
        # Inicializa as conexões com as classes auditadas e protegidas
        self.binance_client = BinanceClient()
        self.order_manager = OrderManagerCliente(self.binance_client, logger) # Passa o logger

        # Carrega a banca inicial real do cliente direto da corretora para evitar resets fictícios
        banca_inicial_real = float(self.binance_client.get_asset_balance("USDT"))
        self.risk_manager = RiskManagerCliente(banca_inicial=banca_inicial_real, logger=logger) # Passa o logger

        # Inicializa o monitor de Stop Loss paralelo que protegemos contra falhas de moedas
        self.stop_loss_monitor = StopLossMonitor(
            binance_client=self.binance_client,
            order_manager=self.order_manager,
            risk_manager=self.risk_manager,
            logger=logger, # Passa o logger correto
            intervalo=5
        )

        # Endereço de rede interno do container do WebSocket Mestre
        self.websocket_url = f"ws://{WEBSOCKET_HOST}:{WEBSOCKET_PORT}"
        self.running = True

    def checar_se_pode_copiar(self):
        """Lê o arquivo de estado compartilhado com o Dashboard do cliente"""
        try:
            # Garante que o diretório 'data' exista antes de tentar ler o STATE_FILE
            STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            if STATE_FILE.exists():
                with open(STATE_FILE, 'r') as f:
                    state = json.load(f)
                # Verifica a verificação de reset diário e se o bot mestre está ativo
                return state.get("bot_active", True) and self.risk_manager.pode_operar_hoje()
        except Exception as e:
            logger.log_error(f"Erro ao validar travas de execução do cliente: {e}")
        return True

    async def processar_sinal(self, sinal_bruto):
        """Processa e replica a ordem enviada pelo robô mestre em tempo real"""
        try:
            sinal = json.loads(sinal_bruto)
            operacao = sinal.get("operation_type")
            symbol = sinal.get("symbol")
            preco_mestre = float(sinal.get("price", 0))

            logger.log_info(f"📡 Sinal recebido via WebSocket: {operacao} | {symbol} @ ${preco_mestre}")

            if not self.checar_se_pode_copiar():
                logger.log_info("💤 Operação descartada: Painel do cliente inativo ou Meta Diária atingida.")
                return

            # --- CASO SEJA UM SINAL DE COMPRA (BUY) ---
            if operacao == "BUY" and not self.risk_manager.position_active:
                logger.log_info(f"🛒 Calculando tamanho de lote proporcional para entrar em {symbol}...")

                # Lê o tamanho do lote (%) configurado na interface de visualização do cliente
                try:
                    # Garante que o diretório 'data' exista antes de tentar ler o STATE_FILE
                    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
                    with open(STATE_FILE, 'r') as f:
                        state = json.load(f)
                    lote_percentual = float(state.get("quantidade_percentual", 100)) / 100.0
                except Exception:
                    lote_percentual = 1.0 # Fallback padrão de 100% da banca livre se o JSON sumir
                    logger.log_warning("⚠️ Não foi possível ler 'quantidade_percentual' do STATE_FILE. Usando 100% da banca livre.")


                # Realiza o cálculo de lote proporcional blindado contra dízimas da Binance
                calc = self.order_manager.calculate_quantity(symbol, quantity_percent=lote_percentual)

                if calc and self.order_manager.validate_order(symbol, "BUY", calc["quantity"]):
                    # Executa a compra real na conta do cliente
                    order = self.binance_client.create_order(symbol, "BUY", calc["quantity"])
                    if order:
                        # Extrai os parâmetros dinâmicos de Stop e Take enviados no sinal do mestre
                        sl_mestre = sinal.get("stop_loss")
                        tp_mestre = sinal.get("take_profit")

                        # Salva a entrada na memória e no JSON persistente para o Dashboard ler
                        self.risk_manager.set_entry(symbol, calc["price"], calc["quantity"], sl=sl_mestre, tp=tp_mestre)
                        logger.log_info(f"✅ COMPRA EXECUTADA COM SUCESSO: {calc['quantity']} {symbol}")
                    else:
                        logger.log_error(f"❌ Falha ao executar ordem de compra para {symbol} na Binance.")


            # --- CASO SEJA UM SINAL DE VENDA (SELL) ---
            elif operacao == "SELL" and self.risk_manager.position_active:
                if self.risk_manager.current_symbol == symbol:
                    logger.log_info(f"🚨 Sinal de fechamento do Mestre recebido para {symbol}. Liquidando...")
                    qty = self.risk_manager.entry_quantity

                    if qty and self.order_manager.validate_order(symbol, "SELL", qty):
                        # Executa a venda real na conta do cliente
                        order = self.binance_client.create_order(symbol, "SELL", qty)
                        if order:
                            self.risk_manager.clear_position()
                            logger.log_info(f"✅ POSIÇÃO ENCERRADA COM SUCESSO EM {symbol} VIA CÓPIA MESTRE.")
                        else:
                            logger.log_error(f"❌ Falha ao executar ordem de venda para {symbol} na Binance.")
                else:
                    logger.log_warning(f"Sinal de venda ignorado: Cliente operando {self.risk_manager.current_symbol}, mestre mandou fechar {symbol}.")

        except Exception as e:
            logger.log_error(f"Erro crítico ao processar e replicar sinal: {e}")

    async def escutar_sinais_mestre(self):
        """Mantém a conexão estável via WebSocket com reconexão automática em caso de queda de rede"""
        while self.running:
            try:
                logger.log_info(f"🔌 Conectando ao canal de transmissão do Mestre em {self.websocket_url}...")
                async with websockets.connect(self.websocket_url, ping_interval=20, ping_timeout=20) as websocket:
                    logger.log_info("✅ CONECTADO AO MESTRE! Ouvindo canal de sinais em tempo real...")

                    # Inicia o monitor paralelo de Stop Loss físico na conta
                    self.stop_loss_monitor.iniciar()

                    async for message in websocket:
                        await self.processar_sinal(message)

            except (websockets.exceptions.ConnectionClosed, OSError) as network_err:
                logger.log_warning(f"⚠️ Conexão perdida com o servidor mestre: {network_err}")
                self.stop_loss_monitor.parar()
                logger.log_info("⏳ Aguardando 10 segundos antes de tentar reconectar...")
                await asyncio.sleep(10)
            except Exception as e:
                logger.log_error(f"Erro inesperado na malha de rede do cliente: {e}")
                await asyncio.sleep(5)

    def start(self):
        """Inicia a orquestração do loop assíncrono principal"""
        try:
            asyncio.run(self.escutar_sinais_mestre())
        except KeyboardInterrupt:
            logger.log_info("⏹️ Copy Trader desativado pelo operador.")
            self.stop_loss_monitor.parar()

if __name__ == "__main__":
    bot_cliente = CopyTraderCliente()
    bot_cliente.start()
