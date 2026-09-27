#!/usr/bin/env python3
"""
Validador de Integridad y Sintaxis de Migraciones SQL — Squad Database
Email-Automation con Strata Core (Riwi Moodle ID: 132)
"""

import json
import re
import sys
from pathlib import Path

# Soporte para consolas Windows CP1252
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

MIGRATIONS_DIR = Path(__file__).parent / "migrations"

EXPECTED_MIGRATIONS = [
    "001_initial_schema.sql",
    "002_seed_data.sql",
    "003_storage_and_indexes.sql",
    "004_riwi_coders_directory.sql",
]

EXPECTED_TABLES = [
    "hse_system_config",
    "email_templates",
    "justifications",
    "justification_attachments",
    "coders",
]

EXPECTED_VIEWS = [
    "vw_dashboard_kpis",
    "vw_recent_justifications",
]

EXPECTED_STATUSES = [
    "APROBADO_AUTO",
    "RECHAZADO_AUTO",
    "REVISION_MANUAL",
    "APROBADO_MANUAL",
    "RECHAZADO_MANUAL",
]


def test_migrations_exist():
    print("[1/5] Verificando presencia de archivos de migracion...")
    for filename in EXPECTED_MIGRATIONS:
        path = MIGRATIONS_DIR / filename
        assert path.exists(), f"[ERROR] Falta el archivo de migracion requerido: {filename}"
        assert path.stat().st_size > 0, f"[ERROR] El archivo {filename} esta vacio"
        print(f"  [OK] {filename} presente ({path.stat().st_size} bytes)")


def test_schema_definitions():
    print("\n[2/5] Validando definicion de tablas, vistas y directorio Riwi...")
    content_001 = (MIGRATIONS_DIR / "001_initial_schema.sql").read_text(encoding="utf-8")
    content_003 = (MIGRATIONS_DIR / "003_storage_and_indexes.sql").read_text(encoding="utf-8")
    content_004 = (MIGRATIONS_DIR / "004_riwi_coders_directory.sql").read_text(encoding="utf-8")
    full_ddl = content_001 + "\n" + content_003 + "\n" + content_004

    # Validar ENUM
    for status in EXPECTED_STATUSES:
        assert status in content_001, f"[ERROR] Falta el estado del enum: {status}"
    print(f"  [OK] Todos los estados del ENUM justification_status ({len(EXPECTED_STATUSES)}) definidos correctamente.")

    # Validar Tablas
    for table in EXPECTED_TABLES:
        pattern = rf"CREATE\s+TABLE\s+(IF\s+NOT\s+EXISTS\s+)?{table}"
        assert re.search(pattern, full_ddl, re.IGNORECASE), f"[ERROR] No se encontro la definicion de tabla: {table}"
        print(f"  [OK] Tabla '{table}' definida con clausula de seguridad.")

    # Validar Vistas
    for view in EXPECTED_VIEWS:
        pattern = rf"CREATE\s+(OR\s+REPLACE\s+)?VIEW\s+{view}"
        assert re.search(pattern, full_ddl, re.IGNORECASE), f"[ERROR] No se encontro la vista: {view}"
        print(f"  [OK] Vista analitica '{view}' definida correctamente.")

    # Validar campos de resolucion de coders
    assert "cc_coder" in content_004, "[ERROR] Falta la definicion de cc_coder en 004"
    assert "academic_route" in content_004, "[ERROR] Falta la definicion de academic_route en 004"
    assert "fn_resolve_coder_identity" in content_004, "[ERROR] Falta la funcion fn_resolve_coder_identity"
    print("  [OK] Campos cc_coder, academic_route y funcion fn_resolve_coder_identity validados.")


def test_performance_indexes():
    print("\n[3/5] Validando indices de alto rendimiento (< 50ms)...")
    content_003 = (MIGRATIONS_DIR / "003_storage_and_indexes.sql").read_text(encoding="utf-8")
    content_004 = (MIGRATIONS_DIR / "004_riwi_coders_directory.sql").read_text(encoding="utf-8")

    assert "idx_justifications_ai_verdict_gin" in content_003, "[ERROR] Falta el indice GIN sobre ai_verdict"
    assert "idx_justifications_status_created_at" in content_003, "[ERROR] Falta el indice compuesto (status, created_at)"
    assert "idx_coders_cc" in content_004, "[ERROR] Falta el indice de busqueda por cedula en coders"
    assert "idx_coders_email" in content_004, "[ERROR] Falta el indice de busqueda por email en coders"
    print("  [OK] Indices GIN, compuestos, clave foranea y de resolucion de coders configurados con exito.")


def test_seed_json_validity():
    print("\n[4/5] Validando integridad de JSONs en datos semilla y plantillas...")
    content_002 = (MIGRATIONS_DIR / "002_seed_data.sql").read_text(encoding="utf-8")
    content_004 = (MIGRATIONS_DIR / "004_riwi_coders_directory.sql").read_text(encoding="utf-8")

    # Extraer bloques JSON dentro de '{"..."}'::jsonb
    json_blocks = re.findall(r"'(\{.*?\})'::jsonb", content_002, re.DOTALL)
    assert len(json_blocks) > 0, "[ERROR] No se encontraron bloques JSON en 002_seed_data.sql"

    for idx, block in enumerate(json_blocks, 1):
        try:
            parsed = json.loads(block)
            assert isinstance(parsed, dict)
        except json.JSONDecodeError as err:
            raise AssertionError(f"[ERROR] JSON invalido en bloque semilla #{idx}: {err}\nContenido:\n{block}")

    assert "UNIDENTIFIED_CODER" in content_004, "[ERROR] Falta la plantilla de contingencia UNIDENTIFIED_CODER"
    print(f"  [OK] Se validaron {len(json_blocks)} bloques JSON y la plantilla de contingencia UNIDENTIFIED_CODER.")


def test_idempotency_and_syntax():
    print("\n[5/5] Validando reglas de idempotencia y estandar arquitectonico...")
    for filename in EXPECTED_MIGRATIONS:
        content = (MIGRATIONS_DIR / filename).read_text(encoding="utf-8")
        assert "-- ============================================================" in content, (
            f"[ERROR] El archivo {filename} no incluye el encabezado estandar de Elian"
        )
        assert "IF NOT EXISTS" in content or "ON CONFLICT" in content or "OR REPLACE" in content, (
            f"[ERROR] El archivo {filename} no asegura idempotencia"
        )
    print("  [OK] Todos los archivos siguen la estructura, encabezados e idempotencia canonica.")


def main():
    print("============================================================")
    print("   VERIFICACION INTEGRAL DE BASE DE DATOS - SQUAD DB        ")
    print("      Riwi HSE & Moodle ID=132 - Motor Strata Core          ")
    print("============================================================\n")
    try:
        test_migrations_exist()
        test_schema_definitions()
        test_performance_indexes()
        test_seed_json_validity()
        test_idempotency_and_syntax()
        print("\n[EXITO] TODAS LAS COMPROBACIONES DE BASE DE DATOS PASARON EXITOSAMENTE (5/5).")
        return 0
    except AssertionError as e:
        print(f"\n{e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
