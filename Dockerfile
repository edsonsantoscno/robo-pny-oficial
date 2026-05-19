# Dockerfile (na raiz do projeto)
FROM python:3.12-slim-buster

WORKDIR /app

# Instala tzdata para configurar o fuso horário e garantir logs corretos
RUN apt-get update && apt-get install -y tzdata \
    && rm -rf /var/lib/apt/lists/*

# Define o fuso horário para evitar avisos e garantir consistência de logs
ENV TZ=America/Sao_Paulo
RUN ln -sf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Copia o arquivo de requisitos para o cache do Docker
COPY environment.yml . # Pelo erro, você está usando environment.yml aqui

# Instala as dependências Python
RUN pip install --no-cache-dir -r environment.yml

# Copia o websocket_server.py para o WORKDIR /app
# Se o websocket_server.py estiver na pasta robo_trader/, o caminho precisa ser ajustado.
# Pelo erro, a linha 23 é `COPY robo_trader/websocket_server.py ./websocket_server.py`
COPY robo_trader/websocket_server.py ./websocket_server.py

# REMOVA OU COMENTE A LINHA ABAIXO, ELA ESTÁ CAUSANDO O ERRO
# COPY data/robo_trader ./data/robo_trader

# Comando para iniciar o servidor WebSocket
CMD ["python", "websocket_server.py"]
