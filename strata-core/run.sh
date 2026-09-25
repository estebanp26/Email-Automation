#!/usr/bin/env bash
# run.sh - Inicia el microservicio Strata Core en el puerto 8001
set -e

PORT=8001
VENV_PYTHON="/home/andres/Projects/PDF-Engine/.venv/bin/python3"

if [ -f "$VENV_PYTHON" ]; then
    PYTHON_CMD="$VENV_PYTHON"
elif [ -d ".venv" ]; then
    PYTHON_CMD=".venv/bin/python3"
else
    PYTHON_CMD="python3"
fi

echo "[*] Iniciando Strata Core Microservice en puerto $PORT..."
echo "[*] Usando intérprete: $PYTHON_CMD"

exec $PYTHON_CMD -m uvicorn server:app --host 0.0.0.0 --port $PORT --reload
