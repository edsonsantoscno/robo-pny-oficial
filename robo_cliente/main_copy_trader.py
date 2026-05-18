import asyncio
import os
import json
import logging
import websockets
import sys
from pathlib import Path
# Importação corrigida para o BinanceClient do cliente
from client_cliente import BinanceClient # type: ignore
from order_manager_cliente import OrderManagerCliente
from risk_manager_cliente import RiskManagerCliente
from stop_loss_monitor import StopLossMonitor # type: ignore
# Importação corrigida para o logger do cliente
from logger_cliente import TradingLoggerCliente
# Importação corrigida para o config_cliente
from config_cliente import WEBSOCKET_HOST, WEBSOCKET_PORT # type: ignore

# Garante o isolamento do arquivo de estado dinâmico compartilhado
# Ajustado para o novo volume mapeado: /app/robo_cliente/data/
BASE_DIR = Path(__file__).parent
STATE_FILE = BASE_DIR / "data" / "trading_state_cliente.json" # <-- CORREÇÃO AQUI

# Configuração robusta de logs e registros locais para o terminal do Dashboard ler
# O logger agora é uma instância de TradingLoggerCliente
# O logging.basicConfig será substituído pelo logger_cliente
# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
#     handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()]
# )
# logger = logging.getLogger("CopyTraderCliente")

class CopyTraderCliente:
    def __init__(self):
        # Inicializa o logger do cliente
        self.logger = TradingLoggerCliente() # <-- CORREÇÃO AQUI: Instancia o logger

        # Inicializa as conexões com as classes auditadas e protegidas
        self.binance_client = BinanceClient(logger=self.logger) # <-- CORREÇÃO AQUI: Passa o logger
        self.order_manager = OrderManagerCliente(self.binance_client)

        # Carrega a banca inicial real do cliente direto da corretora para evitar resets fictícios
        banca_inicial_real = float(self.binance_client.get_asset_balance("USDT"))
        self.risk_manager = RiskManagerCliente(banca_inicial=banca_inicial_real)

        # Inicializa o monitor de Stop Loss paralelo que protegemos contra falhas de moedas
        self.stop_loss_monitor = StopLossMonitor(
            binance_client=self.binance_client,
            order_manager=self.order_manager,
            risk_manager=self.risk_manager,
            logger=self.logger, # <-- CORREÇÃO AQUI: Passa o logger correto
            intervalo=5
        )

        # Endereço de rede interno do container do WebSocket Mestre
        self.websocket_url = f"ws://{WEBSOCKET_HOST}:{WEBSOCKET_PORT}"
        self.running = True

    def checar_se_pode_copiar(self):
        """Lê o arquivo de estado compartilhado com o Dashboard do cliente"""
        try:
            if STATE_FILE.exists():
                with open(STATE_FILE, 'r') as f:
                    state = json.load(f)
                # Verifica a verificação de reset diário e se o bot mestre está ativo
                # Adicionado 'bot_active' do estado do cliente para controle via dashboard
                return state.get("bot_active", True) and self.risk_manager.pode_operar_hoje()
        except Exception as e:
            self.logger.error(f"Erro ao validar travas de execução do cliente: {e}") # <-- CORREÇÃO AQUI
        return True

    async def processar_sinal(self, sinal_bruto):
        """Processa e replica a ordem enviada pelo robô mestre em tempo real"""
        try:
            sinal = json.loads(sinal_bruto)
            operacao = sinal.get("operation_type")
            symbol = sinal.get("symbol")
            preco_mestre = float(sinal.get("price", 0))

            self.logger.info(f"📡 Sinal recebido via WebSocket: {operacao} | {symbol} @ ${preco_mestre}") # <-- CORREÇÃO AQUI

            if not self.checar_se_pode_copiar():
                self.logger.info("💤 Operação descartada: Painel do cliente inativo ou Meta Diária atingida.") # <-- CORREÇÃO AQUI
                return

            # --- CASO SEJA UM SINAL DE COMPRA (BUY) ---
            if operacao == "BUY" and not self.risk_manager.position_active:
                self.logger.info(f"🛒 Calculando tamanho de lote proporcional para entrar em {symbol}...") # <-- CORREÇÃO AQUI

                # Lê o tamanho do lote (%) configurado na interface de visualização do cliente
                try:
                    # Garante que o diretório exista antes de tentar ler o arquivo
                    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
                    with open(STATE_FILE, 'r') as f:
                        state = json.load(f)
                    lote_percentual = float(state.get("quantidade_percentual", 100)) / 100.0
                except Exception:
                    lote_percentual = 1.0 # Fallback padrão de 100% da banca livre se o JSON sumir

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
                        self.logger.log_entry("BUY", symbol, calc["quantity"], calc["price"], "Cópia Mestre") # <-- CORREÇÃO AQUI

            # --- CASO SEJA UM SINAL DE VENDA (SELL) ---
            elif operacao == "SELL" and self.risk_manager.position_active:
                if self.risk_manager.current_symbol == symbol:
                    self.logger.info(f"🚨 Sinal de fechamento do Mestre recebido para {symbol}. Liquidando...") # <-- CORREÇÃO AQUI
                    qty = self.risk_manager.entry_quantity

                    if qty and self.order_manager.validate_order(symbol, "SELL", qty):
                        # Executa a venda real na conta do cliente
                        order = self.binance_client.create_order(symbol, "SELL", qty)
                        if order:
                            self.risk_manager.clear_position()
                            self.logger.info(f"✅ POSIÇÃO ENCERRADA COM SUCESSO EM {symbol} VIA CÓPIA MESTRE.") # <-- CORREÇÃO AQUI
                else:
                    self.logger.warning(f"Sinal de venda ignorado: Cliente operando {self.risk_manager.current_symbol}, mestre mandou fechar {symbol}.") # <-- CORREÇÃO AQUI

        except Exception as e:
            self.logger.error(f"Erro crítico ao processar e replicar sinal: {e}") # <-- CORREÇÃO AQUI

    async def escutar_sinais_mestre(self):
        """Mantém a conexão estável via WebSocket com reconexão automática em caso de queda de rede"""
        while self.running:
            try:
                self.logger.info(f"🔌 Conectando ao canal de transmissão do Mestre em {self.websocket_url}...") # <-- CORREÇÃO AQUI
                async with websockets.connect(self.websocket_url, ping_interval=20, ping_timeout=20) as websocket:
                    self.logger.info("✅ CONECTADO AO MESTRE! Ouvindo canal de sinais em tempo real...") # <-- CORREÇÃO AQUI

                    # Inicia o monitor paralelo de Stop Loss físico na conta
                    self.stop_loss_monitor.iniciar()

                    async for message in websocket:
                        await self.processar_sinal(message)

            except (websockets.exceptions.ConnectionClosed, OSError) as network_err:
                self.logger.warning(f"⚠️ Conexão perdida com o servidor mestre: {network_err}") # <-- CORREÇÃO AQUI
                self.stop_loss_monitor.parar()
                self.logger.info("⏳ Aguardando 10 segundos antes de tentar reconectar...") # <-- CORREÇÃO AQUI
                await asyncio.sleep(10)
            except Exception as e:
                self.logger.error(f"Erro inesperado na malha de rede do cliente: {e}") # <-- CORREÇÃO AQUI
                await asyncio.sleep(5)

    def start(self):
        """Inicia a orquestração do loop assíncrono principal"""
        try:
            asyncio.run(self.escutar_sinais_mestre())
        except KeyboardInterrupt:
            self.logger.info("⏹️ Copy Trader desativado pelo operador.") # <-- CORREÇÃO AQUI
            self.stop_loss_monitor.parar()

if __name__ == "__main__":
    bot_cliente = CopyTraderCliente()
    bot_cliente.start()
