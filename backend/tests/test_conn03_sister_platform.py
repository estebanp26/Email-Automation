from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.config import settings
from backend.app.ports.sister_platform import (
    SisterPlatformAttendancePort,
    ExternalAttendanceRecord,
    AbsenceVerificationResult,
    AttendanceStatus,
)
from backend.app.adapters.sister_platform.mock_service import MockSisterPlatformAttendanceService
from backend.app.adapters.sister_platform.http_adapter import HttpSisterPlatformAttendanceAdapter
from backend.app.adapters.sister_platform.factory import (
    get_sister_platform_attendance_service,
    reset_mock_instance,
)
from backend.app.services.hse_engine import HSEPolicyEngine, hse_engine
from backend.app.schemas.policy import PolicyEvaluationInput

client = TestClient(app)


# =============================================================================
# 1. PRUEBAS DEL MOCK SERVICE Y ARQUITECTURA HEXAGONAL (CRITERIO 1)
# =============================================================================

def test_mock_service_implements_port():
    """Verifica que MockSisterPlatformAttendanceService implemente fielmente el puerto abstracto."""
    mock = MockSisterPlatformAttendanceService()
    assert isinstance(mock, SisterPlatformAttendancePort)


def test_mock_service_generates_absences_for_any_coder():
    """Criterio 1: Capaz de generar inasistencias de prueba para cualquier coder."""
    mock = MockSisterPlatformAttendanceService(auto_generate=False)
    custom_coder = "coder-arbitrario-999"

    dates = [
        date(2026, 10, 1),
        date(2026, 10, 2),
        date(2026, 10, 3)
    ]

    # Antes de generar: no debe tener registros
    records_before = mock.get_attendance_records(custom_coder, date(2026, 10, 1), date(2026, 10, 3))
    assert len(records_before) == 0

    # Generar inasistencias de prueba
    created = mock.generate_mock_absences(custom_coder, dates)
    assert len(created) == 3
    for rec in created:
        assert rec.coder_id == custom_coder
        assert rec.status == AttendanceStatus.ABSENT
        assert rec.source_platform == "SISTER_PLATFORM_MOCK"

    # Verificar que ahora consten en el historial
    records_after = mock.get_attendance_records(custom_coder, date(2026, 10, 1), date(2026, 10, 3))
    assert len(records_after) == 3


def test_mock_service_verify_absence_confirmed():
    """Verifica que verify_absence retorne is_absent_recorded=True cuando hay faltas ABSENT."""
    mock = MockSisterPlatformAttendanceService(auto_generate=False)
    coder_id = "coder-test-verify"
    d1 = date(2026, 10, 5)

    mock.set_coder_attendance(coder_id, d1, AttendanceStatus.ABSENT)
    res = mock.verify_absence(coder_id, d1, d1)

    assert res.is_absent_recorded is True
    assert res.has_records is True
    assert "2026-10-05" in res.absent_days
    assert "Inasistencia confirmada" in res.details


def test_mock_service_verify_absence_present_contradiction():
    """Verifica el caso donde el coder estuvo PRESENTE en las fechas indicadas."""
    mock = MockSisterPlatformAttendanceService(auto_generate=False)
    coder_id = "coder-presente-test"
    d1 = date(2026, 10, 6)

    mock.set_coder_attendance(coder_id, d1, AttendanceStatus.PRESENT)
    res = mock.verify_absence(coder_id, d1, d1)

    assert res.is_absent_recorded is False
    assert res.has_records is True
    assert len(res.absent_days) == 0
    assert "2026-10-06" in res.present_days
    assert "Sin inasistencia registrada" in res.details


def test_mock_service_auto_generate_on_query():
    """Verifica que con auto_generate=True sintetice inasistencias automáticamente para cualquier coder nuevo."""
    mock = MockSisterPlatformAttendanceService(auto_generate=True)
    new_coder = "coder-totalmente-nuevo"
    d1 = date(2026, 10, 10)
    d2 = date(2026, 10, 12)

    res = mock.verify_absence(new_coder, d1, d2)
    assert res.is_absent_recorded is True
    assert res.has_records is True
    assert len(res.absent_days) == 3


# =============================================================================
# 2. INTEGRACIÓN EN HSE POLICY ENGINE (CRITERIO 2)
# =============================================================================

def test_hse_engine_consults_sister_platform_absence_confirmed():
    """
    Criterio 2: Cuando se evalúa una justificación, el motor consulta el adaptador
    para verificar si en las fechas indicadas realmente consta una inasistencia (ABSENT).
    """
    mock_adapter = MockSisterPlatformAttendanceService(auto_generate=False)
    coder_id = "coder-policy-confirmed"
    start_d = "2026-10-15"
    end_d = "2026-10-16"

    # Registrar inasistencias en el mock adapter
    mock_adapter.set_coder_attendance(coder_id, date(2026, 10, 15), AttendanceStatus.ABSENT)
    mock_adapter.set_coder_attendance(coder_id, date(2026, 10, 16), AttendanceStatus.ABSENT)

    # Inyectar adaptador desacoplado en el motor
    engine = HSEPolicyEngine(attendance_adapter=mock_adapter)

    payload = PolicyEvaluationInput(
        coder_id=coder_id,
        excuse_type="incapacidad_medica",
        start_date=start_d,
        end_date=end_d,
        report_date=start_d,
        has_attachment=True,
        attachment_is_eps_official=True
    )

    res = engine.evaluate_excuse(payload)

    assert res.absence_verified is True
    assert res.external_absence_status == "ABSENT"
    assert "Inasistencia (ABSENT) verificada exitosamente" in res.sister_platform_notes
    assert res.decision == "POSIBLEMENTE_VALIDO"


def test_hse_engine_detects_contradictory_presence():
    """
    El motor detecta inconsistencia si la plataforma hermana reporta que el coder
    estuvo PRESENTE en las fechas de la justificación.
    """
    mock_adapter = MockSisterPlatformAttendanceService(auto_generate=False)
    coder_id = "coder-policy-contradiction"
    start_d = "2026-10-20"
    end_d = "2026-10-20"

    # Simular que el coder estuvo presente
    mock_adapter.set_coder_attendance(coder_id, date(2026, 10, 20), AttendanceStatus.PRESENT)

    engine = HSEPolicyEngine(attendance_adapter=mock_adapter)

    payload = PolicyEvaluationInput(
        coder_id=coder_id,
        excuse_type="incapacidad_medica",
        start_date=start_d,
        end_date=end_d,
        report_date=start_d,
        has_attachment=True,
        attachment_is_eps_official=True
    )

    res = engine.evaluate_excuse(payload)

    assert res.absence_verified is False
    assert res.external_absence_status == "PRESENT"
    assert res.policy_rule_triggered == "REGISTRO_PRESENTE_CONTRADICTORIO"
    assert res.decision == "POSIBLEMENTE_INVALIDO"
    assert res.escalate_to_hse is True


def test_hse_engine_handles_no_remote_records():
    """
    El motor documenta correctamente cuando la plataforma hermana no tiene registros aún.
    """
    mock_adapter = MockSisterPlatformAttendanceService(auto_generate=False)
    coder_id = "coder-sin-registros"

    engine = HSEPolicyEngine(attendance_adapter=mock_adapter)

    payload = PolicyEvaluationInput(
        coder_id=coder_id,
        excuse_type="cita_medica",
        start_date="2026-10-25",
        end_date="2026-10-25",
        report_date="2026-10-24",  # Oportuno
        has_attachment=True
    )

    res = engine.evaluate_excuse(payload)

    assert res.absence_verified is False
    assert res.external_absence_status == "NO_RECORDS"
    assert "Sin registros remotos" in res.sister_platform_notes


# =============================================================================
# 3. VARIABLES DE ENTORNO Y FACTORY (CRITERIO 3)
# =============================================================================

def test_environment_variables_configured():
    """Criterio 3: Inclusión de variables de entorno preparadas."""
    assert hasattr(settings, "SISTER_PLATFORM_API_URL")
    assert hasattr(settings, "SISTER_PLATFORM_API_KEY")
    assert hasattr(settings, "SISTER_PLATFORM_USE_MOCK")
    assert settings.SISTER_PLATFORM_USE_MOCK is True
    assert "plataforma-hermana" in settings.SISTER_PLATFORM_API_URL.lower()


def test_factory_returns_mock_service_by_default(monkeypatch):
    """Verifica que el Factory retorne MockService cuando USE_MOCK es True."""
    monkeypatch.setattr(settings, "SISTER_PLATFORM_USE_MOCK", True)
    reset_mock_instance()

    service = get_sister_platform_attendance_service()
    assert isinstance(service, MockSisterPlatformAttendanceService)


def test_factory_returns_http_adapter_when_mock_disabled(monkeypatch):
    """Verifica que el Factory retorne HttpSisterPlatformAttendanceAdapter cuando USE_MOCK es False."""
    monkeypatch.setattr(settings, "SISTER_PLATFORM_USE_MOCK", False)
    monkeypatch.setattr(settings, "SISTER_PLATFORM_API_URL", "https://api.sister.test")
    monkeypatch.setattr(settings, "SISTER_PLATFORM_API_KEY", "secret-token")

    service = get_sister_platform_attendance_service()
    assert isinstance(service, HttpSisterPlatformAttendanceAdapter)
    assert service.api_url == "https://api.sister.test"
    assert service.api_key == "secret-token"

    # Restaurar para siguientes pruebas
    monkeypatch.setattr(settings, "SISTER_PLATFORM_USE_MOCK", True)
    reset_mock_instance()


# =============================================================================
# 4. PRUEBAS DE ENDPOINTS REST API
# =============================================================================

def test_api_attendance_verify_endpoint():
    """Valida el endpoint GET /api/v1/attendance/verify."""
    response = client.get(
        "/api/v1/attendance/verify",
        params={
            "coder_id": "1000000001",
            "start_date": "2026-09-28",
            "end_date": "2026-09-29"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "is_absent_recorded" in data
    assert "has_records" in data
    assert "absent_days" in data
    assert data["is_absent_recorded"] is True


def test_api_attendance_mock_absences_endpoint():
    """Valida el endpoint POST /api/v1/attendance/mock/absences."""
    payload = {
        "coder_id": "coder-api-test",
        "dates": ["2026-11-01", "2026-11-02"],
        "session_type": "CLASE"
    }
    response = client.post("/api/v1/attendance/mock/absences", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert len(data) == 2
    assert data[0]["coder_id"] == "coder-api-test"
    assert data[0]["status"] == "ABSENT"


def test_api_attendance_mock_status_endpoint():
    """Valida el endpoint POST /api/v1/attendance/mock/status."""
    payload = {
        "coder_id": "coder-api-test",
        "attendance_date": "2026-11-03",
        "status": "PRESENT",
        "session_type": "TALLER",
        "notes": "Asistencia fijada manualmente para prueba"
    }
    response = client.post("/api/v1/attendance/mock/status", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["coder_id"] == "coder-api-test"
    assert data["status"] == "PRESENT"
    assert data["session_type"] == "TALLER"
