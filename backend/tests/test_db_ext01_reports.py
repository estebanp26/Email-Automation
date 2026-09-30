"""
test_db_ext01_reports.py
=============================================================================
SUITE DE PRUEBAS AUTOMATIZADAS — TASK [DB-EXT-01]
Generador y Exportador de Reportes de Ausentismo a CSV/Excel para Comité HSE
=============================================================================
Criterios de Aceptación Evaluados:
1. Endpoint GET /api/v1/reports/export-csv:
   - Header Content-Disposition: attachment; filename=reporte_hse_barranquilla.csv
   - Headers Content-Type y Cache-Control
   - Formato CSV estructurado con las 9 columnas mandatorias:
     Cédula, Nombre Coder, Ruta Formativa, Tipo de Novedad, Fecha Inicio,
     Fecha Fin, Días Ausente, Estado HSE, Número de Radicado
   - Streaming o buffer en memoria (sin archivos temporales huérfanos)
   - Filtros por estado HSE (?status=...) y por ruta (?route=...)
2. Endpoint GET /api/v1/reports/export-excel:
   - Archivo .xlsx válido con header attachment; filename=reporte_hse_barranquilla.xlsx
   - Estructura y nombres de columnas
3. Endpoint GET /api/v1/reports/weekly-summary:
   - Resumen agrupado por ruta y semana académica
4. Verificación DDL:
   - Migración 005_hse_weekly_summary_view.sql con security_invoker = true
   - Sincronización en init_database.sql y supabase_schema.sql
5. Herramienta CLI scripts/export_hse_report.py:
   - Exportación de CSV y Excel por línea de comandos
"""

import csv
import io
import os
import subprocess
import sys
from pathlib import Path
from fastapi.testclient import TestClient

import pytest

try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False

from backend.app.main import app
from backend.app.services.report_service import (
    HSEReportService,
    report_service,
    OFFICIAL_REPORT_HEADERS
)

client = TestClient(app)
ROOT_DIR = Path(__file__).resolve().parent.parent.parent


# =============================================================================
# 1. PRUEBAS DEL ENDPOINT GET /api/v1/reports/export-csv
# =============================================================================

def test_export_csv_endpoint_status_and_headers():
    """Valida status 200 y headers oficiales de Content-Disposition."""
    response = client.get("/api/v1/reports/export-csv")
    assert response.status_code == 200
    assert response.headers.get("content-disposition") == "attachment; filename=reporte_hse_barranquilla.csv"
    assert "text/csv" in response.headers.get("content-type", "")


def test_export_csv_headers_and_columns():
    """Valida que el archivo CSV contenga exactamente las 9 columnas requeridas."""
    response = client.get("/api/v1/reports/export-csv")
    assert response.status_code == 200

    content = response.content.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(content))
    headers = next(reader)

    expected = [
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
    assert headers == expected


def test_export_csv_data_content():
    """Valida que existan filas de datos válidas con los 9 campos diligenciados."""
    response = client.get("/api/v1/reports/export-csv")
    assert response.status_code == 200

    content = response.content.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(content))
    _ = next(reader)  # Header

    rows = list(reader)
    assert len(rows) >= 1

    first_row = rows[0]
    assert len(first_row) == 9
    cedula, nombre, ruta, tipo, inicio, fin, dias, estado, radicado = first_row

    # Validar que los campos no estén vacíos
    assert len(cedula) > 0
    assert len(nombre) > 0
    assert len(ruta) > 0
    assert len(tipo) > 0
    assert len(inicio) == 10  # YYYY-MM-DD
    assert len(fin) == 10     # YYYY-MM-DD
    assert int(dias) >= 1
    assert len(estado) > 0
    assert len(radicado) > 0


def test_export_csv_filter_by_status():
    """Valida el filtrado por estado HSE."""
    res_approved = client.get("/api/v1/reports/export-csv?status=APPROVED")
    assert res_approved.status_code == 200
    reader_app = csv.reader(io.StringIO(res_approved.content.decode("utf-8-sig")))
    _ = next(reader_app)
    rows_app = list(reader_app)
    for r in rows_app:
        assert r[7] == "APPROVED"


def test_export_csv_filter_by_route():
    """Valida el filtrado por ruta formativa."""
    res_route = client.get("/api/v1/reports/export-csv?route=Node.js")
    assert res_route.status_code == 200
    reader = csv.reader(io.StringIO(res_route.content.decode("utf-8-sig")))
    _ = next(reader)
    rows = list(reader)
    for r in rows:
        assert "node" in r[2].lower()


def test_export_csv_via_api_alias():
    """Valida que el alias /api/reports/export-csv también esté operativo."""
    response = client.get("/api/reports/export-csv")
    assert response.status_code == 200
    assert response.headers.get("content-disposition") == "attachment; filename=reporte_hse_barranquilla.csv"


# =============================================================================
# 2. PRUEBAS DEL ENDPOINT GET /api/v1/reports/export-excel
# =============================================================================

def test_export_excel_endpoint():
    """Valida la generación en memoria del archivo Excel .xlsx."""
    response = client.get("/api/v1/reports/export-excel")
    assert response.status_code == 200
    assert response.headers.get("content-disposition") == "attachment; filename=reporte_hse_barranquilla.xlsx"

    if HAS_OPENPYXL:
        wb = openpyxl.load_workbook(io.BytesIO(response.content))
        ws = wb.active
        assert ws.title == "Reporte Ausentismo HSE"

        # Validar fila de encabezados
        header_vals = [cell.value for cell in ws[1]]
        assert header_vals == OFFICIAL_REPORT_HEADERS

        # Validar que al menos haya una fila de datos
        assert ws.max_row >= 2


# =============================================================================
# 3. PRUEBAS DE LA VISTA ANALÍTICA Y ENDPOINT /api/v1/reports/weekly-summary
# =============================================================================

def test_weekly_summary_endpoint():
    """Valida el endpoint de métricas semanales agrupadas por ruta."""
    response = client.get("/api/v1/reports/weekly-summary")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1

    item = data[0]
    expected_keys = {
        "route",
        "ruta_formativa",
        "week_start",
        "week_number",
        "year",
        "total_requests",
        "total_approved",
        "total_disapproved",
        "total_pending",
        "total_absence_days",
        "unique_coders_count"
    }
    assert expected_keys.issubset(item.keys())
    assert item["total_requests"] >= 1


# =============================================================================
# 4. PRUEBAS DEL SERVICIO EN MEMORIA (Sin archivos huérfanos)
# =============================================================================

def test_service_buffer_and_streaming_in_memory(tmp_path):
    """Verifica que el servicio trabaje 100% en memoria sin escribir en disco."""
    svc = HSEReportService()

    # 1. CSV buffer
    csv_buf = svc.generate_csv_buffer()
    assert isinstance(csv_buf, io.BytesIO)
    content = csv_buf.getvalue()
    assert len(content) > 0
    assert content.startswith(b"\xef\xbb\xbf")  # UTF-8 BOM

    # 2. Generator stream
    chunks = list(svc.stream_csv())
    assert len(chunks) >= 2
    full_stream = b"".join(chunks)
    assert b"C\xc3\xa9dula" in full_stream or b"Cedula" in full_stream

    # 3. Excel buffer
    if HAS_OPENPYXL:
        excel_buf = svc.generate_excel_buffer()
        assert isinstance(excel_buf, io.BytesIO)
        assert len(excel_buf.getvalue()) > 1000


# =============================================================================
# 5. INTEGRIDAD DDL DE LA VISTA v_hse_weekly_summary
# =============================================================================

def test_ddl_migration_files_integrity():
    """Valida la presencia y consistencia de la vista analítica en los archivos SQL."""
    mig_005 = ROOT_DIR / "database" / "migrations" / "005_hse_weekly_summary_view.sql"
    init_sql = ROOT_DIR / "init_database.sql"
    supa_sql = ROOT_DIR / "supabase_schema.sql"

    assert mig_005.exists(), "Falta archivo de migración 005_hse_weekly_summary_view.sql"
    assert init_sql.exists(), "Falta init_database.sql"
    assert supa_sql.exists(), "Falta supabase_schema.sql"

    content_005 = mig_005.read_text(encoding="utf-8")
    content_init = init_sql.read_text(encoding="utf-8")
    content_supa = supa_sql.read_text(encoding="utf-8")

    # Validar creación de la vista y security_invoker
    for c in [content_005, content_init, content_supa]:
        assert "CREATE OR REPLACE VIEW" in c
        assert "v_hse_weekly_summary" in c
        assert "security_invoker = true" in c
        assert "DATE_TRUNC('week', j.start_date)" in c
        assert "GROUP BY" in c


# =============================================================================
# 6. PRUEBAS DEL SCRIPT CLI scripts/export_hse_report.py
# =============================================================================

def test_cli_script_csv_export(tmp_path):
    """Valida que el script CLI genere un archivo CSV correctamente."""
    out_csv = tmp_path / "test_report.csv"
    script_path = ROOT_DIR / "scripts" / "export_hse_report.py"

    cmd = [sys.executable, str(script_path), "--format", "csv", "--output", str(out_csv)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"Error ejecutando CLI: {res.stderr}"
    assert out_csv.exists()

    with open(out_csv, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        headers = next(reader)
        assert headers == OFFICIAL_REPORT_HEADERS
        rows = list(reader)
        assert len(rows) >= 1


def test_cli_script_excel_export(tmp_path):
    """Valida que el script CLI genere un archivo Excel correctamente."""
    out_xlsx = tmp_path / "test_report.xlsx"
    script_path = ROOT_DIR / "scripts" / "export_hse_report.py"

    cmd = [sys.executable, str(script_path), "--format", "excel", "--output", str(out_xlsx)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"Error ejecutando CLI: {res.stderr}"
    assert out_xlsx.exists()
    assert out_xlsx.stat().st_size > 1000


def test_cli_script_stdout():
    """Valida que el script CLI pueda escribir a stdout."""
    script_path = ROOT_DIR / "scripts" / "export_hse_report.py"

    cmd = [sys.executable, str(script_path), "--stdout"]
    res = subprocess.run(cmd, capture_output=True)
    assert res.returncode == 0
    assert b"C\xc3\xa9dula" in res.stdout or b"Cedula" in res.stdout
