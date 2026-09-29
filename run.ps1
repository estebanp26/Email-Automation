# =============================================================================
# RIWI - SISTEMA AUTOMATIZADO DE JUSTIFICACIONES HSE
# Script de Inicio Unificado para PowerShell (Windows 10/11)
# Uso: .\run.ps1
# =============================================================================

$ErrorActionPreference = "Continue"
$ProjectRoot = $PSScriptRoot

Write-Host ""
Write-Host "  ================================================================" -ForegroundColor Magenta
Write-Host "    RIWI HSE - SISTEMA DE AUTOMATIZACION Y GESTION DE JUSTIFICACIONES" -ForegroundColor Magenta
Write-Host "  ================================================================" -ForegroundColor Magenta
Write-Host ""

# 1. Comprobación y activación de Docker
Write-Host "[1/5] Verificando contenedores Docker..." -ForegroundColor Cyan
if (Get-Command docker -ErrorAction SilentlyContinue) {
    # hse-postgres
    $pgState = docker inspect -f '{{.State.Running}}' hse-postgres 2>$null
    if ($pgState -eq "true") {
        Write-Host "  ✓ hse-postgres ya está en ejecución (Puerto 5432)" -ForegroundColor Green
    } else {
        Write-Host "  Iniciando contenedor hse-postgres..." -ForegroundColor Yellow
        docker start hse-postgres | Out-Null
    }

    # novasync-n8n
    $n8nState = docker inspect -f '{{.State.Running}}' novasync-n8n 2>$null
    if ($n8nState -eq "true") {
        Write-Host "  ✓ novasync-n8n ya está en ejecución (Puerto 5678)" -ForegroundColor Green
    } else {
        Write-Host "  Iniciando contenedor novasync-n8n..." -ForegroundColor Yellow
        docker start novasync-n8n | Out-Null
    }
} else {
    Write-Host "  [!] Docker no detectado en PATH; asumiendo servicios externos activos." -ForegroundColor Yellow
}

# 2. Detección del intérprete Python
Write-Host "[2/5] Configurando entorno Python para Backend Strata Core..." -ForegroundColor Cyan
$PythonCmd = "python"
$VenvCandidates = @(
    Join-Path $ProjectRoot "strata-core\.venv\Scripts\python.exe",
    Join-Path $ProjectRoot "strata-core\.venv\python.exe",
    Join-Path $ProjectRoot ".venv\Scripts\python.exe"
)

foreach ($cand in $VenvCandidates) {
    if (Test-Path $cand) {
        $PythonCmd = $cand
        break
    }
}
Write-Host "  ✓ Intérprete Python: $PythonCmd" -ForegroundColor Green

# 3. Lanzar procesos en segundo plano
$Processes = @()

# 3. Backend Strata Core
Write-Host "[3/5] Levantando Backend Strata Core en puerto 8001..." -ForegroundColor Cyan
$StrataDir = Join-Path $ProjectRoot "strata-core"
$backendProc = Start-Process -FilePath $PythonCmd -ArgumentList "-m uvicorn server:app --host 0.0.0.0 --port 8001 --reload" -WorkingDirectory $StrataDir -PassThru
$Processes += $backendProc
Start-Sleep -Seconds 2

# 4. Frontend Vite
Write-Host "[4/5] Levantando Frontend (Vite + React) en puerto 5173..." -ForegroundColor Cyan
$FrontendDir = Join-Path $ProjectRoot "frontend"
$frontendProc = Start-Process -FilePath "npm.cmd" -ArgumentList "run dev -- --host 0.0.0.0 --port 5173" -WorkingDirectory $FrontendDir -PassThru
$Processes += $frontendProc
Start-Sleep -Seconds 2

# 5. Escuchador de Gmail
Write-Host "[5/5] Levantando Escuchador en vivo de Gmail (IMAP)..." -ForegroundColor Cyan
$ListenerScript = Join-Path $ProjectRoot "scripts\gmail_live_listener.py"
$listenerProc = Start-Process -FilePath $PythonCmd -ArgumentList "`"$ListenerScript`"" -WorkingDirectory $ProjectRoot -PassThru
$Processes += $listenerProc

Write-Host ""
Write-Host "================================================================" -ForegroundColor Green
Write-Host "  ✓ ECOSISTEMA RIWI HSE LEVANTADO Y LISTO PARA PRUEBAS          " -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
Write-Host "  🖥️  Frontend Tablero HSE:    http://localhost:5173" -ForegroundColor Blue
Write-Host "  📋 Bandeja de Solicitudes:  http://localhost:5173/requests" -ForegroundColor Blue
Write-Host "  👥 Directorio de Coders:    http://localhost:5173/students" -ForegroundColor Blue
Write-Host "  ⚡ Backend Strata Core API: http://localhost:8001/docs" -ForegroundColor Blue
Write-Host "  🔄 Orquestador n8n:         http://localhost:5678" -ForegroundColor Blue
Write-Host "  🗄️  PostgreSQL Database:     localhost:5432 (hse_email_automation)" -ForegroundColor Blue
Write-Host "  📨 Escuchador de Gmail:     Activo en tiempo real" -ForegroundColor Blue
Write-Host "================================================================" -ForegroundColor Green
Write-Host "Presiona Ctrl+C en cualquier momento para detener todos los servicios.`n" -ForegroundColor Yellow

# Limpieza limpia al presionar Ctrl+C o cerrar
try {
    while ($true) {
        Start-Sleep -Seconds 1
    }
} finally {
    Write-Host "`nDeteniendo servicios del ecosistema..." -ForegroundColor Yellow
    foreach ($p in $Processes) {
        if (-not $p.HasExited) {
            Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
        }
    }
    Write-Host "✓ Todos los servicios se han detenido correctamente.`n" -ForegroundColor Green
}
