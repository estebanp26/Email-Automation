import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.notification import notification_service
from backend.app.schemas.notification import (
    NotificationDispatchInput,
    NotificationPreviewRequest,
)

client = TestClient(app)


def test_render_approved_template():
    sub, html_content = notification_service._generate_html_template(
        template_type="APPROVED",
        name="Jose Acevedo",
        dates="2026-09-28 al 2026-09-29",
        excuse_type="incapacidad_medica",
        notes="Soporte EPS convalidado."
    )
    assert "Aprobada" in sub
    assert "ESTADO: JUSTIFICADA" in html_content
    assert "no suma" in html_content.lower()
    assert "Jose Acevedo" in html_content


def test_render_disapproved_template():
    sub, html_content = notification_service._generate_html_template(
        template_type="DISAPPROVED",
        name="Carlos Perez",
        dates="2026-09-25",
        excuse_type="falta_injustificada",
        notes="Falta de soporte oficial verificable."
    )
    assert "No Justificada" in sub
    assert "INASISTENCIA INJUSTIFICADA" in html_content
    assert "moodle" in html_content.lower()


def test_render_request_more_info_template():
    sub, html_content = notification_service._generate_html_template(
        template_type="REQUEST_MORE_INFO",
        name="Laura Gomez",
        dates="2026-09-28",
        excuse_type="cita_medica"
    )
    assert "Requerimiento de Soporte" in sub
    assert "tres (3) días hábiles" in html_content


def test_render_coder_not_found_template():
    sub, html_content = notification_service._generate_html_template(
        template_type="CODER_NOT_FOUND",
        name="Remitente Desconocido",
        dates="2026-09-28",
        excuse_type="desconocido"
    )
    assert "Información de Matrícula" in sub
    assert "CODER NO IDENTIFICADO" in html_content
    assert "número de cédula" in html_content.lower()


def test_render_hse_alert_template():
    sub, html_content = notification_service._generate_html_template(
        template_type="HSE_ALERT",
        name="Andrea Ahumada",
        dates="2026-09-29",
        excuse_type="situacion_emocional_critica",
        threshold_level=3
    )
    assert "Alerta de Permanencia HSE" in sub
    assert "Umbral 3" in sub
    assert "Acompañamiento Psicosocial" in html_content


def test_thread_aware_reply_subject():
    inp = NotificationDispatchInput(
        recipient_email="coder@riwi.io",
        recipient_name="Coder",
        template_type="APPROVED",
        original_subject="Justificación de inasistencia 28 Sept",
        in_reply_to_message_id="msg-12345"
    )
    res = notification_service.dispatch(inp)
    assert res.subject.startswith("Re: ")
    assert res.in_reply_to == "msg-12345"


def test_dispatch_stores_in_outbox():
    initial_count = len(notification_service.list_outbox())
    inp = NotificationDispatchInput(
        recipient_email="test.coder@riwi.io",
        recipient_name="Test Coder",
        template_type="APPROVED",
        excuse_type="incapacidad_medica"
    )
    res = notification_service.dispatch(inp)
    assert res.status == "SENT"
    assert len(notification_service.list_outbox()) == initial_count + 1


def test_api_dispatch_endpoint():
    payload = {
        "recipient_email": "jose.acevedo@riwi.io",
        "recipient_name": "Jose Acevedo",
        "template_type": "APPROVED",
        "start_date": "2026-09-28",
        "end_date": "2026-09-29",
        "excuse_type": "incapacidad_medica",
        "notes": "Convalidado por Team Leader"
    }
    response = client.post("/api/v1/notifications/dispatch", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SENT"
    assert data["recipient"] == "jose.acevedo@riwi.io"
    assert "Aprobada" in data["subject"]


def test_api_preview_endpoint():
    payload = {
        "template_type": "DISAPPROVED",
        "recipient_name": "Coder Prueba",
        "excuse_type": "falta_injustificada",
        "start_date": "2026-09-28",
        "end_date": "2026-09-28",
        "notes": "No presentó soporte formal"
    }
    response = client.post("/api/v1/notifications/preview", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "No Justificada" in data["subject"]
    assert "Coder Prueba" in data["html_body"]


def test_api_outbox_endpoint():
    response = client.get("/api/v1/notifications/outbox?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
