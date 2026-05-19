
FROM python:3.12-slim-buster

WORKDIR /app

RUN apt-get update && apt-get install -y tzdata \
    && rm -rf /var/lib/apt/lists/*

ENV TZ=America/Sao_Paulo
RUN ln -sf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

COPY saas-dashboard/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY saas-dashboard/ .

CMD ["python", "app.py"]
