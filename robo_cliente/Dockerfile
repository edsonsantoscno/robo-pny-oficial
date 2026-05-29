FROM python:3.12-slim

WORKDIR /app

# Instala dependências do sistema essenciais para compilação e fuso horário
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Configura o fuso horário oficial do ecossistema de trading
ENV TZ=America/Sao_Paulo
RUN ln -sf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Instala as dependências Python isoladas do cliente
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# CORREÇÃO: Adicionado o espaço correto entre a origem e o destino do contêiner
COPY .  .

# Comando de inicialização do robô copiador
CMD ["python", "main_copy_trader.py"]
