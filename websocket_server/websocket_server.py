import asyncio
import json
import logging
import os
import sys
from datetime import datetime
import websockets

# CONFIGURAÇÃO DE LOGS NO TERMINAL DA VPS
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("WS_SERVER")

# VARIÁVEIS DE AMBIENTE E REDE
WS_HOST = os.environ.get("WS_HOST", "0.0.0.0")
WS_PORT = int(os.environ.get("WS_PORT", 6001))
# Chave simples de segurança para garantir que apenas o SEU robô mestre envie ordens
AUTH_TOKEN = os.environ.get("WS_AUTH_TOKEN", "pny_master_secret_token_2026")

# ESTRUTURA DE ARMAZENAMENTO DE CONEXÕES ATIVAS
CONNECTED_CLIENTS = set()
MASTER_CONNECTION = None

async def register_client(websocket):
    """Registra uma nova subconta cliente para escuta de sinais"""
    CONNECTED_CLIENTS.add(websocket)
    logger.info(f"👥 Cliente conectado. Total de ouvintes ativos: {len(CONNECTED_CLIENTS)}")

async def unregister_client(websocket):
    """Remove o cliente da lista de transmissão ao desconectar"""
    CONNECTED_CLIENTS.remove(websocket)
    logger.info(f"🏃 Cliente desconectado. Ouvintes restantes: {len(CONNECTED_CLIENTS)}")

async def broadcast_order_to_clients(message_dict):
    """Varre todas as conexões de clientes e injeta a ordem do mestre sem delay"""
    if not CONNECTED_CLIENTS:
        logger.warning("⚠️ Nova ordem recebida do Mestre, mas NÃO há clientes conectados para copiar!")
        return

    payload = json.dumps(message_dict)
    logger.info(f"📣 Transmitindo ordem para {len(CONNECTED_CLIENTS)} clientes simultaneamente...")
    
    # Executa os disparos em paralelo para garantir latência próxima a zero
    await asyncio.gather(
        *[asyncio.create_task(client.send(payload)) for client in CONNECTED_CLIENTS],
        return_exceptions=True
    )
    logger.info("✅ Sinal de trading replicado com sucesso em todo o ecossistema.")
# ========== PROCESSAMENTO DE EVENTOS DA CONEXÃO ==========
async def handler(websocket, path=None):
    """Gerencia o ciclo de vida completo de cada conexão WebSocket"""
    global MASTER_CONNECTION
    
    # Identifica o tipo de conexão pelos parâmetros da URL (ex: ws://vps:6001/?role=master)
    from urllib.parse import urlparse, parse_qs
    query_params = parse_qs(urlparse(websocket.path).query)
    role = query_params.get('role', ['client'])[0]
    token = query_params.get('token', [''])[0]

    if role == 'master':
        # Validação simples de segurança contra invasores tentando forçar ordens falsas
        if token != AUTH_TOKEN:
            logger.warning(f"🚨 Tentativa de conexão Master REJEITADA! Token inválido.")
            await websocket.close(1008, "Token de autenticação inválido.")
            return
        
        MASTER_CONNECTION = websocket
        logger.info("🏆 ROBÔ MASTER conectado e autenticado com sucesso! Pronto para emitir sinais.")
    else:
        await register_client(websocket)

    try:
        # Loop contínuo escutando mensagens da conexão ativa
        async for message in websocket:
            try:
                data = json.loads(message)
                
                # Se a mensagem vier do Robô Mestre, distribui imediatamente para os clientes
                if websocket == MASTER_CONNECTION:
                    logger.info(f"📥 Sinal recebido do Mestre: Ativo={data.get('symbol')} | Ação={data.get('type')}")
                    # Injeta timestamp do servidor para auditoria de latência posterior
                    data["server_timestamp"] = datetime.now().isoformat()
                    await broadcast_order_to_clients(data)
                else:
                    # Clientes normais não devem enviar ordens para o servidor
                    logger.info(f"💬 Mensagem recebida de cliente (Ignorada): {data}")
                    
            except json.JSONDecodeError:
                logger.error(f"❌ Falha ao decodificar JSON enviado pela conexão: {message}")

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        # Tratamento e limpeza de conexões derrubadas
        if websocket == MASTER_CONNECTION:
            logger.warning("⚠️ O ROBÔ MASTER se desconectou do servidor WebSocket!")
            MASTER_CONNECTION = None
        else:
            await unregister_client(websocket)

# ========== LOOP PRINCIPAL DE INICIALIZAÇÃO DA VPS ==========
async def main():
    logger.info(f"🚀 Inicializando servidor WebSocket em ws://{WS_HOST}:{WS_PORT}")
    
    # Configurações agressivas de ping/pong para derrubar conexões fantasmas instantaneamente na VPS
    async with websockets.serve(
        handler, 
        WS_HOST, 
        WS_PORT,
        ping_interval=10, # Envia ping a cada 10 segundos
        ping_timeout=5,   # Aguarda resposta por no máximo 5 segundos antes de desconectar
        max_size=2**20    # Proteção contra estouro de payload (limite de 1MB)
    ):
        await asyncio.Future() # Mantém o servidor rodando infinitamente 24/7

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⏹ Servidor WebSocket encerrado manualmente.")
