#!/usr/bin/env python3
"""
test_inbound_email.py
=============================================================================
SUITE DE PRUEBAS AUTOMATIZADAS — CONTROLADOR FASTAPI /api/v1/inbound-email
=============================================================================
Valida los criterios de aceptación (Gherkin) de la User Story de Ingesta Desacoplada:
1. Escenario: Recepción exitosa de correo desde adaptador de Outlook (HTTP 202 Accepted,
   encolado y estado PENDING_IDENTIFICATION).
2. Escenario: Detección y rechazo de payload duplicado / Idempotencia (HTTP 200 OK,
   mensaje "Event already processed", sin duplicación en BD).
3. Compatibilidad con eventos de Gmail (CONN-03 / Google PubSub).
4. Generación automática y determinista de message_id y conversation_id cuando no se proveen.
5. Almacenamiento seguro de adjuntos y protección contra Path Traversal.
6. Validación de esquemas con Pydantic e InboundEmailDTO (HTTP 422 ante payload inválido).
=============================================================================
"""

import os
import sys
import json
import base64
import hashlib
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

# Asegurar importación de strata-core
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import server
from schemas.inbound_dto import InboundEmailDTO, AttachmentDTO
from services.inbound_service import inbound_service


@pytest.fixture(autouse=True)
def reset_service_state():
    """Limpia el registro en memoria y registros de prueba en BD antes y después de cada prueba."""
    inbound_service._memory_registry.clear()
    inbound_service.event_queue.clear()
    conn = inbound_service.get_db_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM inbound_emails WHERE message_id LIKE '%TEST%' OR message_id = 'MSG-12345' OR message_id = '18ac2fe34a012345';")
                cur.execute("DELETE FROM justifications WHERE message_id LIKE '%TEST%' OR message_id = 'MSG-12345' OR message_id = '18ac2fe34a012345';")
            conn.commit()
        except Exception:
            conn.rollback()
        finally:
            conn.close()
    yield
    inbound_service._memory_registry.clear()
    inbound_service.event_queue.clear()
    conn = inbound_service.get_db_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM inbound_emails WHERE message_id LIKE '%TEST%' OR message_id = 'MSG-12345' OR message_id = '18ac2fe34a012345';")
                cur.execute("DELETE FROM justifications WHERE message_id LIKE '%TEST%' OR message_id = 'MSG-12345' OR message_id = '18ac2fe34a012345';")
            conn.commit()
        except Exception:
            conn.rollback()
        finally:
            conn.close()


@pytest.fixture
def client():
    """Cliente HTTP de prueba para FastAPI."""
    return TestClient(server.app)


def test_scenario_1_successful_outlook_email_reception(client):
    """
    Criterio de Aceptación 1 (Gherkin):
    Escenario: Recepción exitosa de correo desde adaptador de Outlook
      Dado que el servicio de ingesta está en ejecución en /api/v1/inbound-email
      Cuando el conector de Outlook envía un payload válido con remitente, asunto, cuerpo y adjuntos en Base64
      Entonces el servicio responde HTTP 202 Accepted
      Y el evento es encolado para identificación y validación
      Y se almacena un registro transaccional con estado PENDING_IDENTIFICATION
    """
    # 1. Preparar archivo de prueba en Base64
    sample_pdf_bytes = b"%PDF-1.4 Mock Certificado Medico EPS Sanitas - Dr. Sebastian Ropain"
    sample_pdf_b64 = base64.b64encode(sample_pdf_bytes).decode("ascii")
    expected_hash = hashlib.sha256(sample_pdf_bytes).hexdigest()

    outlook_payload = {
        "source_provider": "OUTLOOK",
        "message_id": "AAMkAGI2_TEST_OUTLOOK_001",
        "conversation_id": "AAQkAGI_THREAD_001",
        "sender_email": "laura.gomez@riwi.io",
        "sender_name": "Laura Gómez",
        "email_subject": "Justificación inasistencia 29 Septiembre",
        "email_body": "Buenos días equipo HSE, adjunto comprobante médico de mi cita de hoy...",
        "received_at": "2026-09-29T14:10:00Z",
        "attachments": [
            {
                "filename": "incapacidad_sanitas.pdf",
                "mime_type": "application/pdf",
                "data_base64": sample_pdf_b64
            }
        ]
    }

    # 2. Enviar petición al endpoint
    response = client.post("/api/v1/inbound-email", json=outlook_payload)

    # 3. Validar HTTP 202 Accepted
    assert response.status_code == 202, f"Esperado HTTP 202, obtenido: {response.status_code}"
    data = response.json()

    assert data["status"] == "ACCEPTED"
    assert data["message"] == "Event queued for identification and validation"
    assert data["message_id"] == "AAMkAGI2_TEST_OUTLOOK_001"
    assert data["conversation_id"] == "AAQkAGI_THREAD_001"
    assert data["state"] == "PENDING_IDENTIFICATION"
    assert data["attachments_count"] == 1
    assert data["transaction_id"] is not None

    # 4. Validar que el registro transaccional fue almacenado con estado PENDING_IDENTIFICATION
    record = inbound_service._memory_registry.get("AAMkAGI2_TEST_OUTLOOK_001")
    assert record is not None, "El registro transaccional debe persistir en el repositorio"
    assert record["status"] == "PENDING_IDENTIFICATION"
    assert record["sender_email"] == "laura.gomez@riwi.io"
    assert record["sender_name"] == "Laura Gómez"
    assert len(record["attachments"]) == 1

    # 5. Validar almacenamiento seguro del adjunto en disco y cálculo SHA-256
    saved_att = record["attachments"][0]
    assert saved_att["filename"] == "incapacidad_sanitas.pdf"
    assert saved_att["sha256_hash"] == expected_hash
    assert saved_att["temp_path"] is not None
    assert os.path.exists(saved_att["temp_path"]), f"El archivo debe existir en disco: {saved_att['temp_path']}"

    with open(saved_att["temp_path"], "rb") as f:
        written_bytes = f.read()
    assert written_bytes == sample_pdf_bytes, "El contenido guardado en disco debe coincidir con el Base64 recibido"

    # 6. Validar que el evento fue encolado para identificación y validación
    assert len(inbound_service.event_queue) == 1
    queued_event = inbound_service.event_queue[0]
    assert queued_event["message_id"] == "AAMkAGI2_TEST_OUTLOOK_001"
    assert queued_event["status"] == "QUEUED"


def test_scenario_2_idempotency_duplicate_detection(client):
    """
    Criterio de Aceptación 2 (Gherkin):
    Escenario: Detección y rechazo de payload duplicado (Idempotencia)
      Dado que ya existe un correo registrado con message_id "MSG-12345"
      Cuando ingresa una nueva solicitud con el mismo message_id
      Entonces el sistema responde HTTP 200 OK con mensaje "Event already processed"
      Y no se duplica ningún registro en la base de datos
    """
    payload = {
        "source_provider": "OUTLOOK",
        "message_id": "MSG-12345",
        "conversation_id": "CONV-12345",
        "sender_email": "esteban.coder@riwi.io",
        "sender_name": "Esteban Developer",
        "email_subject": "Cita médica odontológica",
        "email_body": "Adjunto soporte de mi cita de odontología.",
        "attachments": []
    }

    # 1. Primera petición: debe ser aceptada (HTTP 202)
    res_first = client.post("/api/v1/inbound-email", json=payload)
    assert res_first.status_code == 202
    assert res_first.json()["status"] == "ACCEPTED"
    assert res_first.json()["state"] == "PENDING_IDENTIFICATION"

    initial_registry_count = len(inbound_service._memory_registry)
    initial_queue_count = len(inbound_service.event_queue)
    assert initial_registry_count == 1
    assert initial_queue_count == 1

    # 2. Segunda petición con el MISMO message_id "MSG-12345"
    res_duplicate = client.post("/api/v1/inbound-email", json=payload)

    # 3. Validaciones de Idempotencia
    assert res_duplicate.status_code == 200, f"Esperado HTTP 200, obtenido: {res_duplicate.status_code}"
    dup_data = res_duplicate.json()
    assert dup_data["status"] == "OK"
    assert dup_data["message"] == "Event already processed"
    assert dup_data["message_id"] == "MSG-12345"

    # 4. Validar que NO se duplicó ningún registro en la base de datos/repositorio
    assert len(inbound_service._memory_registry) == initial_registry_count
    # Tampoco se debe encolar un segundo evento
    assert len(inbound_service.event_queue) == initial_queue_count


def test_gmail_adapter_payload_compatibility(client):
    """Verifica compatibilidad con conectores de Gmail (CONN-03 / Google PubSub)."""
    raw_evidence = b"Mock Evidencia EPS Sura Imagen JPEG"
    b64_evidence = base64.b64encode(raw_evidence).decode("ascii")

    gmail_payload = {
        "source_provider": "GMAIL",
        "message_id": "18ac2fe34a012345",
        "conversation_id": "thread_gmail_999",
        "sender_email": "mariana.ospina@riwi.io",
        "sender_name": "Mariana Ospina",
        "email_subject": "Justificación Médica - Mariana Ospina",
        "email_body": "Buenas tardes equipo HSE, adjunto soporte médico de EPS Sura.",
        "attachments": [
            {
                "filename": "incapacidad_sura.jpg",
                "mime_type": "image/jpeg",
                "data_base64": b64_evidence
            }
        ]
    }

    res = client.post("/api/v1/inbound-email", json=gmail_payload)
    assert res.status_code == 202
    data = res.json()
    assert data["message_id"] == "18ac2fe34a012345"
    assert data["state"] == "PENDING_IDENTIFICATION"
    assert data["attachments_count"] == 1


def test_auto_generate_identifiers_when_missing(client):
    """Verifica que el servicio genere message_id y conversation_id únicos cuando no se proporcionan."""
    payload_no_ids = {
        "sender_email": "coder.sin.id@riwi.io",
        "email_subject": "Ausencia justificada",
        "email_body": "No podré asistir por asuntos personales de fuerza mayor."
    }

    res = client.post("/api/v1/inbound-email", json=payload_no_ids)
    assert res.status_code == 202
    data = res.json()
    assert data["message_id"].startswith("msg_")
    assert data["conversation_id"].startswith("conv_")
    assert data["state"] == "PENDING_IDENTIFICATION"


def test_validation_error_on_invalid_payload(client):
    """Verifica que payloads inválidos sean rechazados con HTTP 422 Unprocessable Entity."""
    # Correo inválido y sin asunto ni cuerpo
    bad_payload = {
        "sender_email": "correo-no-valido-sin-arroba",
    }

    res = client.post("/api/v1/inbound-email", json=bad_payload)
    assert res.status_code == 422
    assert "detail" in res.json()


def test_path_traversal_prevention_on_attachments(client):
    """Verifica que nombres de archivo maliciosos sean sanitizados sin escapar del directorio seguro."""
    malicious_payload = {
        "sender_email": "hacker@riwi.io",
        "email_subject": "Intento de path traversal",
        "email_body": "Prueba de seguridad",
        "attachments": [
            {
                "filename": "../../../../../etc/passwd",
                "mime_type": "text/plain",
                "data_base64": base64.b64encode(b"root:x:0:0:root").decode("ascii")
            }
        ]
    }

    res = client.post("/api/v1/inbound-email", json=malicious_payload)
    assert res.status_code == 202
    record = list(inbound_service._memory_registry.values())[0]
    saved_path = record["attachments"][0]["temp_path"]

    # Debe residir estrictamente dentro de DEFAULT_ATTACHMENTS_DIR
    assert os.path.exists(saved_path)
    assert str(inbound_service.attachments_dir) in saved_path
    assert "etc/passwd" not in saved_path
