import asyncio
import os
import logging
import urllib.parse
import websockets

# Configuração de logs profissional para o contêiner
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("WebSocketServer")

# Conjunto de conexões ativas gerenciadas em memória (thread-safe através do loop do asyncio)
CONEXOES_CLIENTES = set()
CONEXOES_MESTRES = set()

# Definição de porta dinâmica alinhada com o docker-compose.yml
PORTA_WS = int(os.getenv("WS_PORT", 6001))

async def gerenciar_conexao(websocket, path):
    """
    Roteia o handshake inicial identificando se a conexão é o robô mestre 
    enviando sinais ou o robô cliente escutando transmissões.
    """
    try:
        # Faz o parse da query string da URL para validar o papel (ex: ?role=client)
        url_parseada = urllib.parse.urlparse(path)
        parametros = urllib.parse.parse_qs(url_parseada.query)
        papel = parametros.get("role", ["unknown"])[0]

        if papel == "master":
            CONEXOES_MESTRES.add(websocket)
            logger.info(f"🚀 Canal MESTRE registrado com sucesso! Total Masters: {len(CONEXOES_MESTRES)}")
            
            # Loop de escuta: recebe o sinal do mestre e faz broadcast imediato para os clientes
            async for sinal in websocket:
                logger.info(f"📡 Sinal recebido do Master: {sinal}")
                if CONEXOES_CLIENTES:
                    # Envia em lote de forma assíncrona concorrente
                    await asyncio.gather(*[
                        asyncio.create_task(cliente.send(sinal))
                        for cliente in CONEXOES_CLIENTES
                    ], return_exceptions=True)
                    logger.info(f"📢 Sinal retransmitido (Broadcast) para {len(CONEXOES_CLIENTES)} clientes ativos.")
                else:
                    logger.info("ℹ Sinal ignorado no broadcast: Nenhum robô cliente conectado na escuta.")
                    
        elif papel == "client":
            CONEXOES_CLIENTES.add(websocket)
            logger.info(f"👥 Robô CLIENTE sincronizado na escuta! Total Clientes: {len(CONEXOES_CLIENTES)}")
            
            # Mantém a conexão aberta e escuta mensagens vazias (pings de verificação de rede)
            async for _ in websocket:
                pass
        else:
            logger.warning(f"🔒 Tentativa de conexão rejeitada: Papel '{papel}' inválido ou não autenticado.")
            await websocket.close(1008, "Papel de autenticação inválido.")
            
    except websockets.exceptions.ConnectionClosed:
        pass
    except Exception as e:
        logger.error(f"❌ Erro operacional na thread do WebSocket: {e}")
    finally:
        # Garante a limpeza do conjunto em memória caso a conexão caia
        if websocket in CONEXOES_MESTRES:
            CONEXOES_MESTRES.remove(websocket)
            logger.info(f"🔌 Conexão Mestre encerrada. Restantes: {len(CONEXOES_MESTRES)}")
        if websocket in CONEXOES_CLIENTES:
            CONEXOES_CLIENTES.remove(websocket)
            logger.info(f"🔌 Conexão Cliente encerrada. Restantes: {len(CONEXOES_CLIENTES)}")

async def main():
    """Inicializa e mantém o loop estável do servidor na porta 6001."""
    logger.info(f"🔌 Inicializando o Servidor de Sinais WebSocket na porta {PORTA_WS}...")
    async with websockets.serve(gerenciar_conexao, "0.0.0.0", PORTA_WS, ping_interval=20, ping_timeout=20):
        await asyncio.Future()  # Executa o servidor de forma indefinida 24/7

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # AJUSTADO DEFINITIVAMENTE: String fechada corretamente com as aspas (Fix #1)
        logger.info("⏹️ Servidor WebSocket encerrado de forma segura via terminal.")
