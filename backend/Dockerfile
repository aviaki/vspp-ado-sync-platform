# backend/Dockerfile — v0.0.1
FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libffi-dev && \
    rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
USER nobody
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
