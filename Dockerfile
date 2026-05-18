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

# Copia o código da aplicação do dashboard
COPY saas_dashboard/app.py ./app.py
COPY saas_dashboard/config_dashboard.py ./config_dashboard.py
COPY saas_dashboard/templates ./templates
COPY saas_dashboard/static ./static

# Comando padrão para executar o dashboard
CMD ["python", "-u", "app.py"]
