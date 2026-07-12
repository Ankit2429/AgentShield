FROM python:3.11-slim

# Create a non-root user
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

WORKDIR /app

# Install dependencies first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy the backend source
COPY --chown=appuser:appgroup . .

# Switch to non-root user
USER appuser

EXPOSE 8000 10000

# Run with Gunicorn and Uvicorn workers for production readiness
CMD sh -c "gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:${PORT:-8000}"
