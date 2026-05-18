FROM python:3.12-slim-buster

WORKDIR /app

# Instala tzdata para configurar o fuso horário
RUN apt-get update && apt-get install -y tzdata \
    && rm -rf /var/lib/apt/lists/*

# Copia o arquivo de requisitos e instala as dependências
COPY websocket_server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o script principal do servidor WebSocket
COPY websocket_server/websocket_server.py .

# Não copie data/robo_trader, pois o websocket-server lerá de /app/state
# REMOVIDA A LINHA QUE CAUSAVA O ERRO: COPY data/robo_trader ./data/robo_trader

# Comando para iniciar o servidor WebSocket
CMD ["python", "websocket_server.py"]
