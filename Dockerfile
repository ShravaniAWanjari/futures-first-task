# =============================================================================
# FuturesFirst Backend — Production Dockerfile
# =============================================================================
FROM python:3.11-slim

# Prevent bytecode and enable real-time logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Install system dependencies (build tools for native extensions + curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (cached layer — only rebuilds when requirements change)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY backend/ backend/
COPY data/ data/
COPY docs/ docs/

# Create persistent directories (will be overridden by volume mounts)
RUN mkdir -p databases logs chroma

EXPOSE 8000

# Entrypoint script: bootstrap if first run, then start API
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

ENTRYPOINT ["/app/docker-entrypoint.sh"]
