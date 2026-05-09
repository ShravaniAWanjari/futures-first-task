#!/bin/sh
set -e

echo "=============================================="
echo "  FuturesFirst Backend — Container Startup"
echo "=============================================="

# Check if databases already exist (persistent volume)
if [ ! -f "/app/databases/vistastream.db" ] || [ ! -s "/app/databases/vistastream.db" ]; then
    echo "[INIT] First run detected — running full bootstrap pipeline..."
    python -m backend.bootstrap
    echo "[INIT] Bootstrap complete."
else
    echo "[INIT] Existing databases found — skipping bootstrap."
    echo "[INIT] To force a rebuild, delete the databases/ volume and restart."
fi

echo ""
echo "[START] Launching FuturesFirst API Server..."
exec uvicorn backend.api.app:app --host 0.0.0.0 --port 8000
