# websocket_server/Dockerfile (Exemplo)
FROM python:3.12-slim-buster

WORKDIR /app

# Instala tzdata para configurar o fuso horário
RUN apt-get update && apt-get install -y tzdata && \
    rm /etc/localtime && \
    ln -sf /usr/share/zoneinfo/America/Sao_Paulo /etc/localtime && \
    echo America/Sao_Paulo > /etc/timezone && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copia os requirements.txt específicos do websocket-server
# Assumindo que você tem um requirements.txt para o websocket-server
COPY websocket_server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o script principal do websocket-server
COPY websocket_server/websocket_server.py .

# REMOVA A LINHA ABAIXO OU COMENTE-A SE ELA EXISTIR NO SEU DOCKERFILE DO WEBSOCKET-SERVER
# COPY data/robo_trader ./data/robo_trader
# OU QUALQUER LINHA QUE TENTE COPIAR 'data/robo_trader'

CMD ["python", "websocket_server.py"]
