FROM python:3.12-slim

WORKDIR /app

ENV PYTHONPATH=/app
ENV API_HOST=0.0.0.0
ENV PIP_NO_CACHE_DIR=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY config ./config
COPY ingestion ./ingestion
COPY data ./data

EXPOSE 8000

CMD ["python", "-m", "app.main"]
