# Dockerfile para o serviço websocket-server
FROM python:3.12-slim-buster

WORKDIR /app

# Instala tzdata para configurar o fuso horário
RUN apt-get update && apt-get install -y tzdata git && \
    ln -snf /usr/share/zoneinfo/America/Sao_Paulo /etc/localtime && echo America/Sao_Paulo > /etc/timezone && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copia o arquivo de requisitos e instala as dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código do websocket_server
# Assumindo que websocket_server.py está na raiz do projeto ou em robo_trader/
# Se estiver na raiz:
COPY websocket_server.py ./websocket_server.py
# Se estiver em robo_trader/:
# COPY robo_trader/websocket_server.py ./websocket_server.py

# REMOVA ESTA LINHA: COPY data/robo_trader ./data/robo_trader
# Os dados serão montados via volume no docker-compose.yml, não copiados para a imagem.

# O comando final será definido no docker-compose.yml
