# robo_trader/Dockerfile.robo-trader
FROM python:3.12-slim

WORKDIR /app

# Instala tzdata para configurar o fuso horário e garantir logs corretos
RUN apt-get update && apt-get install -y tzdata build-essential \
    && rm -rf /var/lib/apt/lists/*

# Define o fuso horário para evitar avisos e garantir consistência de logs
ENV TZ=America/Sao_Paulo
RUN ln -sf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Copia o arquivo de requisitos para o cache do Docker
COPY robo_trader/requirements.txt .

# Instala as dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# --- INSTALAÇÃO DO PANDAS-TA DO TAR.GZ ---
COPY robo_trader/pandas_ta-0.4.71b0.tar.gz .
RUN pip install --no-cache-dir ./pandas_ta-0.4.71b0.tar.gz

# Copia todos os arquivos mantendo a pasta "robo_trader" na estrutura interna
# Isso garante que caminhos como "/app/robo_trader/main_trader.py" funcionem perfeitamente
COPY robo_trader/ ./robo_trader/

# Dá permissão e prepara o script de inicialização que agora está na subpasta
RUN chmod +x ./robo_trader/start_robo_trader.sh

CMD ["./robo_trader/start_robo_trader.sh"]
