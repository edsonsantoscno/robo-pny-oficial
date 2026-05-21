FROM python:3.12-slim

WORKDIR /app

# Instala dependencias do sistema (timezone, build-essential, curl)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Configura o fuso horário
ENV TZ=America/Sao_Paulo
RUN ln -sf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Copia requirements e instala dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o código do robo_trader para /app
COPY . .

# Arquivo principal do robo_trader
CMD ["python", "main_trader.py"]
