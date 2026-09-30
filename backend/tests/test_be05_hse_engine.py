import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.hse_engine import hse_engine
from backend.app.schemas.policy import PolicyEvaluationInput

client = TestClient(app)


def test_incapacidad_medica_valida():
    payload = PolicyEvaluationInput(
        coder_id="coder-1000000001",
        excuse_type="incapacidad_medica",
        start_date="2026-09-27",
        end_date="2026-09-28",
        report_date="2026-09-28",
        has_attachment=True,
        attachment_is_eps_official=True
    )
    res = hse_engine.evaluate_excuse(payload)
    assert res.decision == "POSIBLEMENTE_VALIDO"
    assert res.is_timely is True
    assert res.support_valid is True
    assert res.days_calculated == 2


def test_incapacidad_extemporanea_mas_de_3_dias():
    # Reporte 5 días después (plazo máximo en Slide 3 PPTX es 3 días)
    payload = PolicyEvaluationInput(
        coder_id="coder-1000000001",
        excuse_type="incapacidad_medica",
        start_date="2026-09-20",
        end_date="2026-09-21",
        report_date="2026-09-26",
        has_attachment=True,
        attachment_is_eps_official=True
    )
    res = hse_engine.evaluate_excuse(payload)
    assert res.is_timely is False
    assert res.decision == "POSIBLEMENTE_INVALIDO"
    assert res.policy_rule_triggered == "FUERZA_MAYOR_VENCIDA"


def test_incapacidad_sin_soporte_eps_oficial():
    # Tiene adjunto pero no es EPS oficial (ej. fórmula o recibo)
    payload = PolicyEvaluationInput(
        coder_id="coder-1000000001",
        excuse_type="incapacidad_medica",
        start_date="2026-09-28",
        end_date="2026-09-29",
        report_date="2026-09-28",
        has_attachment=True,
        attachment_is_eps_official=False
    )
    res = hse_engine.evaluate_excuse(payload)
    assert res.decision == "REVISION_MANUAL"
    assert res.escalate_to_hse is True
    assert res.policy_rule_triggered == "INCAPACIDAD_NO_EPS_OFICIAL"


def test_malestar_2_dias_vs_3_dias():
    # 2 días de malestar: Válido sin incapacidad
    p2 = PolicyEvaluationInput(
        excuse_type="enfermo_sin_incapacidad",
        start_date="2026-09-28",
        end_date="2026-09-29",
        report_date="2026-09-28"
    )
    r2 = hse_engine.evaluate_excuse(p2)
    assert r2.days_calculated == 2
    assert r2.decision == "POSIBLEMENTE_VALIDO"
    assert r2.support_valid is True

    # 3 días de malestar: Inválido sin soporte de EPS oficial (Slide 3 PPTX)
    p3 = PolicyEvaluationInput(
        excuse_type="enfermo_sin_incapacidad",
        start_date="2026-09-26",
        end_date="2026-09-28",
        report_date="2026-09-26"
    )
    r3 = hse_engine.evaluate_excuse(p3)
    assert r3.days_calculated == 3
    assert r3.decision == "POSIBLEMENTE_INVALIDO"
    assert r3.escalate_to_hse is True
    assert r3.policy_rule_triggered == "MALESTAR_SUPERA_2_DIAS"


def test_cita_medica_previsible_extemporanea():
    # Cita médica reportada DESPUÉS de que ocurrió (Slide 3 PPTX)
    payload = PolicyEvaluationInput(
        excuse_type="cita_medica",
        start_date="2026-09-27",
        end_date="2026-09-27",
        report_date="2026-09-28",
        has_attachment=True
    )
    res = hse_engine.evaluate_excuse(payload)
    assert res.is_timely is False
    assert res.decision == "POSIBLEMENTE_INVALIDO"
    assert res.policy_rule_triggered == "PREVISIBLE_EXTEMPORANEO"


def test_situacion_emocional_sensible():
    # Slide 5 y 8: Salud mental / situación emocional crítica -> derivar a HSE
    payload = PolicyEvaluationInput(
        excuse_type="situacion_emocional_critica",
        start_date="2026-09-29",
        end_date="2026-09-29",
        report_date="2026-09-29"
    )
    res = hse_engine.evaluate_excuse(payload)
    assert res.decision == "REVISION_MANUAL"
    assert res.escalate_to_hse is True
    assert res.is_sensitive is True


def test_umbrales_progresivos_pptx():
    # Umbral 1: 1 a 2 inasistencias en la semana -> Solo TL
    u1 = hse_engine.calculate_thresholds("c1", unjustified_week=2, unjustified_month=2)
    assert u1.current_threshold == "UMBRAL_1"
    assert u1.responsible_area == "SOLO_TL"

    # Umbral 2: 3 a 4 inasistencias en la semana -> TL escala a HSE
    u2 = hse_engine.calculate_thresholds("c2", unjustified_week=3, unjustified_month=3)
    assert u2.current_threshold == "UMBRAL_2"
    assert u2.responsible_area == "TL_ESCALA_HSE"

    # Umbral 3: 10 a 14 inasistencias en el mes -> HSE lidera
    u3 = hse_engine.calculate_thresholds("c3", unjustified_week=1, unjustified_month=11)
    assert u3.current_threshold == "UMBRAL_3"
    assert u3.responsible_area == "HSE_LIDERA"

    # Umbral 4: 15+ inasistencias en el mes -> Coordinación HSE (Proceso de Retiro)
    u4 = hse_engine.calculate_thresholds("c4", unjustified_week=4, unjustified_month=15)
    assert u4.current_threshold == "UMBRAL_4"
    assert u4.responsible_area == "COORDINACION_HSE"


def test_api_policy_evaluate():
    payload = {
        "excuse_type": "incapacidad_medica",
        "start_date": "2026-09-28",
        "end_date": "2026-09-29",
        "report_date": "2026-09-28",
        "has_attachment": True,
        "attachment_is_eps_official": True
    }
    response = client.post("/api/v1/policy/evaluate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "POSIBLEMENTE_VALIDO"
    assert data["days_calculated"] == 2


def test_api_policy_thresholds():
    response = client.get("/api/v1/policy/thresholds/coder-123?unjustified_week=3&unjustified_month=3")
    assert response.status_code == 200
    data = response.json()
    assert data["current_threshold"] == "UMBRAL_2"
    assert data["responsible_area"] == "TL_ESCALA_HSE"


def test_api_policy_motives():
    response = client.get("/api/v1/policy/motives")
    assert response.status_code == 200
    data = response.json()
    assert len(data["motives"]) == 10
