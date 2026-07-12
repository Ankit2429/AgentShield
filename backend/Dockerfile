FROM python:3.11-slim

# Create non-root user with home directory
RUN groupadd -r appgroup && \
    useradd -m -r -g appgroup appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY . .

RUN chown -R appuser:appgroup /app

USER appuser

ENV HOME=/home/appuser

EXPOSE 8000

CMD ["gunicorn", "app.main:app", "--workers", "2", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:${PORT}"]