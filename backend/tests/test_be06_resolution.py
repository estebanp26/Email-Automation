import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.orchestrator import orchestrator
from backend.app.services.resolution_service import resolution_service
from backend.app.schemas.resolution import ManualResolutionInput, ReconsiderationInput

client = TestClient(app)
SAMPLE_JUST_ID = "just-c6357532-2555-4a40-a4ff-bd148a8036b2"


def test_manual_approve_justification():
    inp = ManualResolutionInput(
        action="APPROVE",
        reviewer_name="Paola Team Leader",
        reviewer_role="TEAM_LEADER",
        notes="Soporte médico verificado y validado con EPS Sura.",
        dispatch_notification=True
    )
    res = resolution_service.resolve_justification(SAMPLE_JUST_ID, inp)
    assert res.status == "APPROVED"
    assert res.resolution_mode == "MANUAL_HSE"
    assert res.has_human_intervention is True
    assert res.hse_reviewer_name == "Paola Team Leader"
    assert res.notification_dispatched is True
    assert res.notification_details["template"] == "APPROVED"


def test_manual_disapprove_justification():
    inp = ManualResolutionInput(
        action="DISAPPROVE",
        reviewer_name="Carlos TL Desarrollo",
        reviewer_role="TEAM_LEADER",
        notes="Incapacidad no oficial de EPS. Malestar supera 2 días reglamentarios.",
        dispatch_notification=True
    )
    res = resolution_service.resolve_justification(SAMPLE_JUST_ID, inp)
    assert res.status == "DISAPPROVED"
    assert res.notification_details["template"] == "DISAPPROVED"


def test_manual_request_more_info():
    inp = ManualResolutionInput(
        action="REQUEST_MORE_INFO",
        reviewer_name="Andres HSE",
        reviewer_role="HSE",
        notes="Por favor adjuntar certificado con sello y firma de la EPS.",
        dispatch_notification=True
    )
    res = resolution_service.resolve_justification(SAMPLE_JUST_ID, inp)
    assert res.status == "REVISION_MANUAL"
    assert res.notification_details["template"] == "REQUEST_MORE_INFO"


def test_reconsideration_flow():
    rec_inp = ReconsiderationInput(
        new_action="APPROVE",
        reviewer_name="Coordinación HSE",
        reconsideration_reason="El estudiante aportó la transcripción oficial de la EPS dentro de los 3 días hábiles.",
        new_attachment_name="transcripcion_eps_oficial.pdf"
    )
    res = resolution_service.reconsider_justification(SAMPLE_JUST_ID, rec_inp)
    assert res.status == "APPROVED"
    assert len(res.audit_trail) >= 2
    assert "RECONSIDERATION_APPROVE" in res.audit_trail[-1].action


def test_api_resolve_endpoint():
    payload = {
        "action": "APPROVE",
        "reviewer_name": "Paola Team Leader",
        "notes": "Validado en comité de asistencia",
        "dispatch_notification": True
    }
    response = client.post(f"/api/v1/justifications/{SAMPLE_JUST_ID}/resolve", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "APPROVED"
    assert data["has_human_intervention"] is True


def test_api_reconsider_endpoint():
    payload = {
        "new_action": "APPROVE",
        "reviewer_name": "Coordinador Académico",
        "reconsideration_reason": "Presentó descargos válidos y soporte médico legal",
        "new_attachment_name": "soporte_reconsiderado.pdf"
    }
    response = client.post(f"/api/v1/justifications/{SAMPLE_JUST_ID}/reconsider", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "APPROVED"


def test_api_audit_trail_endpoint():
    response = client.get(f"/api/v1/justifications/{SAMPLE_JUST_ID}/audit-trail")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
