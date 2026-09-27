#!/usr/bin/env python3
"""
Importador de Coders Reales de Riwi (Moodle ID: 132)
Procesa courseid_132_participants.xlsx y genera 005_real_riwi_coders.sql
"""

import sys
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from pathlib import Path

# Soporte para consolas Windows CP1252
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

EXCEL_PATH = Path(r"C:\Users\SOPORTE\Downloads\courseid_132_participants.xlsx")
OUTPUT_SQL = Path(__file__).parent / "migrations" / "005_real_riwi_coders.sql"


def clean_text(text: str) -> str:
    if not text:
        return ""
    # Quitar caracteres invisibles y espacios extras
    return " ".join(text.strip().split())


def strip_accents(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def generate_email(nombre: str, apellido: str, used_emails: set) -> str:
    # Obtener primer nombre y primer apellido
    n_part = strip_accents(nombre.split()[0]).lower() if nombre else "coder"
    a_part = strip_accents(apellido.split()[0]).lower() if apellido else "riwi"
    
    # Sanitizar caracteres que no sean alfanuméricos
    n_part = "".join(c for c in n_part if c.isalnum())
    a_part = "".join(c for c in a_part if c.isalnum())
    
    base_email = f"{n_part}.{a_part}@riwi.io"
    email = base_email
    counter = 2
    while email in used_emails:
        email = f"{n_part}.{a_part}{counter}@riwi.io"
        counter += 1
    used_emails.add(email)
    return email


def map_route(grupo: str) -> str:
    g = grupo.lower()
    if "ia" in g or "automatizaci" in g:
        return "Automatización con IA"
    elif "typescript" in g:
        return "TypeScript Fullstack"
    elif "anal" in g or "datos" in g:
        return "Analítica de Datos & BI"
    elif "c#" in g or "net" in g:
        return ".NET / C# Backend"
    elif "nodejs" in g or "node" in g:
        return "Node.js Backend"
    elif "java" in g:
        return "Java Spring Boot"
    elif "bpo" in g or "retiro" in g:
        return "BPO / Retiros"
    elif not grupo:
        return "Sin Asignar"
    return grupo


def main():
    print("============================================================")
    print("   IMPORTADOR DE CODERS REALES RIWI (MOODLE 132)           ")
    print("============================================================\n")

    if not EXCEL_PATH.exists():
        print(f"[ERROR] No se encontró el archivo: {EXCEL_PATH}")
        sys.exit(1)

    print(f"Leyendo archivo Excel: {EXCEL_PATH}...")
    with zipfile.ZipFile(EXCEL_PATH) as z:
        sheet_xml = z.read("xl/worksheets/sheet1.xml")
        tree = ET.fromstring(sheet_xml)
        ns = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        rows = tree.findall(".//main:row", ns)

    print(f"Total filas encontradas en el archivo: {len(rows)}")
    header = rows[0]
    data_rows = rows[1:]

    coders = []
    used_emails = set()
    used_ccs = set()
    groups_counter = Counter()

    for idx, r in enumerate(data_rows, 1):
        cells = r.findall(".//main:c", ns)
        vals = []
        for c in cells:
            t = c.find(".//main:t", ns)
            v = c.find(".//main:v", ns)
            val = t.text if t is not None and t.text else (v.text if v is not None and v.text else "")
            vals.append(clean_text(val))

        if len(vals) >= 2:
            nombre = vals[0]
            apellido = vals[1]
            grupo = vals[2] if len(vals) > 2 else "Sin grupo"
            if not grupo:
                grupo = "Sin grupo"

            nombre_completo = f"{nombre} {apellido}".strip()
            email = generate_email(nombre, apellido, used_emails)
            route = map_route(grupo)
            moodle_id = f"132_{idx:03d}"

            # Cédula determinística inicial (10 dígitos colombiana)
            cc_base = 1000000000 + idx
            while str(cc_base) in used_ccs:
                cc_base += 1
            cc = str(cc_base)
            used_ccs.add(cc)

            groups_counter[grupo] += 1
            coders.append({
                "moodle_id": moodle_id,
                "name": nombre_completo,
                "cc": cc,
                "email": email,
                "route": route,
                "group": grupo,
            })

    print(f"\n[OK] Se procesaron {len(coders)} coders reales.")
    print("Distribución de Grupos y Rutas en Riwi:")
    for grp, count in groups_counter.most_common():
        print(f"  • {grp}: {count} coders")

    # Generar la migración SQL 005
    sql_lines = [
        "-- ============================================================",
        "-- Migración 005: Siembra de los 297 Coders Reales de Riwi (Moodle 132)",
        "-- Proyecto: Email-Automation con Strata Core",
        "-- Descripción:",
        f"--   Inserta los {len(coders)} estudiantes activos del curso 132 de Riwi Moodle,",
        "--   sus rutas técnicas, jornadas (AM/PM), correos oficiales @riwi.io",
        "--   y actualiza el catálogo de rutas en hse_system_config.",
        "-- ============================================================\n",
        "-- 1. Catálogo oficial de Rutas y Grupos de Riwi en la configuración dinámica",
        "INSERT INTO hse_system_config (key, value, description)",
        "VALUES (",
        "    'academic_routes_and_groups',",
        "    '{\"routes\": [\"Automatización con IA\", \"TypeScript Fullstack\", \"Analítica de Datos & BI\", \".NET / C# Backend\", \"Node.js Backend\", \"Java Spring Boot\", \"BPO / Retiros\"], \"groups\": [\"Automatización con IA AM\", \"TypeScript AM\", \"Analítica de datos AM\", \"C# PM\", \"NodeJS AM\", \"Java PM\", \"NodeJS PM\", \"BPO/Retiros\"]}'::jsonb,",
        "    'Listado de rutas técnicas y grupos oficiales de formación activa en Riwi'",
        ")",
        "ON CONFLICT (key) DO UPDATE",
        "SET value = EXCLUDED.value,",
        "    description = EXCLUDED.description,",
        "    updated_at = NOW();\n",
        "-- 2. Inserción Masiva Idempotente de los 297 Coders Reales",
        "INSERT INTO coders (moodle_id, name_coder, cc_coder, email_coder, academic_route, cohort_group)",
        "VALUES",
    ]

    values_entries = []
    for c in coders:
        # Escapar comillas simples en nombres (ej. D'Angelo)
        name_esc = c["name"].replace("'", "''")
        route_esc = c["route"].replace("'", "''")
        group_esc = c["group"].replace("'", "''")
        entry = f"    ('{c['moodle_id']}', '{name_esc}', '{c['cc']}', '{c['email']}', '{route_esc}', '{group_esc}')"
        values_entries.append(entry)

    sql_lines.append(",\n".join(values_entries))
    sql_lines.append(
        "ON CONFLICT (email_coder) DO UPDATE\n"
        "SET name_coder = EXCLUDED.name_coder,\n"
        "    academic_route = EXCLUDED.academic_route,\n"
        "    cohort_group = EXCLUDED.cohort_group,\n"
        "    updated_at = NOW();\n"
    )

    OUTPUT_SQL.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_SQL.write_text("\n".join(sql_lines), encoding="utf-8")
    print(f"\n[EXITO] Archivo de migración generado exitosamente:")
    print(f"  👉 {OUTPUT_SQL} ({OUTPUT_SQL.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
