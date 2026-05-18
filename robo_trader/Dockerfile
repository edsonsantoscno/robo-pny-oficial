# robo_trader/Dockerfile.robo-trader
FROM python:3.12-slim-buster

WORKDIR /app

# Instala tzdata para configurar o fuso horário e garantir logs corretos
RUN apt-get update && apt-get install -y tzdata \
    && rm -rf /var/lib/apt/lists/*

# Define o fuso horário para evitar avisos e garantir consistência de logs
ENV TZ=America/Sao_Paulo
RUN ln -sf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Copia o arquivo de requisitos para o cache do Docker
COPY robo_trader/requirements.txt .

# Instala as dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia todos os arquivos do robo_trader para o WORKDIR /app
# Isso inclui config.py, client.py, strategy.py, order_manager.py, risk_manager.py, logger.py, signal_generator.py
# E AGORA TAMBÉM O websocket_server.py
COPY robo_trader/ .

# Comando para iniciar o servidor WebSocket e o robô trader
# Usaremos um script de entrada para iniciar ambos em segundo plano
COPY robo_trader/start_robo_trader.sh .
RUN chmod +x start_robo_trader.sh

CMD ["./start_robo_trader.sh"]
