# Use uma imagem base Python leve
FROM python:3.12-slim

# Define o diretório de trabalho dentro do container
WORKDIR /app

# Instala as dependências do sistema (tzdata, git)
RUN apt-get update && apt-get install -y tzdata git && \
    ln -snf /usr/share/zoneinfo/America/Sao_Paulo /etc/localtime && echo America/Sao_Paulo > /etc/timezone && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copia o arquivo de requisitos e instala as dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código do robo-trader e do websocket_server
COPY robo_trader/main_trader.py ./main_trader.py
COPY robo_trader/websocket_server.py ./websocket_server.py
COPY robo_trader/config.py ./config.py
COPY robo_trader/logger.py ./logger.py
COPY robo_trader/client.py ./client.py
COPY robo_trader/order_manager.py ./order_manager.py
COPY robo_trader/risk_manager.py ./risk_manager.py
COPY robo_trader/stop_loss_monitor.py ./stop_loss_monitor.py

# Cria o diretório 'data' dentro do container, se ele for usado para arquivos internos do robo-trader
# O acesso ao 'latest_signal.json' será via volume, então não precisa copiar aqui.
RUN mkdir -p data

# Comando padrão para executar o robo-trader e o websocket_server
# (Você precisará de um script de entrada ou um comando mais complexo para rodar ambos)
# Exemplo: CMD ["bash", "-c", "python -u websocket_server.py & python -u main_trader.py"]
# Ou, se o main_trader.py inicia o websocket_server internamente, apenas:
CMD ["python", "-u", "main_trader.py"]
