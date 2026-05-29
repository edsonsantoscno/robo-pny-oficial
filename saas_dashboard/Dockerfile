FROM python:3.12-slim

WORKDIR /app

# Instala dependencias do sistema, timezone e garante Gunicorn para produção
RUN apt-get update && apt-get install -y \
    build-essential curl tzdata \
    && rm -rf /var/lib/apt/lists/*

ENV TZ=America/Sao_Paulo
RUN ln -sf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Correção: Sintaxe corrigida (espaço entre . e .)
COPY . .

EXPOSE 5000

# Correção: Gunicorn para estabilidade na VPS
CMD ["gunicorn", "--workers", "4", "--bind", "0.0.0.0:5000", "app:app"]
