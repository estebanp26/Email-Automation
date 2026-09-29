import pytest
import base64
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.portal_service import portal_service
from backend.app.schemas.coder_portal import CoderExcuseSubmission

client = TestClient(app)


def test_submit_coder_excuse():
    sub = CoderExcuseSubmission(
        coder_name="Jose Luis Acevedo Vargas",
        coder_email="jose.acevedo@riwi.io",
        document_id="1000000001",
        clan="Node.js Backend",
        shift="Mañana",
        category="cita_medica",
        start_date="2026-09-30",
        end_date="2026-09-30",
        reason="Cita odontológica prioritaria programada.",
        attachment_filename="cita_odontologia.pdf",
        attachment_data_base64=base64.b64encode(b"Dummy PDF Cita").decode("utf-8")
    )
    result = portal_service.submit_excuse(sub)
    assert result.execution_status == "COMPLETED"
    assert result.justification is not None
    assert result.justification.coder_cedula == "1000000001"
    assert result.justification.excuse_type == "cita_medica"


def test_get_coder_excuses_filtered():
    excuses = portal_service.get_coder_excuses(coder_email="jose.acevedo@riwi.io")
    assert isinstance(excuses, list)
    assert len(excuses) >= 1
    assert excuses[0].coder_cedula == "1000000001"


def test_get_coder_attendance_summary():
    summary = portal_service.get_attendance_summary("1000000001")
    assert summary.coder_cedula == "1000000001"
    assert summary.coder_name == "Jose Luis Acevedo Vargas"
    assert summary.total_requests >= 1
    assert summary.current_threshold in ["NINGUNO", "UMBRAL_1", "UMBRAL_2", "UMBRAL_3", "UMBRAL_4"]


def test_get_dashboard_global_stats():
    stats = portal_service.get_dashboard_global_stats()
    assert stats.total_requests >= 1
    assert stats.approved_count >= 1


def test_api_submit_coder_excuse_endpoint():
    payload = {
        "coder_name": "Andrea Ahumada",
        "coder_email": "andrea.ahumada@riwi.io",
        "document_id": "1000000002",
        "clan": "Java Spring Boot",
        "shift": "Mañana",
        "category": "incapacidad_medica",
        "start_date": "2026-09-28",
        "end_date": "2026-09-29",
        "reason": "Incapacidad médica por amigdalitis bacteriana emitida por EPS.",
        "attachment_filename": "incapacidad_sura.pdf",
        "attachment_data_base64": base64.b64encode(b"Dummy PDF").decode("utf-8")
    }
    response = client.post("/api/v1/coders/excuses", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["execution_status"] == "COMPLETED"
    assert data["justification"]["coder_cedula"] == "1000000002"


def test_api_list_coder_excuses_endpoint():
    response = client.get("/api/v1/coders/excuses?coder_cedula=1000000001")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_api_attendance_summary_endpoint():
    response = client.get("/api/v1/coders/1000000001/attendance-summary")
    assert response.status_code == 200
    data = response.json()
    assert data["coder_cedula"] == "1000000001"
    assert "current_threshold" in data


def test_api_dashboard_stats_endpoint():
    response = client.get("/api/v1/stats/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert data["total_requests"] >= 1
