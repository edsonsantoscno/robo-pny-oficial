import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from urllib.parse import urlparse, parse_qs
import websockets

# ... (Mantenha as configurações de logs e variáveis de ambiente aqui)
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("WS_SERVER")
WS_HOST = os.environ.get("WS_HOST", "0.0.0.0")
WS_PORT = int(os.environ.get("WS_PORT", 6001))
AUTH_TOKEN = os.environ.get("WS_AUTH_TOKEN") # Autenticação obrigatória

CONNECTED_CLIENTS = set()
MASTER_CONNECTION = None

# ... (Funções register_client, unregister_client, broadcast_order_to_clients permanecem iguais)
async def broadcast_order_to_clients(message_dict):
    """Varre todas as conexões de clientes e injeta a ordem do mestre sem delay"""
    if not CONNECTED_CLIENTS:
        logger.warning("⚠ Nova ordem recebida do Mestre, mas NÃO há clientes conectados para copiar!")
        return
    payload = json.dumps(message_dict)
    snapshot_clients = CONNECTED_CLIENTS.copy() # Evita RuntimeError
    tasks = [asyncio.create_task(client.send(payload)) for client in snapshot_clients]
    await asyncio.gather(*tasks, return_exceptions=True)

# ========== PROCESSAMENTO DE EVENTOS DA CONEXÃO RECONSTRUÍDO ==========
async def handler(websocket, path=None):
    """Gerencia o ciclo de vida completo de cada conexão WebSocket"""
    global MASTER_CONNECTION
    
    # Validação de Rota/Token
    query_params = parse_qs(urlparse(websocket.path).query)
    role = query_params.get('role', ['client'])[0]
    token = query_params.get('token', [''])[0]

    if role == 'master':
        if token != AUTH_TOKEN:
            await websocket.close(1008, "Token inválido.")
            return
        MASTER_CONNECTION = websocket
        logger.info("🏆 ROBÔ MASTER conectado!")
    else:
        CONNECTED_CLIENTS.add(websocket)

    try:
        async for message in websocket:
            if websocket == MASTER_CONNECTION:
                data = json.loads(message)
                data["server_timestamp"] = datetime.now().isoformat()
                await broadcast_order_to_clients(data)
    except:
        pass # Tratar desconexões
    finally:
        if websocket == MASTER_CONNECTION:
            MASTER_CONNECTION = None
        else:
            CONNECTED_CLIENTS.discard(websocket)

# ... (main function com configs de ping_interval/timeout)
async def main():
    async with websockets.serve(handler, WS_HOST, WS_PORT, ping_interval=10, ping_timeout=5):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
