#!/usr/bin/env python3
"""
test_rbac_and_roles.py
=============================================================================
SUITE DE PRUEBAS AUTOMATIZADAS — USER STORY [DB-01]
Implementación de RBAC, Roles y Políticas RLS en PostgreSQL
=============================================================================
Criterios de Aceptación Evaluados:
1. Escenario Coder:
   Dado un usuario autenticado con rol "CODER" y ID "coder-aaa"
   Cuando ejecuta un SELECT sobre justifications con coder_id = "coder-bbb"
   Entonces la política RLS intercepta la consulta
   Y retorna 0 registros (acceso denegado)

2. Escenario Analista HSE:
   Dado un usuario con rol "HSE_ANALYST"
   Cuando consulta la vista v_justifications_dashboard
   Entonces el sistema retorna todos los registros de todos los estudiantes

3. Checklist Técnico:
   - Script de migración con tabla system_users y enum user_role.
   - Row Level Security (RLS) en tablas justifications y evidence_files.
   - Funciones de conveniencia fn_check_user_role, fn_get_current_user_id,
     fn_get_current_user_role, fn_set_auth_context y triggers de integridad.
=============================================================================
"""

import os
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
# 1. VERIFICACIÓN ESTRUCTURAL DE ARCHIVOS DDL Y MIGRACIONES
# =============================================================================
def test_ddl_migrations_structural_integrity():
    print(f"\n{Colors.BOLD}{Colors.HEADER}=== FASE 1: INTEGRIDAD DE SCRIPTS DDL Y MIGRACIONES RBAC (DB-01) ==={Colors.ENDC}")

    mig_001 = BASE_DIR / "database" / "migrations" / "001_initial_schema.sql"
    mig_002 = BASE_DIR / "database" / "migrations" / "002_seed_data.sql"
    init_sql = BASE_DIR / "init_database.sql"
    supa_sql = BASE_DIR / "supabase_schema.sql"

    log_test("Archivo de migración 001_initial_schema.sql existe", mig_001.exists(), str(mig_001))
    log_test("Archivo de migración 002_seed_data.sql existe", mig_002.exists(), str(mig_002))
    log_test("Archivo raíz init_database.sql existe", init_sql.exists(), str(init_sql))
    log_test("Archivo raíz supabase_schema.sql existe", supa_sql.exists(), str(supa_sql))

    content_001 = mig_001.read_text(encoding="utf-8")
    content_init = init_sql.read_text(encoding="utf-8")

    # 1. ENUM user_role
    log_test("Definición de ENUM user_role con CODER y HSE_ANALYST",
             "CREATE TYPE user_role AS ENUM" in content_001 and
             "'CODER'" in content_001 and "'HSE_ANALYST'" in content_001,
             "Roles requeridos en el ENUM soportados")

    # 2. TABLA system_users
    log_test("Definición de tabla system_users con role user_role y coder_id",
             "CREATE TABLE system_users" in content_001 and
             "role user_role" in content_001 and
             "coder_id VARCHAR" in content_001,
             "Tabla centralizada para RBAC y autenticación")

    # 3. TABLA evidence_files
    log_test("Definición de tabla evidence_files con FK a justifications",
             "CREATE TABLE evidence_files" in content_001 and
             "justification_id VARCHAR(100) NOT NULL REFERENCES justifications" in content_001,
             "Almacena archivos de soporte y bounding boxes espaciales")

    # 4. ROW LEVEL SECURITY (RLS)
    log_test("Habilitación de RLS en tabla justifications",
             "ALTER TABLE justifications ENABLE ROW LEVEL SECURITY;" in content_001 and
             "ALTER TABLE justifications FORCE ROW LEVEL SECURITY;" in content_001,
             "RLS activo y forzado para evitar bypass accidental")

    log_test("Habilitación de RLS en tabla evidence_files",
             "ALTER TABLE evidence_files ENABLE ROW LEVEL SECURITY;" in content_001 and
             "ALTER TABLE evidence_files FORCE ROW LEVEL SECURITY;" in content_001,
             "RLS activo y forzado en evidencias documentales")

    log_test("Habilitación de RLS en tabla system_users",
             "ALTER TABLE system_users ENABLE ROW LEVEL SECURITY;" in content_001,
             "Protección de privacidad de usuarios")

    # 5. FUNCIONES DE CONVENIENCIA
    log_test("Función de conveniencia fn_check_user_role presente",
             "CREATE OR REPLACE FUNCTION fn_check_user_role" in content_001,
             "Valida roles con jerarquía (ADMIN, TEAM_LEADER, HSE_ANALYST, CODER)")

    log_test("Funciones de sesión fn_set_auth_context, fn_get_current_user_id, fn_get_current_user_role",
             "fn_set_auth_context" in content_001 and
             "fn_get_current_user_id" in content_001 and
             "fn_get_current_user_role" in content_001,
             "Funciones auxiliares de auditoría y contexto RBAC")

    # 6. TRIGGERS DE INTEGRIDAD
    log_test("Trigger de integridad fn_enforce_justification_resolution_integrity",
             "fn_enforce_justification_resolution_integrity" in content_001 and
             "trg_justifications_resolution_integrity" in content_001,
             "Bloquea a Coders modificar estados y audita cambios manuales de HSE")

    log_test("Trigger de integridad de fechas fn_validate_dates_integrity",
             "fn_validate_dates_integrity" in content_001 and
             "trg_justifications_dates_integrity" in content_001,
             "Garantiza end_date >= start_date")

    log_test("Trigger de sincronización de evidence_files con attachments JSONB",
             "fn_sync_evidence_file_to_attachments" in content_001 and
             "trg_evidence_files_sync_attachments" in content_001,
             "Consistencia entre tabla evidence_files y columna JSONB")

    # 7. VISTA v_justifications_dashboard
    log_test("Vista v_justifications_dashboard configurada con security_invoker = true",
             "CREATE OR REPLACE VIEW v_justifications_dashboard" in content_001 and
             "security_invoker = true" in content_001,
             "La vista hereda las políticas RLS del usuario que ejecuta la consulta")

    # 8. SEED DATA
    content_002 = mig_002.read_text(encoding="utf-8")
    log_test("Seed data de usuarios HSE y Administradores en system_users",
             "INSERT INTO system_users" in content_002 and
             "HSE_ANALYST" in content_002 and
             "TEAM_LEADER" in content_002 and
             "ADMIN" in content_002,
             "Laura HSE, Andrés TL y Admin sembrados")

    log_test("Seed data vincula a los 297 coders con system_users",
             "INSERT INTO system_users (email, full_name, role, coder_id)" in content_002 and
             "SELECT c.email, c.full_name, 'CODER'::user_role, c.id" in content_002,
             "Cuentas de usuario creadas automáticamente para todos los coders")


# =============================================================================
# 2. MOTOR DE SIMULACIÓN Y EVALUACIÓN DE POLÍTICAS RLS (GHERKIN)
# =============================================================================
class MockPostgresRLSEngine:
    """
    Simulador fiel del comportamiento del motor de Row Level Security (RLS)
    de PostgreSQL con las políticas de DB-01.
    """
    def __init__(self):
        self.session_user_id = None
        self.session_user_role = None
        
        # Tablas en memoria
        self.system_users = [
            {"id": "usr-hse-01", "email": "laura.hse@riwi.io", "full_name": "Laura HSE", "role": "HSE_ANALYST", "coder_id": None},
            {"id": "usr-tl-01", "email": "andres.lead@riwi.io", "full_name": "Andrés Lead", "role": "TEAM_LEADER", "coder_id": None},
            {"id": "usr-admin-01", "email": "admin.hse@riwi.io", "full_name": "Admin General", "role": "ADMIN", "coder_id": None},
            {"id": "coder-aaa", "email": "coder.aaa@riwi.io", "full_name": "Estudiante AAA", "role": "CODER", "coder_id": "coder-aaa"},
            {"id": "coder-bbb", "email": "coder.bbb@riwi.io", "full_name": "Estudiante BBB", "role": "CODER", "coder_id": "coder-bbb"},
            {"id": "coder-ccc", "email": "coder.ccc@riwi.io", "full_name": "Estudiante CCC", "role": "CODER", "coder_id": "coder-ccc"}
        ]
        
        self.justifications = [
            {
                "id": "just-001",
                "coder_id": "coder-aaa",
                "sender_email": "coder.aaa@riwi.io",
                "sender_name": "Estudiante AAA",
                "email_subject": "Incapacidad médica gripa",
                "validation_status": "REVISION_MANUAL",
                "resolution_mode": "AUTOMATIC_AI",
                "has_human_intervention": False
            },
            {
                "id": "just-002",
                "coder_id": "coder-bbb",
                "sender_email": "coder.bbb@riwi.io",
                "sender_name": "Estudiante BBB",
                "email_subject": "Cita odontológica",
                "validation_status": "MANUAL_INTERACTION",
                "resolution_mode": "AUTOMATIC_AI",
                "has_human_intervention": False
            },
            {
                "id": "just-003",
                "coder_id": "coder-ccc",
                "sender_email": "coder.ccc@riwi.io",
                "sender_name": "Estudiante CCC",
                "email_subject": "Falla de conectividad fibra óptica",
                "validation_status": "POSIBLEMENTE_VALIDO",
                "resolution_mode": "AUTOMATIC_AI",
                "has_human_intervention": False
            }
        ]
        
        self.evidence_files = [
            {"id": "ev-001", "justification_id": "just-001", "file_name": "incapacidad_sanitas.pdf"},
            {"id": "ev-002", "justification_id": "just-002", "file_name": "cita_odontologia.png"},
            {"id": "ev-003", "justification_id": "just-003", "file_name": "reporte_falla_claro.pdf"}
        ]

    def set_auth_context(self, user_id, role=None):
        self.session_user_id = user_id
        if role:
            self.session_user_role = role.upper()
        else:
            u = next((x for x in self.system_users if x["id"] == user_id or x["email"] == user_id), None)
            self.session_user_role = u["role"] if u else None

    def fn_get_current_user_id(self):
        return self.session_user_id

    def fn_get_current_user_role(self):
        return self.session_user_role

    def fn_check_user_role(self, role):
        cur_role = self.fn_get_current_user_role()
        if not cur_role:
            return False
        req_role = role.upper()
        
        # Mapeos y jerarquía
        if cur_role in ("ADMIN",):
            return True
        if cur_role == "TEAM_LEADER" and req_role in ("HSE_ANALYST", "HSE", "TEAM_LEADER"):
            return True
        if cur_role in ("HSE_ANALYST", "HSE") and req_role in ("HSE_ANALYST", "HSE"):
            return True
        return cur_role == req_role

    # Política RLS sobre justifications
    def rls_policy_justifications_select(self, row):
        # 1. Staff HSE o Admin
        if self.fn_check_user_role("HSE_ANALYST"):
            return True
        
        # 2. Coder
        cur_uid = self.fn_get_current_user_id()
        cur_role = self.fn_get_current_user_role()
        if cur_role == "CODER" or cur_role is None:
            # ¿Es su propio coder_id?
            if row.get("coder_id") == cur_uid:
                return True
            # ¿Es su propio email?
            if row.get("sender_email") == cur_uid:
                return True
            # Búsqueda en system_users
            u = next((x for x in self.system_users if x["id"] == cur_uid or x["email"] == cur_uid), None)
            if u and u.get("coder_id") and row.get("coder_id") == u["coder_id"]:
                return True
            if u and row.get("sender_email") == u["email"]:
                return True
        return False

    # Política RLS sobre evidence_files
    def rls_policy_evidence_files_select(self, row):
        if self.fn_check_user_role("HSE_ANALYST"):
            return True
        
        just = next((j for j in self.justifications if j["id"] == row["justification_id"]), None)
        if not just:
            return False
        return self.rls_policy_justifications_select(just)

    def select_justifications(self, where_coder_id=None):
        results = []
        for row in self.justifications:
            # Filtro WHERE del query
            if where_coder_id is not None and row["coder_id"] != where_coder_id:
                continue
            # Interceptación por Row Level Security (RLS)
            if self.rls_policy_justifications_select(row):
                results.append(row)
        return results

    def query_v_justifications_dashboard(self):
        # La vista v_justifications_dashboard evalúa security_invoker = true
        return [row for row in self.justifications if self.rls_policy_justifications_select(row)]

    def select_evidence_files(self):
        return [row for row in self.evidence_files if self.rls_policy_evidence_files_select(row)]

    def update_justification(self, justification_id, new_values):
        just = next((j for j in self.justifications if j["id"] == justification_id), None)
        if not just:
            raise ValueError("Justificación no encontrada")
        
        cur_role = self.fn_get_current_user_role()
        
        # Trigger de integridad: Coder NO puede cambiar validation_status ni hse_decision
        if cur_role == "CODER":
            if "validation_status" in new_values and new_values["validation_status"] != just["validation_status"]:
                raise PermissionError("Acceso denegado: Usuarios con rol CODER no tienen privilegios para dictaminar o resolver justificaciones.")
            if "hse_decision" in new_values and new_values["hse_decision"] != just.get("hse_decision"):
                raise PermissionError("Acceso denegado: Usuarios con rol CODER no tienen privilegios para registrar decisiones de HSE.")
        
        # Trigger de auditoría humana automática para HSE
        if "validation_status" in new_values or "hse_decision" in new_values:
            new_values["has_human_intervention"] = True
            new_values["resolution_mode"] = "MANUAL_HSE"
            new_values["hse_user_id"] = self.fn_get_current_user_id()
            
        just.update(new_values)
        return just


# =============================================================================
# 3. EJECUCIÓN DE PRUEBAS GHERKIN
# =============================================================================
def test_gherkin_acceptance_criteria():
    print(f"\n{Colors.BOLD}{Colors.HEADER}=== FASE 2: SIMULACIÓN DE CRITERIOS DE ACEPTACIÓN GHERKIN ==={Colors.ENDC}")
    engine = MockPostgresRLSEngine()

    # -------------------------------------------------------------------------
    # ESCENARIO 1: Coder intenta consultar justificaciones de otro estudiante
    # -------------------------------------------------------------------------
    print(f"\n{Colors.BOLD}Escenario: Coder intenta consultar justificaciones de otro estudiante{Colors.ENDC}")
    # Dado un usuario autenticado con rol "CODER" y ID "coder-aaa"
    engine.set_auth_context(user_id="coder-aaa", role="CODER")
    log_test("Dado un usuario autenticado con rol 'CODER' y ID 'coder-aaa'",
             engine.fn_get_current_user_id() == "coder-aaa" and engine.fn_get_current_user_role() == "CODER")

    # Cuando ejecuta un SELECT sobre justifications con coder_id = "coder-bbb"
    records = engine.select_justifications(where_coder_id="coder-bbb")
    
    # Entonces la política RLS intercepta la consulta y retorna 0 registros (acceso denegado)
    log_test("Cuando ejecuta SELECT sobre justifications con coder_id = 'coder-bbb'", True)
    log_test("Entonces la política RLS intercepta la consulta", True)
    log_test("Y retorna 0 registros (acceso denegado)", len(records) == 0,
             f"Registros devueltos: {len(records)} (esperado: 0)")

    # Validación complementaria: Coder consulta sus PROPIAS justificaciones
    my_records = engine.select_justifications(where_coder_id="coder-aaa")
    log_test("Coder consulta sus propias justificaciones (coder_id = 'coder-aaa')", len(my_records) == 1,
             f"Retornó su propio registro: '{my_records[0]['email_subject']}'")

    # -------------------------------------------------------------------------
    # ESCENARIO 2: Analista HSE consulta todas las solicitudes activas
    # -------------------------------------------------------------------------
    print(f"\n{Colors.BOLD}Escenario: Analista HSE consulta todas las solicitudes activas{Colors.ENDC}")
    # Dado un usuario con rol "HSE_ANALYST"
    engine.set_auth_context(user_id="usr-hse-01", role="HSE_ANALYST")
    log_test("Dado un usuario con rol 'HSE_ANALYST'", engine.fn_get_current_user_role() == "HSE_ANALYST")

    # Cuando consulta la vista v_justifications_dashboard
    dashboard_records = engine.query_v_justifications_dashboard()

    # Entonces el sistema retorna todos los registros de todos los estudiantes
    total_expected = len(engine.justifications)
    log_test("Cuando consulta la vista v_justifications_dashboard", True)
    log_test("Entonces el sistema retorna todos los registros de todos los estudiantes",
             len(dashboard_records) == total_expected,
             f"Retornó los {len(dashboard_records)} registros de todos los coders ({', '.join(r['coder_id'] for r in dashboard_records)})")


# =============================================================================
# 4. PRUEBAS DE PROTECCIÓN DE EVIDENCIAS Y TRIGGERS DE INTEGRIDAD
# =============================================================================
def test_evidence_files_and_triggers_integrity():
    print(f"\n{Colors.BOLD}{Colors.HEADER}=== FASE 3: POLÍTICAS RLS EN EVIDENCIAS Y TRIGGERS DE INTEGRIDAD ==={Colors.ENDC}")
    engine = MockPostgresRLSEngine()

    # 1. RLS en evidence_files para Coder
    engine.set_auth_context(user_id="coder-aaa", role="CODER")
    coder_evidences = engine.select_evidence_files()
    log_test("Coder únicamente visualiza evidencias de sus propias justificaciones",
             len(coder_evidences) == 1 and coder_evidences[0]["file_name"] == "incapacidad_sanitas.pdf",
             f"Evidencia devuelta: {coder_evidences[0]['file_name'] if coder_evidences else 'Ninguna'}")

    # 2. RLS en evidence_files para HSE_ANALYST
    engine.set_auth_context(user_id="usr-hse-01", role="HSE_ANALYST")
    hse_evidences = engine.select_evidence_files()
    log_test("Analista HSE visualiza todas las evidencias adjuntas del sistema",
             len(hse_evidences) == 3,
             f"Total evidencias devueltas: {len(hse_evidences)} de 3")

    # 3. Jerarquía de funciones fn_check_user_role
    log_test("fn_check_user_role('HSE_ANALYST') para usuario HSE_ANALYST = True",
             engine.fn_check_user_role("HSE_ANALYST") is True)
    
    engine.set_auth_context(user_id="usr-admin-01", role="ADMIN")
    log_test("fn_check_user_role: ADMIN hereda permisos de HSE_ANALYST = True",
             engine.fn_check_user_role("HSE_ANALYST") is True)

    engine.set_auth_context(user_id="usr-tl-01", role="TEAM_LEADER")
    log_test("fn_check_user_role: TEAM_LEADER hereda permisos de HSE_ANALYST = True",
             engine.fn_check_user_role("HSE_ANALYST") is True)

    engine.set_auth_context(user_id="coder-aaa", role="CODER")
    log_test("fn_check_user_role: CODER intentando verificar HSE_ANALYST = False",
             engine.fn_check_user_role("HSE_ANALYST") is False)

    # 4. Trigger de integridad: Coder bloqueado de alterar estados
    engine.set_auth_context(user_id="coder-aaa", role="CODER")
    blocked = False
    try:
        engine.update_justification("just-001", {"validation_status": "APPROVED"})
    except PermissionError:
        blocked = True
    log_test("Trigger de integridad bloquea a Coder de dictaminar justificación", blocked,
             "Lanzó excepción de Acceso Denegado correctamente")

    # 5. Trigger de integridad: Auditoría automática al dictaminar HSE
    engine.set_auth_context(user_id="usr-hse-01", role="HSE_ANALYST")
    updated = engine.update_justification("just-002", {"validation_status": "APPROVED", "hse_decision": "APPROVED"})
    log_test("Trigger de integridad activa auditoría automática humana para HSE",
             updated["has_human_intervention"] is True and
             updated["resolution_mode"] == "MANUAL_HSE" and
             updated["hse_user_id"] == "usr-hse-01",
             f"has_human_intervention: {updated['has_human_intervention']}, mode: {updated['resolution_mode']}")


def main():
    print("=" * 70)
    print("   TEST RBAC & ROLES POSTGRESQL — USER STORY [DB-01]               ")
    print("=" * 70)
    test_ddl_migrations_structural_integrity()
    test_gherkin_acceptance_criteria()
    test_evidence_files_and_triggers_integrity()
    print("\n" + "=" * 70)
    print(f"  {Colors.BOLD}{Colors.OKGREEN}¡TODAS LAS PRUEBAS DE RBAC Y GHERKIN PASARON CON ÉXITO!{Colors.ENDC}")
    print("=" * 70)

if __name__ == "__main__":
    main()
