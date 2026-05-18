# 1. Usa uma imagem leve do Python
FROM python:3.12-slim

# 2. Define o fuso horário
ENV TZ=America/Sao_Paulo

# 3. Instala dependências do sistema (incluindo GIT para baixar bibliotecas)
RUN apt-get update && apt-get install -y tzdata git && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# 4. Define a pasta de trabalho
WORKDIR /app

# 5. Copia o arquivo de requisitos
COPY requirements.txt .

# 6. Instala as bibliotecas
RUN pip install --no-cache-dir -r requirements.txt

# 7. Copia o resto do código
COPY . .

# 8. Inicia o robô
CMD ["python", "robo_trader/main_trader.py"]
