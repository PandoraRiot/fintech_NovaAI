# ──────────────────────────────────────────────────────────────────────────
# FinTech Intelligence MVP — Dockerfile
# Base: python:3.11-slim (imagen oficial, ~125MB)
# ──────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim

# Metadata
LABEL maintainer="FinTech Hackathon 2026"
LABEL description="FinTech Intelligence MVP — Medallion + ML + LLM + Streamlit"

# Variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    STREAMLIT_THEME_BASE=dark \
    PYTHONPATH=/app

WORKDIR /app

# ── Dependencias del sistema ───────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ── Dependencias Python (layer cacheado) ──────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ── Código fuente ─────────────────────────────────────────────────────────
COPY . .

# ── Crear directorios de datos ────────────────────────────────────────────
RUN mkdir -p data/bronze data/silver data/gold

# ── Healthcheck ───────────────────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# ── Exponer puerto ────────────────────────────────────────────────────────
EXPOSE 8501

# ── Entrypoint ────────────────────────────────────────────────────────────
CMD ["streamlit", "run", "dashboard/app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true"]
