# /root/robo-pny-oficial/websocket_server/Dockerfile
FROM python:3.12-slim-buster

WORKDIR /app

# Instala tzdata para configurar o fuso horário
RUN apt-get update && apt-get install -y tzdata \
    && rm -rf /var/lib/apt/lists/*

ENV TZ=America/Sao_Paulo
RUN ln -sf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Copia o arquivo de requisitos para o cache do Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código do websocket_server
COPY websocket_server.py .

CMD ["python", "websocket_server.py"]
