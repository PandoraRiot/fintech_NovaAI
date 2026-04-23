#!/bin/sh
# entrypoint.sh — Backend startup script
# 1. Pre-genera el Gold Layer (Bronze → Silver → Gold) si no existe
# 2. Levanta el servidor FastAPI
# Esto garantiza que el dashboard tenga datos al arrancar

set -e

echo ""
echo "================================================"
echo " FinTech NovaAI — Backend iniciando..."
echo "================================================"
echo ""

# Pre-generar parquets si no existen
# El pipeline tarda ~0.7s — vale la pena para no tener el dashboard vacío
if [ ! -f "data/gold/user_360.parquet" ]; then
    echo "📊 Gold Layer no encontrado — ejecutando pipeline Medallion..."
    python run_pipeline.py
    echo "✅ Pipeline completado — datos listos"
else
    echo "✅ Gold Layer ya existe — saltando pipeline"
fi

echo ""
echo "🚀 Iniciando FastAPI..."
echo ""

# Arrancar el servidor
exec uvicorn api.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 1 \
    --log-level info