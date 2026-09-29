@echo off
REM =============================================================================
REM RIWI - SISTEMA AUTOMATIZADO DE JUSTIFICACIONES HSE
REM Launcher Universal para Windows CMD / Batch
REM Uso: run.bat  (o simplemente run)
REM =============================================================================

cd /d "%~dp0"

REM 1. Verificar si Python está instalado para usar el runner universal
where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    python run.py %*
    goto :eof
)

REM 2. Si no hay Python en PATH, intentar PowerShell
where powershell >nul 2>nul
if %ERRORLEVEL% equ 0 (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run.ps1" %*
    goto :eof
)

echo [X] Error: No se encontro ni Python ni PowerShell en el sistema.
pause
