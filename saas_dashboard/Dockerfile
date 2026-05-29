FROM python:3.12-slim

WORKDIR /app

# Instala ferramentas essenciais do sistema e limpa caches de pacotes
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Fixa o fuso horário oficial brasileiro para bater com os logs de trading
ENV TZ=America/Sao_Paulo
RUN ln -sf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Instala pacotes do Python isolando as camadas de cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# AJUSTADO: Espaço inserido entre os pontos para cópia correta do diretório
COPY . .

# Abre a porta padrão de comunicação mapeada no config_dashboard.py
EXPOSE 5000

# CORREÇÃO DE CONCORRÊNCIA: 1 Worker principal com 4 Threads.
# Isso garante paralelismo mantendo a eficácia da trava (Lock) nos arquivos JSON locais.
CMD ["gunicorn", "--workers", "1", "--threads", "4", "--bind", "0.0.0.0:5000", "app:app"]
