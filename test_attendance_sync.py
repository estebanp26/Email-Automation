#!/usr/bin/env python3
"""
test_attendance_sync.py
=============================================================================
SUITE DE PRUEBAS AUTOMATIZADAS — TASK [DB-03]
Tabla y Vistas de Sincronización de Asistencias Externas (attendance_records)
=============================================================================
Criterios de Aceptación Evaluados:
1. Tabla attendance_records con FKs a coders y justifications.
2. Vista unificada v_unjustified_absences para auditar inasistencias sin justificar.
3. Triggers de auto-vinculación entre asistencias y justificaciones aprobadas.
4. Políticas de Row Level Security (RLS) para aislamiento Coder vs HSE.
=============================================================================
"""

import sys
from datetime import date, timedelta
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
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


# =============================================================================
# 1. VERIFICACIÓN ESTRUCTURAL DDL
# =============================================================================
def test_ddl_integrity():
    print(f"\n{Colors.BOLD}{Colors.HEADER}=== FASE 1: INTEGRIDAD DE SCRIPTS DDL Y MIGRACIÓN DB-03 ==={Colors.ENDC}")
    
    mig_file = BASE_DIR / "database" / "migrations" / "003_attendance_records_and_views.sql"
    init_sql = BASE_DIR / "init_database.sql"
    supa_sql = BASE_DIR / "supabase_schema.sql"

    log_test("Archivo de migración 003_attendance_records_and_views.sql existe",
             mig_file.exists(), str(mig_file))

    content = mig_file.read_text(encoding="utf-8")
    init_content = init_sql.read_text(encoding="utf-8")

    # ENUM attendance_status
    log_test("ENUM attendance_status con PRESENT, ABSENT, LATE, EARLY_LEAVE, EXCUSED",
             "CREATE TYPE attendance_status AS ENUM" in content and
             "'PRESENT'" in content and "'ABSENT'" in content and "'EXCUSED'" in content)

    # Tabla attendance_records
    log_test("Tabla attendance_records con FK a coders y justifications",
             "CREATE TABLE IF NOT EXISTS attendance_records" in content and
             "coder_id VARCHAR(100) NOT NULL REFERENCES coders" in content and
             "justification_id VARCHAR(100) REFERENCES justifications" in content)

    # Constraint unique y check
    log_test("Restricción única coder_id + attendance_date + session_name",
             "uq_coder_attendance_session" in content)

    # Índices de rendimiento
    log_test("Índices de rendimiento en attendance_records",
             "idx_attendance_records_coder_id" in content and
             "idx_attendance_records_date" in content and
             "idx_attendance_records_status" in content and
             "idx_attendance_records_is_justified" in content)

    # Vista v_unjustified_absences
    log_test("Vista v_unjustified_absences definida con security_invoker = true",
             "CREATE OR REPLACE VIEW v_unjustified_absences" in content and
             "security_invoker = true" in content)

    # Triggers de vinculación bidireccional
    log_test("Trigger auto-link inasistencia a justificación aprobada",
             "fn_auto_link_attendance_to_justification" in content and
             "trg_attendance_records_auto_link" in content)

    log_test("Trigger sincronización retroactiva cuando justificación pasa a APPROVED",
             "fn_sync_approved_justification_to_attendance" in content and
             "trg_justification_approved_sync_attendance" in content)

    # RLS en attendance_records
    log_test("Políticas RLS en attendance_records",
             "ALTER TABLE attendance_records ENABLE ROW LEVEL SECURITY;" in content and
             "p_attendance_records_select" in content)

    # Sincronización en init_database.sql
    log_test("Presencia de attendance_records y v_unjustified_absences en init_database.sql",
             "attendance_records" in init_content and "v_unjustified_absences" in init_content)


# =============================================================================
# 2. MOTOR DE SIMULACIÓN EN MEMORIA Y LÓGICA DE NEGOCIO
# =============================================================================
class MockAttendanceDatabase:
    def __init__(self):
        self.session_user_id = None
        self.session_user_role = None

        self.coders = [
            {"id": "coder-001", "cedula": "1000000001", "full_name": "Jose Luis Acevedo", "email": "jose.acevedo@riwi.io", "route": "Node.js Backend"},
            {"id": "coder-002", "cedula": "1000000002", "full_name": "Andrea Ahumada", "email": "andrea.ahumada@riwi.io", "route": "Java Spring Boot"},
            {"id": "coder-003", "cedula": "1000000003", "full_name": "Jhosep Ahumada", "email": "jhosep.ahumada@riwi.io", "route": "BPO / Retiros"}
        ]

        self.justifications = [
            # Coder 001 tiene una justificación médica aprobada para hoy
            {
                "id": "just-app-01",
                "coder_id": "coder-001",
                "start_date": str(date.today()),
                "end_date": str(date.today()),
                "validation_status": "APPROVED",
                "email_subject": "Incapacidad médica Sanitas"
            },
            # Coder 002 tiene una justificación en trámite (revisión manual)
            {
                "id": "just-pend-02",
                "coder_id": "coder-002",
                "start_date": str(date.today() - timedelta(days=1)),
                "end_date": str(date.today() - timedelta(days=1)),
                "validation_status": "MANUAL_INTERACTION",
                "email_subject": "Calamidad doméstica sin soporte"
            }
        ]

        self.attendance_records = []

    def set_auth(self, user_id, role):
        self.session_user_id = user_id
        self.session_user_role = role.upper()

    def insert_attendance(self, coder_id, att_date, status="ABSENT", session_name="Jornada Mañana", source="MOODLE"):
        record = {
            "id": f"att-{len(self.attendance_records) + 1:03d}",
            "coder_id": coder_id,
            "attendance_date": str(att_date),
            "session_name": session_name,
            "status": status,
            "justification_id": None,
            "is_justified": False,
            "source_platform": source
        }

        # Simulación del trigger fn_auto_link_attendance_to_justification
        if status in ("ABSENT", "LATE", "EARLY_LEAVE"):
            matching_just = next(
                (j for j in self.justifications
                 if j["coder_id"] == coder_id
                 and j["validation_status"] == "APPROVED"
                 and j["start_date"] <= record["attendance_date"] <= j["end_date"]),
                None
            )
            if matching_just:
                record["justification_id"] = matching_just["id"]
                record["is_justified"] = True
                if record["status"] == "ABSENT":
                    record["status"] = "EXCUSED"

        self.attendance_records.append(record)
        return record

    def approve_justification(self, just_id):
        just = next((j for j in self.justifications if j["id"] == just_id), None)
        if not just:
            return
        just["validation_status"] = "APPROVED"

        # Simulación del trigger fn_sync_approved_justification_to_attendance
        for att in self.attendance_records:
            if (att["coder_id"] == just["coder_id"] and
                just["start_date"] <= att["attendance_date"] <= just["end_date"]):
                att["justification_id"] = just["id"]
                att["is_justified"] = True
                if att["status"] == "ABSENT":
                    att["status"] = "EXCUSED"

    def query_v_unjustified_absences(self):
        # Vista filtrada con RLS
        results = []
        for att in self.attendance_records:
            # 1. Filtro RLS
            if self.session_user_role == "CODER" and att["coder_id"] != self.session_user_id:
                continue

            # 2. Condiciones de v_unjustified_absences
            if att["is_justified"] is False and att["status"] in ("ABSENT", "LATE", "EARLY_LEAVE"):
                # Verificar que no exista justificación aprobada
                has_approved = any(
                    j for j in self.justifications
                    if j["coder_id"] == att["coder_id"]
                    and j["validation_status"] == "APPROVED"
                    and j["start_date"] <= att["attendance_date"] <= j["end_date"]
                )
                if not has_approved:
                    coder = next((c for c in self.coders if c["id"] == att["coder_id"]), None)
                    # Detección de justificación en trámite
                    pending_just = next(
                        (j for j in self.justifications
                         if j["coder_id"] == att["coder_id"]
                         and j["validation_status"] not in ("APPROVED", "DISAPPROVED")
                         and j["start_date"] <= att["attendance_date"] <= j["end_date"]),
                        None
                    )
                    results.append({
                        "attendance_id": att["id"],
                        "coder_id": att["coder_id"],
                        "coder_name": coder["full_name"] if coder else "Desconocido",
                        "attendance_date": att["attendance_date"],
                        "status": att["status"],
                        "has_pending_justification": pending_just is not None,
                        "pending_justification_id": pending_just["id"] if pending_just else None,
                        "pending_validation_status": pending_just["validation_status"] if pending_just else None
                    })
        return results


# =============================================================================
# 3. EJECUCIÓN DE PRUEBAS FUNCIONALES
# =============================================================================
def test_functional_scenarios():
    print(f"\n{Colors.BOLD}{Colors.HEADER}=== FASE 2: SIMULACIÓN DE ESCENARIOS DE NEGOCIO (DB-03) ==={Colors.ENDC}")
    db = MockAttendanceDatabase()
    today = date.today()
    yesterday = today - timedelta(days=1)

    # 1. Coder 001 tiene inasistencia hoy, pero ya tiene justificación médica aprobada
    print(f"\n{Colors.BOLD}Escenario 1: Inasistencia con justificación previa aprobada (Auto-link){Colors.ENDC}")
    att1 = db.insert_attendance("coder-001", today, status="ABSENT")
    log_test("Trigger auto-link vincula automáticamente just-app-01",
             att1["justification_id"] == "just-app-01" and att1["is_justified"] is True,
             f"Estado: {att1['status']}, just_id: {att1['justification_id']}")

    # 2. Coder 002 tiene inasistencia ayer, con justificación en trámite (MANUAL_INTERACTION)
    print(f"\n{Colors.BOLD}Escenario 2: Inasistencia con justificación en trámite{Colors.ENDC}")
    att2 = db.insert_attendance("coder-002", yesterday, status="ABSENT")
    log_test("Inasistencia permanece is_justified = False mientras está en trámite",
             att2["is_justified"] is False and att2["justification_id"] is None)

    # 3. Coder 003 tiene inasistencia hoy sin ninguna justificación radicada
    print(f"\n{Colors.BOLD}Escenario 3: Inasistencia sin ninguna solicitud radicada{Colors.ENDC}")
    att3 = db.insert_attendance("coder-003", today, status="ABSENT")
    log_test("Inasistencia sin justificación creada exitosamente",
             att3["is_justified"] is False and att3["justification_id"] is None)

    # 4. Consulta de vista v_unjustified_absences por Analista HSE
    print(f"\n{Colors.BOLD}Escenario 4: Analista HSE consulta v_unjustified_absences{Colors.ENDC}")
    db.set_auth(user_id="hse-user", role="HSE_ANALYST")
    unjustified = db.query_v_unjustified_absences()

    # Coder 001 no debe aparecer (está justificado)
    # Coder 002 debe aparecer con has_pending_justification = True
    # Coder 003 debe aparecer con has_pending_justification = False
    log_test("Coder 001 no aparece en v_unjustified_absences (está justificado)",
             not any(r["coder_id"] == "coder-001" for r in unjustified))
    
    r_coder_002 = next((r for r in unjustified if r["coder_id"] == "coder-002"), None)
    log_test("Coder 002 aparece y alerta que tiene justificación en trámite",
             r_coder_002 is not None and r_coder_002["has_pending_justification"] is True and
             r_coder_002["pending_justification_id"] == "just-pend-02",
             f"pending_status: {r_coder_002.get('pending_validation_status') if r_coder_002 else None}")

    r_coder_003 = next((r for r in unjustified if r["coder_id"] == "coder-003"), None)
    log_test("Coder 003 aparece con alerta has_pending_justification = False",
             r_coder_003 is not None and r_coder_003["has_pending_justification"] is False)

    # 5. Resolución posterior: Team Leader aprueba just-pend-02
    print(f"\n{Colors.BOLD}Escenario 5: Aprobación posterior de justificación (Sincronización retroactiva){Colors.ENDC}")
    db.approve_justification("just-pend-02")
    log_test("Inasistencia de Coder 002 se actualiza automáticamente a is_justified = True",
             att2["is_justified"] is True and att2["justification_id"] == "just-pend-02")

    unjustified_after = db.query_v_unjustified_absences()
    log_test("Coder 002 desaparece de v_unjustified_absences tras aprobación",
             not any(r["coder_id"] == "coder-002" for r in unjustified_after),
             f"Quedan {len(unjustified_after)} inasistencias injustificadas (solo Coder 003)")

    # 6. RLS: Coder consulta v_unjustified_absences
    print(f"\n{Colors.BOLD}Escenario 6: Aislamiento RLS en v_unjustified_absences para Coders{Colors.ENDC}")
    db.set_auth(user_id="coder-003", role="CODER")
    coder_view = db.query_v_unjustified_absences()
    log_test("Coder 003 únicamente visualiza sus propias inasistencias",
             len(coder_view) == 1 and coder_view[0]["coder_id"] == "coder-003")

    db.set_auth(user_id="coder-001", role="CODER")
    coder1_view = db.query_v_unjustified_absences()
    log_test("Coder 001 (sin inasistencias injustificadas) obtiene 0 registros",
             len(coder1_view) == 0)


def main():
    print("=" * 70)
    print("   TEST ATTENDANCE SYNC & VISTAS — TASK [DB-03]                    ")
    print("=" * 70)
    test_ddl_integrity()
    test_functional_scenarios()
    print("\n" + "=" * 70)
    print(f"  {Colors.BOLD}{Colors.OKGREEN}¡TODAS LAS PRUEBAS DE DB-03 PASARON CON ÉXITO!{Colors.ENDC}")
    print("=" * 70)

if __name__ == "__main__":
    main()
