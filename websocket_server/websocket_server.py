import asyncio
import websockets
import json
import logging
from datetime import datetime
from pathlib import Path
from config import WEBSOCKET_PORT, WEBSOCKET_HOST # Importa do config.py do mestre

# --- CORREÇÃO AQUI: Caminho unificado para o arquivo de log ---
# O LOG_FILE deve vir do config.py do robô mestre, que já foi ajustado para /app/state
# Se o websocket_server tiver seu próprio LOG_FILE, ele também deve apontar para /app/state
# Para este exemplo, vou assumir que ele usa o LOG_FILE do config.py do mestre
from config import LOG_FILE # Certifique-se que LOG_FILE está definido em config.py

# Configuração robusta de logs integrados
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()]
)
logger = logging.getLogger("WebSocketServer")

# --- CORREÇÃO AQUI: Caminho unificado para o arquivo de sinal ---
# O SIGNAL_FILE deve apontar diretamente para /app/state
SIGNAL_FILE = Path("/app/state") / "latest_signal.json"

class SignalServer:
    def __init__(self):
        self.clients = set()
        # Garante que o arquivo de sinal exista ao iniciar o servidor
        if not SIGNAL_FILE.exists():
            with open(SIGNAL_FILE, 'w') as f:
                json.dump({}, f) # Cria um JSON vazio ou com um estado inicial

    async def register(self, websocket):
        self.clients.add(websocket)
        logger.info(f"Cliente conectado: {websocket.remote_address}. Total de clientes: {len(self.clients)}")

    async def unregister(self, websocket):
        self.clients.remove(websocket)
        logger.info(f"Cliente desconectado: {websocket.remote_address}. Total de clientes: {len(self.clients)}")

    async def send_signal(self, message):
        if self.clients:
            # Envia a mensagem para todos os clientes conectados
            await asyncio.wait([client.send(message) for client in self.clients])

    async def monitor_signal_file(self):
        """Monitora o arquivo latest_signal.json e envia atualizações via WebSocket."""
        last_modified = None
        while True:
            try:
                if SIGNAL_FILE.exists():
                    current_modified = SIGNAL_FILE.stat().st_mtime
                    if current_modified != last_modified:
                        last_modified = current_modified
                        with open(SIGNAL_FILE, 'r') as f:
                            signal_data = json.load(f)
                        await self.send_signal(json.dumps(signal_data))
                await asyncio.sleep(1) # Verifica a cada 1 segundo
            except Exception as e:
                logger.error(f"Erro ao monitorar arquivo de sinal: {e}")
                await asyncio.sleep(5) # Espera um pouco antes de tentar novamente

    async def handle_client(self, websocket, path):
        """Lida com a conexão de um novo cliente WebSocket."""
        await self.register(websocket)
        try:
            await websocket.wait_closed() # Mantém a conexão aberta até o cliente desconectar
        finally:
            await self.unregister(websocket)

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
        logger.info("⏹️ Servidor WebSocket en
