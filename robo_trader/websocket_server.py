import asyncio
import websockets
import json
import logging
from datetime import datetime
from pathlib import Path
from config import WEBSOCKET_PORT, WEBSOCKET_HOST, LOG_FILE

# Configuração robusta de logs integrados
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()]
)
logger = logging.getLogger("WebSocketServer")

# Garante o caminho absoluto unificado no Docker
BASE_DIR = Path(__file__).parent
SIGNAL_FILE = BASE_DIR / "latest_signal.json"

class SignalServer:
    def __init__(self):
        self.clients = set()
        self.last_signal = None

    async def broadcast_signal(self, signal):
        """Transmite o sinal em tempo real para todos os clientes ativos."""
        if self.clients:
            message = json.dumps(signal)
            disconnected = set()
            for client in self.clients:
                try:
                    await client.send(message)
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao enviar para cliente: {e}")
                    disconnected.add(client)
            if disconnected:
                self.clients -= disconnected
                logger.info(f"👥 Clientes limpos. Restantes: {len(self.clients)}")

    async def handle_client(self, websocket, path=None):
        """Gerencia conexões de entrada de novos robôs clientes."""
        self.clients.add(websocket)
        logger.info(f"🔌 Novo cliente conectado | Total ativo: {len(self.clients)}")

        try:
            # Envia o último sinal memorizado logo na conexão para o cliente se atualizar
            if self.last_signal:
                await websocket.send(json.dumps(self.last_signal))

            async for message in websocket:
                data = json.loads(message)
                if data.get("command") == "get_status":
                    status = {
                        "status": "running",
                        "last_signal": self.last_signal,
                        "clients_connected": len(self.clients),
                        "timestamp": datetime.now().isoformat()
                    }
                    await websocket.send(json.dumps(status))
        except Exception as e:
            logger.debug(f"Conexão encerrada com cliente de forma padrão: {e}")
        finally:
            self.clients.discard(websocket)
            logger.info(f"❌ Cliente desconectado | Total ativo: {len(self.clients)}")

    async def monitor_signal_file(self):
        """Varre o arquivo local em busca de novos sinais gerados pelo main_trader.py"""
        logger.info("🔍 Monitor de arquivos de sinais iniciado com sucesso.")
        while True:
            try:
                if SIGNAL_FILE.exists():
                    with open(SIGNAL_FILE, "r") as f:
                        signal = json.load(f)
                    
                    if signal != self.last_signal:
                        self.last_signal = signal
                        logger.info(f"📡 Novo sinal detectado! Transmitindo: {signal.get('operation_type')} | {signal.get('symbol')}")
                        await self.broadcast_signal(signal)
            except Exception as e:
                logger.error(f"Erro ao ler arquivo de sinal dinâmico: {e}")
            
            # Trava de segurança obrigatória: evita o consumo de 100% de CPU
            await asyncio.sleep(1)

    async def start(self):
        """Inicializa o servidor de rede e o monitor em paralelo."""
        logger.info(f"🚀 Inicializando WebSocket mestre em ws://{WEBSOCKET_HOST}:{WEBSOCKET_PORT}")
        
        # Inicia o servidor Websocket na rede da VPS
        async with websockets.serve(self.handle_client, WEBSOCKET_HOST, WEBSOCKET_PORT):
            # Roda o monitor de arquivos em segundo plano junto com o servidor
            await self.monitor_signal_file()

if __name__ == "__main__":
    try:
        server = SignalServer()
        asyncio.run(server.start())
    except KeyboardInterrupt:
        logger.info("⏹️ Servidor WebSocket encerrado.")
