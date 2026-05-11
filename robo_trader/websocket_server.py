# robo_trader/websocket_server.py
import asyncio
import websockets
import json
from datetime import datetime
import time
from config import WEBSOCKET_PORT, WEBSOCKET_HOST, LOG_FILE
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()]
)
logger = logging.getLogger("WebSocketServer")

class SignalServer:
    def __init__(self):
        self.clients = set()
        self.last_signal = None

    async def broadcast_signal(self, signal):
        if self.clients:
            message = json.dumps(signal)
            disconnected = set()
            for client in self.clients:
                try:
                    await client.send(message)
                except Exception as e:
                    logger.warning(f"Erro ao enviar para cliente: {e}")
                    disconnected.add(client)
            self.clients -= disconnected

    async def handle_client(self, websocket, path):
        self.clients.add(websocket)
        logger.info(f"Cliente conectado | Total: {len(self.clients)}")

        try:
            async for message in websocket:
                data = json.loads(message)
                if data.get("command") == "get_status":
                    status = {
                        "status": "running",
                        "last_signal": self.last_signal,
                        "clients_connected": len(self.clients),
                    }
                    await websocket.send(json.dumps(status))
        except Exception as e:
            logger.error(f"Erro com cliente: {e}")
        finally:
            self.clients.discard(websocket)
            logger.info(f"Cliente desconectado | Total: {len(self.clients)}")

    async def run(self):
        async with websockets.serve(self.handle_client, WEBSOCKET_HOST, WEBSOCKET_PORT):
            logger.info(f"WebSocket mestre rodando em ws://{WEBSOCKET_HOST}:{WEBSOCKET_PORT}")
            await asyncio.Future()  # Roda para sempre

async def main():
    server = SignalServer()

    # Em paralelo, escute os sinais que seu robô envia ao Supabase
    # (você já envia "sinal de COMPRA (new)" ao Supabase)
    while True:
        # Aqui você pode ler o Supabase ou um arquivo de sinais
        # Exemplo: ler de um arquivo temporário que seu main_trader.py escreve
        try:
            with open("robo_trader/latest_signal.json", "r") as f:
                signal = json.load(f)
                if signal != server.last_signal:
                    server.last_signal = signal
                    await server.broadcast_signal(signal)
        except Exception as e:
            pass
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())