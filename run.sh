#!/usr/bin/env bash
# =============================================================================
# RIWI - SISTEMA AUTOMATIZADO DE JUSTIFICACIONES HSE
# Script de Inicio Unificado del Ecosistema Completo
# =============================================================================
set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

# Colores para la consola
GREEN='\033[0;32m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color
BOLD='\033[1m'

echo -e "\n${PURPLE}${BOLD}"
echo "  ================================================================"
echo "    RIWI HSE - SISTEMA DE AUTOMATIZACION Y GESTION DE JUSTIFICACIONES"
echo "  ================================================================"
echo -e "${NC}"

# 1. Comprobación y activación de contenedores Docker (PostgreSQL y n8n)
echo -e "${CYAN}[1/4] Verificando contenedores Docker...${NC}"

if command -v docker &>/dev/null; then
    # PostgreSQL
    if docker ps -a --format '{{.Names}}' | grep -q "^hse-postgres$"; then
        if [ "$(docker inspect -f '{{.State.Running}}' hse-postgres 2>/dev/null)" != "true" ]; then
            echo -e "  ${YELLOW}Iniciando contenedor hse-postgres (PostgreSQL 16)...${NC}"
            docker start hse-postgres >/dev/null
        else
            echo -e "  ${GREEN}✓ hse-postgres ya está en ejecución (Puerto 5432)${NC}"
        fi
    else
        echo -e "  ${YELLOW}Aviso: Contenedor 'hse-postgres' no encontrado; asegurando conexión externa a PostgreSQL.${NC}"
    fi

    # n8n
    if docker ps -a --format '{{.Names}}' | grep -q "^novasync-n8n$"; then
        if [ "$(docker inspect -f '{{.State.Running}}' novasync-n8n 2>/dev/null)" != "true" ]; then
            echo -e "  ${YELLOW}Iniciando contenedor novasync-n8n (Workflow Engine)...${NC}"
            docker start novasync-n8n >/dev/null
        else
            echo -e "  ${GREEN}✓ novasync-n8n ya está en ejecución (Puerto 5678)${NC}"
        fi
    fi
else
    echo -e "  ${YELLOW}Aviso: Docker no detectado directamente en PATH; asumiendo servicios externos activos.${NC}"
fi

# 2. Detección del intérprete Python para Strata Core
echo -e "${CYAN}[2/5] Configurando entorno Python para Backend Strata Core...${NC}"
if [ -f "$PROJECT_ROOT/strata-core/.venv/bin/python3" ]; then
    PYTHON_CMD="$PROJECT_ROOT/strata-core/.venv/bin/python3"
elif [ -f "$PROJECT_ROOT/strata-core/.venv/bin/python" ]; then
    PYTHON_CMD="$PROJECT_ROOT/strata-core/.venv/bin/python"
elif [ -f "$PROJECT_ROOT/strata-core/.venv/Scripts/python.exe" ]; then
    PYTHON_CMD="$PROJECT_ROOT/strata-core/.venv/Scripts/python.exe"
elif [ -f "$PROJECT_ROOT/strata-core/.venv/Scripts/python" ]; then
    PYTHON_CMD="$PROJECT_ROOT/strata-core/.venv/Scripts/python"
elif command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
else
    PYTHON_CMD="python"
fi
echo -e "  ${GREEN}✓ Intérprete Python: $PYTHON_CMD${NC}"

# Variables de proceso para limpieza
BACKEND_PID=""
FRONTEND_PID=""
LISTENER_PID=""

cleanup() {
    echo -e "\n${YELLOW}Deteniendo servicios del ecosistema...${NC}"
    if [ -n "$LISTENER_PID" ] && kill -0 "$LISTENER_PID" 2>/dev/null; then
        echo -e "  Deteniendo Escuchador de Gmail (PID: $LISTENER_PID)..."
        kill "$LISTENER_PID" 2>/dev/null || true
    fi
    if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        echo -e "  Deteniendo Backend Strata Core (PID: $BACKEND_PID)..."
        kill "$BACKEND_PID" 2>/dev/null || true
    fi
    if [ -n "$FRONTEND_PID" ] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
        echo -e "  Deteniendo Frontend Vite (PID: $FRONTEND_PID)..."
        kill "$FRONTEND_PID" 2>/dev/null || true
    fi
    # Limpieza de procesos residuales en puertos 8001 y 5173
    fuser -k 8001/tcp 2>/dev/null || true
    fuser -k 5173/tcp 2>/dev/null || true
    echo -e "${GREEN}✓ Todos los servicios se han detenido correctamente.${NC}\n"
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

# Liberar puertos por si estaban ocupados previamente
fuser -k 8001/tcp 2>/dev/null || true
fuser -k 5173/tcp 2>/dev/null || true
sleep 1

# 3. Iniciar Backend Strata Core (FastAPI en puerto 8001)
echo -e "${CYAN}[3/5] Levantando Backend Strata Core en puerto 8001...${NC}"
cd "$PROJECT_ROOT/strata-core"
$PYTHON_CMD -m uvicorn server:app --host 0.0.0.0 --port 8001 --reload &
BACKEND_PID=$!
cd "$PROJECT_ROOT"

# Esperar a que el backend responda
sleep 2

# 4. Iniciar Frontend (Vite en puerto 5173)
echo -e "${CYAN}[4/5] Levantando Frontend (Vite + React) en puerto 5173...${NC}"
cd "$PROJECT_ROOT/frontend"
npm run dev -- --host 0.0.0.0 --port 5173 &
FRONTEND_PID=$!
cd "$PROJECT_ROOT"

# Esperar que los servicios se estabilicen
sleep 2

# 5. Iniciar Escuchador en vivo de Gmail (IMAP)
echo -e "${CYAN}[5/5] Levantando Escuchador en vivo de Gmail (IMAP)...${NC}"
$PYTHON_CMD "$PROJECT_ROOT/scripts/gmail_live_listener.py" &
LISTENER_PID=$!

echo -e "\n${GREEN}${BOLD}================================================================${NC}"
echo -e "${GREEN}${BOLD}  ✓ ECOSISTEMA RIWI HSE LEVANTADO Y LISTO PARA PRUEBAS          ${NC}"
echo -e "${GREEN}${BOLD}================================================================${NC}"
echo -e "  ${BOLD}🖥️  Frontend Tablero HSE:${NC}    ${BLUE}http://localhost:5173${NC}"
echo -e "  ${BOLD}📋 Bandeja de Solicitudes:${NC}  ${BLUE}http://localhost:5173/requests${NC}"
echo -e "  ${BOLD}👥 Directorio de Coders:${NC}    ${BLUE}http://localhost:5173/students${NC}"
echo -e "  ${BOLD}⚡ Backend Strata Core API:${NC} ${BLUE}http://localhost:8001/docs${NC}"
echo -e "  ${BOLD}🔄 Orquestador n8n:${NC}         ${BLUE}http://localhost:5678${NC}"
echo -e "  ${BOLD}🗄️  PostgreSQL Database:${NC}     ${BLUE}localhost:5432 (hse_email_automation)${NC}"
echo -e "  ${BOLD}📨 Escuchador de Gmail:${NC}     ${BLUE}Activo en tiempo real${NC}"
echo -e "${GREEN}================================================================${NC}"
echo -e "${YELLOW}Presiona Ctrl+C en cualquier momento para detener todos los servicios.${NC}\n"

# Mantener en ejecución
wait "$BACKEND_PID" "$FRONTEND_PID" "$LISTENER_PID"
