#!/usr/bin/env bash
# run.sh - Inicia el microservicio Strata Core en el puerto 8001
set -e

PORT=${PORT:-8001}

if [ -f ".venv/bin/python3" ]; then
    PYTHON_CMD=".venv/bin/python3"
elif command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
else
    PYTHON_CMD="python"
fi

echo "[*] Iniciando Strata Core Microservice en puerto $PORT..."
echo "[*] Usando intérprete: $PYTHON_CMD"

exec $PYTHON_CMD -m uvicorn server:app --host 0.0.0.0 --port $PORT --reload
