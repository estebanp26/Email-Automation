import pytest
import base64
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.orchestrator import orchestrator
from backend.app.schemas.email import RawEmailInput, RawAttachmentInput
from backend.app.schemas.justification import PipelineProcessRequest

client = TestClient(app)


def test_process_pipeline_valid_medical_excuse():
    raw_email = RawEmailInput(
        source_provider="OUTLOOK",
        sender_email="jose.acevedo@riwi.io",
        sender_name="Jose Luis Acevedo",
        recipient_email="tl@riwi.io",
        cc_emails=["formacion.barranquilla@riwi.io"],
        subject="Incapacidad médica 28 y 29 de septiembre",
        body="Buenas tardes, adjunto incapacidad emitida por Sura para los días 2026-09-28 y 2026-09-29. CC 1000000001.",
        attachments=[
            RawAttachmentInput(
                filename="incapacidad_eps_sura.pdf",
                mime_type="application/pdf",
                data_base64=base64.b64encode(b"%PDF-1.4 Dummy PDF Sura").decode("utf-8")
            )
        ]
    )

    result = orchestrator.process_pipeline(raw_email)
    assert result.execution_status == "COMPLETED"
    assert result.justification is not None
    assert result.justification.coder_cedula == "1000000001"
    assert result.justification.status == "APPROVED"
    assert result.justification.excuse_type == "incapacidad_medica"
    assert result.justification.days_count == 2
    assert result.justification.has_formacion_cc is True


def test_process_pipeline_coder_not_found():
    raw_email = RawEmailInput(
        source_provider="GMAIL",
        sender_email="externo.desconocido@yahoo.com",
        sender_name="Persona No Registrada",
        subject="Aviso de ausencia",
        body="No pude asistir el día de hoy por asuntos personales."
    )

    result = orchestrator.process_pipeline(raw_email)
    assert result.execution_status == "COMPLETED"
    assert result.justification is not None
    assert result.justification.status == "CODER_NOT_FOUND"
    assert result.justification.coder_id is None
    assert result.justification.escalate_to_hse is True


def test_process_pipeline_sensitive_case():
    raw_email = RawEmailInput(
        source_provider="OUTLOOK",
        sender_email="andrea.ahumada@riwi.io",
        sender_name="Andrea Ahumada",
        subject="Situación urgente de salud mental",
        body="Estimado TL, estoy atravesando una crisis de pánico severa y depresión. Cédula 1000000002."
    )

    result = orchestrator.process_pipeline(raw_email)
    assert result.execution_status == "COMPLETED"
    assert result.justification is not None
    assert result.justification.status == "REVISION_MANUAL"
    assert result.justification.is_sensitive is True
    assert result.justification.escalate_to_hse is True


def test_list_records_and_filters():
    records = orchestrator.list_records(status="APPROVED")
    assert len(records) > 0
    assert all(r.status == "APPROVED" for r in records)


def test_get_record_by_id():
    rec = orchestrator.get_record_by_id("just-c6357532-2555-4a40-a4ff-bd148a8036b2")
    assert rec is not None
    assert rec.coder_full_name == "Jose Luis Acevedo Vargas"


def test_api_process_endpoint():
    payload = {
        "raw_email": {
            "source_provider": "OUTLOOK",
            "sender_email": "cristian.albor@riwi.io",
            "sender_name": "Cristian Albor",
            "subject": "Cita médica programada",
            "body": "Buenas tardes, informo cita médica para el 2026-09-30. Adjunto cita. CC 1000000004.",
            "attachments": [
                {
                    "filename": "comprobante_cita.pdf",
                    "data_base64": base64.b64encode(b"%PDF-1.4 Dummy PDF").decode("utf-8")
                }
            ]
        }
    }
    response = client.post("/api/v1/pipeline/process", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["execution_status"] == "COMPLETED"
    assert data["justification"]["coder_cedula"] == "1000000004"


def test_api_queue_endpoint():
    payload = {
        "source_provider": "GMAIL",
        "sender_email": "jose.acevedo@riwi.io",
        "subject": "Aviso rápido",
        "body": "Hola TL, aviso que llegaré unos minutos tarde por tráfico."
    }
    response = client.post("/api/v1/pipeline/queue", json=payload)
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "QUEUED"


def test_api_records_endpoint():
    response = client.get("/api/v1/pipeline/records")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
