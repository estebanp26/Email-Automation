#!/usr/bin/env python3
"""
RIWI HSE - Ecosistema de Automatización de Justificaciones
Runner Universal Multiplataforma (Windows, Linux, macOS)
Ejecución:
    python run.py
"""

import os
import sys
import time
import signal
import shutil
import subprocess
from pathlib import Path

# Configuración de colores ANSI (compatibles con Windows 10+ Terminal y Unix)
GREEN = "\033[92m"
BLUE = "\033[94m"
PURPLE = "\033[95m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
NC = "\033[0m"

# Habilitar soporte de colores ANSI en Windows cmd/powershell antiguos
if sys.platform == "win32":
    os.system("")

PROJECT_ROOT = Path(__file__).resolve().parent
processes = []


def log(msg, color=NC, bold=False):
    prefix = BOLD if bold else ""
    print(f"{prefix}{color}{msg}{NC}")


def check_docker():
    """Comprueba e inicia contenedores requeridos en Docker si está disponible."""
    log("[1/5] Verificando contenedores Docker...", CYAN)
    docker_bin = shutil.which("docker")
    if not docker_bin:
        log("  [!] Docker no detectado en PATH; asumiendo servicios externos activos.", YELLOW)
        return

    containers = [
        ("hse-postgres", 5432, "PostgreSQL 16"),
        ("novasync-n8n", 5678, "n8n Workflow Engine")
    ]

    for name, port, desc in containers:
        try:
            inspect_res = subprocess.run(
                [docker_bin, "inspect", "-f", "{{.State.Running}}", name],
                capture_output=True,
                text=True,
                check=False
            )
            is_running = inspect_res.stdout.strip() == "true"
            if is_running:
                log(f"  ✓ Contenedor {name} ({desc}) en ejecución en puerto {port}.", GREEN)
            else:
                log(f"  Iniciando contenedor {name}...", YELLOW)
                subprocess.run([docker_bin, "start", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                log(f"  ✓ {name} levantado con éxito.", GREEN)
        except Exception as e:
            log(f"  [!] No se pudo verificar {name}: {e}", YELLOW)


def get_python_cmd():
    """Detecta el intérprete Python adecuado según el SO (Windows vs Unix)."""
    if sys.platform == "win32":
        candidates = [
            PROJECT_ROOT / "strata-core" / ".venv" / "Scripts" / "python.exe",
            PROJECT_ROOT / "strata-core" / ".venv" / "python.exe",
            PROJECT_ROOT / ".venv" / "Scripts" / "python.exe",
        ]
    else:
        candidates = [
            PROJECT_ROOT / "strata-core" / ".venv" / "bin" / "python3",
            PROJECT_ROOT / "strata-core" / ".venv" / "bin" / "python",
            PROJECT_ROOT / ".venv" / "bin" / "python3",
        ]

    for c in candidates:
        if c.is_file():
            return str(c)

    return sys.executable


def terminate_all():
    """Finaliza limpiamente todos los subprocesos iniciados."""
    log("\nDeteniendo servicios del ecosistema...", YELLOW)
    for p, name in processes:
        if p.poll() is None:
            log(f"  Deteniendo {name} (PID: {p.pid})...", YELLOW)
            try:
                if sys.platform == "win32":
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    p.terminate()
                    p.wait(timeout=2)
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass
    log("✓ Todos los servicios se han detenido correctamente.\n", GREEN)


def signal_handler(sig, frame):
    terminate_all()
    sys.exit(0)


def main():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print()
    log("  ================================================================", PURPLE, True)
    log("    RIWI HSE - SISTEMA DE AUTOMATIZACION Y GESTION DE JUSTIFICACIONES", PURPLE, True)
    log("  ================================================================", PURPLE, True)
    print()

    # 1. Docker
    check_docker()

    # 2. Python Interpreter
    log("[2/5] Configurando intérprete Python...", CYAN)
    py_cmd = get_python_cmd()
    log(f"  ✓ Intérprete Python: {py_cmd}", GREEN)

    # 3. Backend Strata Core
    log("[3/5] Levantando Backend Strata Core en puerto 8001...", CYAN)
    strata_dir = PROJECT_ROOT / "strata-core"
    backend_proc = subprocess.Popen(
        [py_cmd, "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001", "--reload"],
        cwd=str(strata_dir)
    )
    processes.append((backend_proc, "Backend Strata Core (FastAPI:8001)"))
    time.sleep(2)

    # 4. Frontend Vite
    log("[4/5] Levantando Frontend (Vite + React) en puerto 5173...", CYAN)
    frontend_dir = PROJECT_ROOT / "frontend"
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    frontend_proc = subprocess.Popen(
        [npm_cmd, "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"],
        cwd=str(frontend_dir)
    )
    processes.append((frontend_proc, "Frontend Vite (Puerto 5173)"))
    time.sleep(2)

    # 5. Escuchador en vivo de Gmail
    log("[5/5] Levantando Escuchador en vivo de Gmail (IMAP)...", CYAN)
    listener_script = PROJECT_ROOT / "scripts" / "gmail_live_listener.py"
    listener_proc = subprocess.Popen(
        [py_cmd, str(listener_script)],
        cwd=str(PROJECT_ROOT)
    )
    processes.append((listener_proc, "Escuchador de Gmail (IMAP)"))

    print()
    log("================================================================", GREEN, True)
    log("  ✓ ECOSISTEMA RIWI HSE LEVANTADO Y LISTO PARA PRUEBAS          ", GREEN, True)
    log("================================================================", GREEN, True)
    log("  🖥️  Frontend Tablero HSE:    http://localhost:5173", BLUE, True)
    log("  📋 Bandeja de Solicitudes:  http://localhost:5173/requests", BLUE, True)
    log("  👥 Directorio de Coders:    http://localhost:5173/students", BLUE, True)
    log("  ⚡ Backend Strata Core API: http://localhost:8001/docs", BLUE, True)
    log("  🔄 Orquestador n8n:         http://localhost:5678", BLUE, True)
    log("  🗄️  PostgreSQL Database:     localhost:5432 (hse_email_automation)", BLUE, True)
    log("  📨 Escuchador de Gmail:     Activo en tiempo real", BLUE, True)
    log("================================================================", GREEN, False)
    log("Presiona Ctrl+C en cualquier momento para detener todos los servicios.\n", YELLOW)

    try:
        while True:
            # Monitorear estado de subprocesos
            for p, name in processes:
                code = p.poll()
                if code is not None and code != 0:
                    log(f"[!] Aviso: {name} finalizó inesperadamente con código {code}", RED)
            time.sleep(1)
    except KeyboardInterrupt:
        terminate_all()
        sys.exit(0)


if __name__ == "__main__":
    main()
