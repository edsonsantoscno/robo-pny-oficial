# Use uma imagem base Python leve
FROM python:3.12-slim

# Define o fuso horário
ENV TZ=America/Sao_Paulo

# Instala dependências do sistema (incluindo GIT para baixar bibliotecas)
RUN apt-get update && apt-get install -y tzdata git && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Define a pasta de trabalho
WORKDIR /app

# Copia o arquivo environment.yml para instalar as dependências
COPY environment.yml .

# Instala as bibliotecas
RUN pip install --no-cache-dir -r environment.yml

# Copia o arquivo websocket_server.py e o diretório de dados do mestre
# O websocket_server.py está em robo_trader/websocket_server.py
COPY robo_trader/websocket_server.py ./websocket_server.py
# Copia o diretório de dados do mestre para que o websocket_server possa ler latest_signal.json
COPY data/robo_trader ./data/robo_trader

# Comando para iniciar o servidor WebSocket
CMD ["python", "-u", "websocket_server.py"]
