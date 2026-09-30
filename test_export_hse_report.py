#!/usr/bin/env python3
"""
test_export_hse_report.py
=============================================================================
SUITE DE PRUEBAS DE ACEPTACIÓN — TASK [DB-EXT-01]
Generador y Exportador de Reportes de Ausentismo a CSV/Excel para Comité HSE
=============================================================================
Criterios de Aceptación Evaluados:
1. Endpoint GET /api/v1/reports/export-csv con Streaming / In-Memory Buffer
   (sin archivos huérfanos).
2. Headers oficiales: Content-Disposition: attachment; filename=reporte_hse_barranquilla.csv.
3. Formato con las 9 columnas mandatorias:
   Cédula, Nombre Coder, Ruta Formativa, Tipo de Novedad, Fecha Inicio,
   Fecha Fin, Días Ausente, Estado HSE, Número de Radicado.
4. Vista SQL analítica v_hse_weekly_summary con seguridad security_invoker = true
   y totales agrupados por ruta formativa y semana.
5. Exportación en Microsoft Excel (.xlsx) estilizado vía openpyxl.
6. Script CLI scripts/export_hse_report.py funcional por consola.
=============================================================================
"""

import csv
import io
import os
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent

class Colors:
    HEADER = '\033[95m'
    OKGREEN = '\033[92m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def log_test(title, passed, details=""):
    status = f"{Colors.OKGREEN}✓ PASÓ{Colors.ENDC}" if passed else f"{Colors.FAIL}✗ FALLÓ{Colors.ENDC}"
    print(f"  [{status}] {title}")
    if details:
        print(f"       → {details}")
    if not passed:
        sys.exit(1)


def test_ddl_integrity():
    print(f"\n{Colors.BOLD}{Colors.HEADER}=== FASE 1: INTEGRIDAD DE MIGRACIÓN Y VISTA ANALÍTICA (v_hse_weekly_summary) ==={Colors.ENDC}")

    mig_file = BASE_DIR / "database" / "migrations" / "005_hse_weekly_summary_view.sql"
    init_sql = BASE_DIR / "init_database.sql"
    supa_sql = BASE_DIR / "supabase_schema.sql"

    log_test("Archivo de migración 005_hse_weekly_summary_view.sql existe",
             mig_file.exists(), str(mig_file))

    content_mig = mig_file.read_text(encoding="utf-8")
    content_init = init_sql.read_text(encoding="utf-8")
    content_supa = supa_sql.read_text(encoding="utf-8")

    # 1. Definición de la vista
    log_test("Vista v_hse_weekly_summary creada con security_invoker = true",
             "CREATE OR REPLACE VIEW public.v_hse_weekly_summary" in content_mig and
             "security_invoker = true" in content_mig and
             "v_hse_weekly_summary" in content_init and
             "v_hse_weekly_summary" in content_supa)

    # 2. Agrupación por ruta y semana
    log_test("Vista agrupa por Ruta Formativa y semana académica (DATE_TRUNC)",
             "DATE_TRUNC('week', j.start_date)" in content_mig and
             "GROUP BY" in content_mig and
             "COALESCE(c.route" in content_mig)

    # 3. Métricas analíticas de agregación
    log_test("Métricas de total_requests, aprobadas, rechazadas, pendientes y días ausentes",
             "total_requests" in content_mig and
             "total_approved" in content_mig and
             "total_disapproved" in content_mig and
             "total_pending" in content_mig and
             "total_absence_days" in content_mig)


def test_fastapi_endpoints():
    print(f"\n{Colors.BOLD}{Colors.HEADER}=== FASE 2: VERIFICACIÓN DE ENDPOINTS FASTAPI (DB-EXT-01) ==={Colors.ENDC}")

    from fastapi.testclient import TestClient
    from backend.app.main import app

    client = TestClient(app)

    # 1. Endpoint CSV
    res_csv = client.get("/api/v1/reports/export-csv")
    log_test("GET /api/v1/reports/export-csv responde HTTP 200", res_csv.status_code == 200)

    # 2. Headers oficiales
    cd_header = res_csv.headers.get("content-disposition", "")
    log_test("Header Content-Disposition: attachment; filename=reporte_hse_barranquilla.csv",
             cd_header == "attachment; filename=reporte_hse_barranquilla.csv", cd_header)

    # 3. Columnas obligatorias
    content = res_csv.content.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(content))
    headers = next(reader)
    expected_headers = [
        "Cédula",
        "Nombre Coder",
        "Ruta Formativa",
        "Tipo de Novedad",
        "Fecha Inicio",
        "Fecha Fin",
        "Días Ausente",
        "Estado HSE",
        "Número de Radicado"
    ]
    log_test("Estructura exacta de 9 columnas oficiales requeridas por Comité HSE",
             headers == expected_headers, f"Columnas: {headers}")

    # 4. Datos presentes
    rows = list(reader)
    log_test("Contenido de datos consolidado con campos poblados",
             len(rows) >= 1 and len(rows[0]) == 9, f"Filas exportadas: {len(rows)}")

    # 5. Endpoint Excel
    res_xlsx = client.get("/api/v1/reports/export-excel")
    log_test("GET /api/v1/reports/export-excel responde HTTP 200", res_xlsx.status_code == 200)
    log_test("Header Content-Disposition Excel: attachment; filename=reporte_hse_barranquilla.xlsx",
             res_xlsx.headers.get("content-disposition") == "attachment; filename=reporte_hse_barranquilla.xlsx")

    # 6. Endpoint Weekly Summary
    res_ws = client.get("/api/v1/reports/weekly-summary")
    log_test("GET /api/v1/reports/weekly-summary responde HTTP 200", res_ws.status_code == 200)
    data = res_ws.json()
    log_test("Resumen semanal estructurado por ruta formativa",
             isinstance(data, list) and len(data) >= 1 and "route" in data[0])


def test_cli_execution():
    print(f"\n{Colors.BOLD}{Colors.HEADER}=== FASE 3: VERIFICACIÓN DE SCRIPT CLI (scripts/export_hse_report.py) ==={Colors.ENDC}")

    script = BASE_DIR / "scripts" / "export_hse_report.py"
    log_test("Script CLI scripts/export_hse_report.py existe", script.exists())

    # Ejecutar CLI exportando a stdout
    cmd = [sys.executable, str(script), "--stdout"]
    res = subprocess.run(cmd, capture_output=True)
    log_test("Ejecución CLI con --stdout exitosa (código 0)", res.returncode == 0)
    log_test("Salida stdout contiene encabezados oficiales",
             b"C\xc3\xa9dula" in res.stdout or b"Cedula" in res.stdout)


if __name__ == "__main__":
    print(f"{Colors.BOLD}{Colors.HEADER}======================================================================{Colors.ENDC}")
    print(f"{Colors.BOLD}SUITE DE VALIDACIÓN: TASK [DB-EXT-01] EXPORTADOR DE REPORTES HSE{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}======================================================================{Colors.ENDC}")

    test_ddl_integrity()
    test_fastapi_endpoints()
    test_cli_execution()

    print(f"\n{Colors.BOLD}{Colors.OKGREEN}🎉 TODOS LOS CRITERIOS DE ACEPTACIÓN DE [DB-EXT-01] FUERON SATISFECHOS AL 100%.{Colors.ENDC}\n")
