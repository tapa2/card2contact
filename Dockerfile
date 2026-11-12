# Container image of the service (can run locally or on Google Cloud Run).
FROM python:3.14-slim

WORKDIR /app

# Install dependencies first: this layer is cached while only the code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/
COPY static/ static/
COPY samples/ samples/

# Cloud Run tells the container which port to listen on via $PORT (8080 by default).
ENV PORT=8080
EXPOSE 8080
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port $PORT"]
