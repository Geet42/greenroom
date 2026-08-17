FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    nodejs \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000


# --no-access-log: main.py's own request_logger middleware already emits one
# structured JSON line per request (method, route template, status, latency,
# user_id) — uvicorn's default plain-text access log was duplicating every
# request as a second, unstructured line in the same log stream, cluttering
# the Grafana log panels for no added information.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
