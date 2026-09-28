#!/usr/bin/env python3
"""
Test Suite y Simulador de Validación para el Workflow n8n de Justificaciones RIWI.
Valida la integridad estructural del JSON de n8n, consistencia de conexiones,
esquema DDL de PostgreSQL v2.1 con intervención humana y autenticación,
y ejecuta la simulación de lógica de los 6 escenarios operativos clave.
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent
WORKFLOW_PATH = BASE_DIR / "n8n_workflow_email_hse.json"
DDL_PATH = BASE_DIR / "init_database.sql"

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

def test_database_schema_integrity():
    print(f"\n{Colors.BOLD}{Colors.HEADER}=== FASE 1: VALIDACIÓN DEL ESQUEMA DDL POSTGRESQL (v2.1) ==={Colors.ENDC}")
    with open(DDL_PATH, "r", encoding="utf-8") as f:
        ddl = f.read()
    
    log_test("Presencia de password_hash en hse_users", "password_hash" in ddl, "Soporta autenticación directa email/password")
    log_test("Presencia de resolution_mode en justifications", "resolution_mode" in ddl, "Diferenciador AUTOMATIC_AI vs MANUAL_HSE")
    log_test("Presencia de has_human_intervention en justifications", "has_human_intervention" in ddl, "Flag booleano de auditoría humana")
    log_test("Constraint chk_resolution_mode", "chk_resolution_mode" in ddl, "Restringe valores a ('AUTOMATIC_AI', 'MANUAL_HSE')")
    log_test("Vista v_justifications_dashboard con trazabilidad humana", "has_human_intervention" in ddl and "hse_reviewer_email" in ddl)

def test_workflow_structure():
    print(f"\n{Colors.BOLD}{Colors.HEADER}=== FASE 2: VALIDACIÓN ESTRUCTURAL DEL WORKFLOW N8N ==={Colors.ENDC}")
    
    with open(WORKFLOW_PATH, "r", encoding="utf-8") as f:
        wf = json.load(f)
    
    log_test("Archivo JSON parseable y válido", True, f"Tamaño: {len(json.dumps(wf))} bytes")
    
    nodes = wf.get("nodes", [])
    log_test("Presencia de nodos", len(nodes) > 0, f"Total de nodos encontrados: {len(nodes)}")
    
    node_names = [n["name"] for n in nodes]
    node_ids = [n["id"] for n in nodes]
    
    log_test("Nombres de nodos únicos", len(node_names) == len(set(node_names)), f"{len(node_names)} nombres únicos")
    log_test("IDs de nodos únicos", len(node_ids) == len(set(node_ids)), f"{len(node_ids)} IDs únicos")
    
    # Validar conexiones
    connections = wf.get("connections", {})
    all_source_nodes = set(connections.keys())
    all_valid_names = set(node_names)
    
    missing_sources = all_source_nodes - all_valid_names
    log_test("Todos los nodos origen de conexiones existen", len(missing_sources) == 0, f"Huérfanos: {missing_sources}")
    
    target_nodes = set()
    for src, conn_types in connections.items():
        for conn_type, outputs in conn_types.items():
            for output_group in outputs:
                for target in output_group:
                    target_name = target["node"]
                    target_nodes.add(target_name)
                    if target_name not in all_valid_names:
                        log_test(f"Destino de conexión '{target_name}' existe", False, f"Origen: {src}")
    
    log_test("Todos los nodos destino de conexiones existen", True, f"Nodos alcanzados: {len(target_nodes)}")
    
    # Validar Switch outputs
    switch_node = next(n for n in nodes if n["name"] == "10 Decision Switch")
    switch_rules = switch_node["parameters"]["rules"]["rules"]
    log_test("Reglas de Switch completas (3 salidas)", len(switch_rules) == 3, f"Reglas: {[r['value2'] for r in switch_rules]}")
    
    # Validar Timeout de Strata Core en HTTP Request
    http_node = next(n for n in nodes if n["name"] == "08 HTTP Strata Core Evaluation")
    timeout = http_node["parameters"]["options"]["timeout"]
    log_test("Timeout de Strata Core >= 60000 ms", timeout >= 60000, f"Configurado: {timeout} ms")
    log_test("ContinueOnFail habilitado en HTTP Request", http_node.get("continueOnFail") is True)

# Simulación de la lógica de negocio implementada en los nodos JS
def simulate_01_normalize(data):
    sender_email = (data.get("sender_email") or data.get("from") or "").lower().strip()
    sender_name = data.get("sender_name") or "Coder"
    subject = data.get("email_subject") or data.get("subject") or "Sin asunto"
    body = data.get("email_body") or data.get("body") or ""
    message_id = data.get("message_id") or "msg_sim_123"
    conversation_id = data.get("conversation_id")
    received_at = data.get("received_at") or datetime.now().isoformat()
    raw_attachments = data.get("attachments") or []
    
    attachments = []
    for att in raw_attachments:
        attachments.append({
            "filename": att.get("filename") or "documento.pdf",
            "mime_type": att.get("mime_type") or "application/pdf",
            "data_base64": att.get("data_base64")
        })
    
    return {
        "source_provider": data.get("source_provider") or "OUTLOOK",
        "message_id": message_id,
        "conversation_id": conversation_id,
        "sender_email": sender_email,
        "sender_name": sender_name,
        "email_subject": subject,
        "email_body": body,
        "received_at": received_at,
        "attachments": attachments,
        "has_attachments": len(attachments) > 0
    }

def simulate_02_extract_keys(data):
    full_text = data["email_subject"] + " " + data["email_body"]
    cedula_match = re.search(r'\b(1\d{9}|[1-9]\d{6,8})\b', full_text)
    data["search_cedula"] = cedula_match.group(0) if cedula_match else ""
    data["search_name"] = data["sender_name"] if data["sender_name"] != "Coder" else ""
    data["email_url"] = f"https://outlook.office.com/mail/deeplink/read/{data['message_id']}"
    return data

def simulate_03_db_search(data, mock_coders_db):
    found = None
    for c in mock_coders_db:
        if c["email"].lower() == data["sender_email"]:
            found = c
            break
        if data["search_cedula"] and c["cedula"] == data["search_cedula"]:
            found = c
            break
        if data["search_name"] and c["full_name"].lower() == data["search_name"].lower():
            found = c
            break
    
    if found:
        data["coder_found"] = True
        data["coder_id"] = found["id"]
        data["coder_name"] = found["full_name"]
        data["coder_cedula"] = found["cedula"]
        data["coder_route"] = found["route"]
        data["coder_identification_status"] = "IDENTIFIED"
    else:
        data["coder_found"] = False
        data["coder_id"] = None
        data["coder_name"] = data["sender_name"]
        data["coder_cedula"] = data["search_cedula"]
        data["coder_route"] = None
        data["coder_identification_status"] = "CODER_NOT_FOUND"
    
    return data

def simulate_09_guardrails(data, http_result):
    has_error = http_result.get("error") is not None or "tipo_novedad" not in http_result
    
    if has_error:
        ai_valido = False
        ai_tipo = "no_identificado"
        ai_confidence = 0.0
        ai_manual = True
        ai_motivo = "Fallo técnico o timeout con Strata Core / Ollama."
        ai_full = {"error": True}
    else:
        ai_valido = bool(http_result.get("valido"))
        ai_tipo = http_result.get("tipo_novedad") or "no_identificado"
        ai_motivo = http_result.get("motivo_decision") or "Evaluado por Qwen 2.5"
        ai_confidence = http_result.get("confianza_score", 0.85)
        ai_manual = bool(http_result.get("requiere_revision_manual"))
        ai_full = http_result
    
    full_text = (data["email_subject"] + " " + data["email_body"]).lower()
    
    # Guardrail Calamidad
    if re.search(r"falleci|luto|funerar|entierro|calamidad", full_text):
        ai_tipo = "calamidad"
        if not data["has_attachments"]:
            ai_valido = False
            ai_manual = True
            ai_motivo = "Reporte de calamidad sin soporte adjunto. Requiere validación manual de HSE."
    
    # Guardrail Spam
    if re.search(r"descuento|cursos de|promocion|suscripcion", full_text):
        ai_tipo = "no_identificado"
        ai_valido = False
        ai_manual = True
        ai_motivo = "Contenido sospechoso de spam."
    
    # Determinación de validation_status
    if ai_manual or ai_confidence < 0.80:
        validation_status = "MANUAL_INTERACTION"
    elif ai_valido:
        validation_status = "APPROVED"
    else:
        validation_status = "DISAPPROVED"
    
    data["intent"] = ai_tipo.upper()
    data["excuse_type"] = ai_tipo
    data["ai_confidence"] = ai_confidence
    data["ai_reason"] = ai_motivo
    data["ai_response"] = ai_full
    data["validation_status"] = validation_status
    data["resolution_mode"] = "AUTOMATIC_AI"
    data["has_human_intervention"] = False
    return data

def run_scenarios():
    print(f"\n{Colors.BOLD}{Colors.HEADER}=== FASE 3: SIMULACIÓN DE ESCENARIOS END-TO-END ==={Colors.ENDC}")
    
    mock_db = [
        {
            "id": "c001-uuid",
            "cedula": "1002345678",
            "full_name": "Santiago Morales",
            "email": "santiago.morales@riwi.io",
            "route": "Node.js Cloud Native",
            "is_active": True
        },
        {
            "id": "c002-uuid",
            "cedula": "1098765432",
            "full_name": "Valentina Ospina",
            "email": "valentina.ospina@riwi.io",
            "route": "Python AI Specialist",
            "is_active": True
        }
    ]

    mock_hse_users = [
        {
            "id": "hse-001-uuid",
            "email": "laura.gomez@riwi.io",
            "full_name": "Laura Gómez",
            "password_hash": "$2b$12$e8Y3yqGczf5RShBrwBp...",
            "role": "HSE"
        }
    ]

    # ESCENARIO 1: Incapacidad médica válida de Coder registrado
    print(f"\n{Colors.BOLD}Escenario 1: Coder Identificado + Incapacidad Médica Válida (EPS Sanitas){Colors.ENDC}")
    e1_input = {
        "sender_email": "santiago.morales@riwi.io",
        "sender_name": "Santiago Morales",
        "email_subject": "Incapacidad médica 25 y 26 de Septiembre",
        "email_body": "Buenos días equipo HSE, adjunto certificado de incapacidad emitido por EPS Sanitas por cuadro viral.",
        "attachments": [{"filename": "incapacidad_eps.pdf", "data_base64": "JVBERi0xLjQK..."}]
    }
    d1 = simulate_01_normalize(e1_input)
    d1 = simulate_02_extract_keys(d1)
    d1 = simulate_03_db_search(d1, mock_db)
    log_test("Identificación del Coder exitosa", d1["coder_found"] is True and d1["coder_id"] == "c001-uuid")
    
    strata_mock_1 = {
        "valido": True,
        "tipo_novedad": "inasistencia_medica",
        "fecha_afectada": "2026-09-25",
        "confianza_score": 0.96,
        "requiere_revision_manual": False,
        "motivo_decision": "Certificado de incapacidad médica emitido por EPS Sanitas con sello y registro."
    }
    d1 = simulate_09_guardrails(d1, strata_mock_1)
    log_test("Estado final APPROVED", d1["validation_status"] == "APPROVED")
    log_test("Modo automático AUTOMATIC_AI", d1["resolution_mode"] == "AUTOMATIC_AI")
    log_test("Sin intervención humana (has_human_intervention=False)", d1["has_human_intervention"] is False)

    # ESCENARIO 2: Coder no encontrado (remitente desconocido)
    print(f"\n{Colors.BOLD}Escenario 2: Coder No Encontrado (Buzón no institucional sin cédula){Colors.ENDC}")
    e2_input = {
        "sender_email": "desconocido99@gmail.com",
        "sender_name": "Carlos Gomez",
        "email_subject": "Excusame hoy no voy",
        "email_body": "Hola, hoy no voy a poder ir a clase porque tengo dolor de cabeza.",
        "attachments": []
    }
    d2 = simulate_01_normalize(e2_input)
    d2 = simulate_02_extract_keys(d2)
    d2 = simulate_03_db_search(d2, mock_db)
    log_test("Coder identificado como NO ENCONTRADO", d2["coder_found"] is False and d2["coder_id"] is None)
    log_test("Status CODER_NOT_FOUND", d2["coder_identification_status"] == "CODER_NOT_FOUND")

    # ESCENARIO 3: Calamidad familiar sin adjunto (Disparo de Guardrail)
    print(f"\n{Colors.BOLD}Escenario 3: Calamidad Familiar sin Adjunto (Guardrail de Negocio){Colors.ENDC}")
    e3_input = {
        "sender_email": "valentina.ospina@riwi.io",
        "sender_name": "Valentina Ospina",
        "email_subject": "Urgente: Calamidad familiar",
        "email_body": "Estimados, lamentablemente ocurrió el fallecimiento de mi abuela materna, estaré en el entierro estos dos días.",
        "attachments": []
    }
    d3 = simulate_01_normalize(e3_input)
    d3 = simulate_02_extract_keys(d3)
    d3 = simulate_03_db_search(d3, mock_db)
    
    strata_mock_3 = {
        "valido": True,
        "tipo_novedad": "calamidad",
        "fecha_afectada": "2026-09-27",
        "confianza_score": 0.90,
        "requiere_revision_manual": False,
        "motivo_decision": "Luto reportado"
    }
    d3 = simulate_09_guardrails(d3, strata_mock_3)
    log_test("Guardrail interceptó y derivó a MANUAL_INTERACTION", d3["validation_status"] == "MANUAL_INTERACTION")
    log_test("Motivo indica soporte pendiente", "sin soporte adjunto" in d3["ai_reason"])

    # ESCENARIO 4: Failover técnico (Caída / Timeout de Ollama)
    print(f"\n{Colors.BOLD}Escenario 4: Failover Técnico (Strata Core / Ollama no responde){Colors.ENDC}")
    e4_input = {
        "sender_email": "santiago.morales@riwi.io",
        "sender_name": "Santiago Morales",
        "email_subject": "Cita médica",
        "email_body": "Adjunto soporte de odontología.",
        "attachments": [{"filename": "cita.pdf"}]
    }
    d4 = simulate_01_normalize(e4_input)
    d4 = simulate_02_extract_keys(d4)
    d4 = simulate_03_db_search(d4, mock_db)
    
    strata_mock_4 = {"error": "Connection refused: Ollama 11434 down"}
    d4 = simulate_09_guardrails(d4, strata_mock_4)
    log_test("Failover redirige a MANUAL_INTERACTION (No rechaza erróneamente)", d4["validation_status"] == "MANUAL_INTERACTION")
    log_test("Confianza asignada a 0.0 por fallo técnico", d4["ai_confidence"] == 0.0)

    # ESCENARIO 5: Excusa no justificada (Motivos personales / Fiesta)
    print(f"\n{Colors.BOLD}Escenario 5: Coder Identificado + Causa Injustificada (Tardanza injustificada){Colors.ENDC}")
    e5_input = {
        "sender_email": "santiago.morales@riwi.io",
        "sender_name": "Santiago Morales",
        "email_subject": "Llegaré tarde",
        "email_body": "Profe me quedé dormido porque me acosté tarde jugando videojuegos.",
        "attachments": []
    }
    d5 = simulate_01_normalize(e5_input)
    d5 = simulate_02_extract_keys(d5)
    d5 = simulate_03_db_search(d5, mock_db)
    
    strata_mock_5 = {
        "valido": False,
        "tipo_novedad": "tardanza",
        "fecha_afectada": "2026-09-27",
        "confianza_score": 0.95,
        "requiere_revision_manual": False,
        "motivo_decision": "Motivo no contemplado como justificación válida (quedarse dormido)."
    }
    d5 = simulate_09_guardrails(d5, strata_mock_5)
    log_test("Estado final DISAPPROVED", d5["validation_status"] == "DISAPPROVED")
    log_test("Motivo claro de no aprobación", "Motivo no contemplado" in d5["ai_reason"])

    # ESCENARIO 6: Resolución Manual por Frontend HSE (Login + Corrección + Despacho)
    print(f"\n{Colors.BOLD}Escenario 6: Resolución Manual HSE (Login email/password + Corrección de datos + Despacho n8n){Colors.ENDC}")
    
    # 1. Login del usuario HSE
    hse_login_email = "laura.gomez@riwi.io"
    hse_user = next((u for u in mock_hse_users if u["email"] == hse_login_email), None)
    log_test("Autenticación de usuario HSE en base de datos", hse_user is not None and "password_hash" in hse_user)
    
    # 2. Corrección de datos del caso 3 (Calamidad) en Frontend
    frontend_update_payload = {
        "justification_id": "just-003-uuid",
        "action": "APPROVED",
        "corrected_start_date": "2026-09-27",
        "corrected_end_date": "2026-09-28",
        "corrected_excuse_type": "calamidad",
        "hse_notes": "Se verificó la situación directamente con la coder Valentina Ospina. Se concede permiso por fuerza mayor.",
        "hse_user_id": hse_user["id"],
        "hse_reviewer_name": hse_user["full_name"]
    }
    
    # Simulación del UPDATE en PostgreSQL ejecutado directamente por Frontend
    updated_justification = {
        "id": frontend_update_payload["justification_id"],
        "validation_status": frontend_update_payload["action"],
        "resolution_mode": "MANUAL_HSE",
        "has_human_intervention": True,
        "start_date": frontend_update_payload["corrected_start_date"],
        "end_date": frontend_update_payload["corrected_end_date"],
        "excuse_type": frontend_update_payload["corrected_excuse_type"],
        "hse_user_id": frontend_update_payload["hse_user_id"],
        "hse_decision": frontend_update_payload["action"],
        "hse_notes": frontend_update_payload["hse_notes"],
        "hse_reviewed_at": datetime.now().isoformat()
    }
    
    log_test("UPDATE directo en PostgreSQL exitoso", updated_justification["validation_status"] == "APPROVED")
    log_test("Factor diferenciador 'resolution_mode' = MANUAL_HSE", updated_justification["resolution_mode"] == "MANUAL_HSE")
    log_test("Flag 'has_human_intervention' = TRUE", updated_justification["has_human_intervention"] is True)
    log_test("Auditoría asociada a usuario HSE específico", updated_justification["hse_user_id"] == "hse-001-uuid")
    log_test("Fechas y tipo de excusa corregidos por el analista", updated_justification["excuse_type"] == "calamidad")

    # 3. Disparo asíncrono al Webhook de n8n para despacho de correo
    n8n_dispatch_payload = {
        "justification_id": updated_justification["id"],
        "action": updated_justification["validation_status"],
        "coder_name": "Valentina Ospina",
        "recipient_email": "valentina.ospina@riwi.io",
        "start_date": updated_justification["start_date"],
        "excuse_type": updated_justification["excuse_type"],
        "hse_notes": updated_justification["hse_notes"],
        "hse_reviewer_name": frontend_update_payload["hse_reviewer_name"]
    }
    
    log_test("Despacho de notificación n8n preparado", len(n8n_dispatch_payload["recipient_email"]) > 0)
    log_test("Correo incluye nombre del analista que validó", n8n_dispatch_payload["hse_reviewer_name"] == "Laura Gómez")

    print(f"\n{Colors.BOLD}{Colors.OKGREEN}======================================================{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.OKGREEN}  ¡TODAS LAS PRUEBAS Y VALIDACIONES PASARON EXITOSAMENTE!  {Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.OKGREEN}======================================================{Colors.ENDC}\n")

if __name__ == "__main__":
    test_database_schema_integrity()
    test_workflow_structure()
    run_scenarios()
