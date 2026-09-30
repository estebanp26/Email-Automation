"""Matriz de Pruebas de Integración y Regresión de Políticas HSE (QA-04).

Cubre con ``pytest + httpx`` la matriz completa de reglas de negocio:

- Plazo GENERAL de 48h hábiles (lun-vie, sin festivos): incapacidad médica,
  malestar sin incapacidad, falla técnica con comprobante.
- Plazo de FUERZA MAYOR de 72h / 3 días hábiles: calamidad doméstica y luto
  de primer/segundo grado (G1/G2). Sin soporte dentro del plazo -> NUNCA
  ``POSIBLEMENTE_INVALIDO`` directo, sino ``REVISION_MANUAL`` con regla
  ``FUERZA_MAYOR_SIN_SOPORTE_PENDIENTE``.
- Casos de rechazo fulminante, previsibles extemporáneos, sensibles y
  umbrales progresivos.
- Integración API vía ``httpx.AsyncClient`` (``ASGITransport``).

Ejecución con cobertura (criterio: >85% en ``hse_rules.py``)::

    pytest backend/tests/test_qa04_hse_matrix.py -v \\
        --cov=backend/app/services/hse_rules \\
        --cov=backend/app/services/hse_engine \\
        --cov-report=term-missing --cov-fail-under=85
"""

from datetime import date, datetime

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.app.main import app
from backend.app.schemas.policy import PolicyEvaluationInput
from backend.app.services.hse_engine import HSEPolicyEngine
from backend.app.services.hse_rules import (
    FUERZA_MAYOR_MOTIVES,
    GENERAL_DEADLINE_MOTIVES,
    HSERules,
    business_days_elapsed,
    business_hours_between,
    classify_kinship,
    evaluate_excuse,
    hse_rules,
    is_business_day,
    is_within_fuerza_mayor_deadline,
    is_within_general_deadline,
)

NO_EXT = {"verify_external_attendance": False}


def _payload(**overrides):
    base = {
        "excuse_type": "incapacidad_medica",
        "start_date": "2026-09-28",  # lunes
        "end_date": "2026-09-28",
        "report_date": "2026-09-29",  # martes
        "verify_external_attendance": False,
    }
    base.update(overrides)
    return PolicyEvaluationInput(**base)


# ===========================================================================
# 1. HELPERS DE HORAS/DÍAS HÁBILES
# ===========================================================================

@pytest.mark.parametrize(
    "day,expected",
    [
        ("2026-09-28", True),  # lunes
        ("2026-09-25", True),  # viernes
        ("2026-09-26", False),  # sábado
        ("2026-09-27", False),  # domingo
        ("2026-12-25", False),  # Navidad (festivo, viernes)
        ("2026-12-24", True),  # jueves previo a Navidad
    ],
)
def test_is_business_day(day, expected):
    assert is_business_day(date.fromisoformat(day)) is expected


@pytest.mark.parametrize(
    "start,report,expected",
    [
        ("2026-09-28", "2026-09-29", 1),  # lun -> mar
        ("2026-09-28", "2026-09-28", 0),  # mismo día
        ("2026-09-29", "2026-09-28", 0),  # reporte previo
        ("2026-09-25", "2026-09-28", 1),  # vie -> lun (finde no cuenta)
        ("2026-09-28", "2026-10-05", 5),  # lun -> lun siguiente
        ("2026-12-24", "2026-12-28", 1),  # jue -> lun (25 festivo + finde)
    ],
)
def test_business_days_elapsed(start, report, expected):
    assert business_days_elapsed(date.fromisoformat(start), date.fromisoformat(report)) == expected


def test_business_hours_between_weekend_not_counted():
    # Sáb 10:00 -> Lun 10:00: solo cuentan las 10h del lunes.
    start = datetime(2026, 9, 26, 10, 0)
    end = datetime(2026, 9, 28, 10, 0)
    assert business_hours_between(start, end) == pytest.approx(10.0)


def test_business_hours_between_friday_to_tuesday_edge():
    # Vie 17:00 -> Mar 17:00 = 7h (vie) + 24h (lun) + 17h (mar) = 48h.
    start = datetime(2026, 9, 25, 17, 0)
    assert business_hours_between(start, datetime(2026, 9, 29, 17, 0)) == pytest.approx(48.0)
    # Un minuto más -> supera las 48h hábiles (rechazo fulminante de plazo).
    assert business_hours_between(start, datetime(2026, 9, 29, 17, 1)) > 48.0
    assert business_hours_between(datetime(2026, 9, 29, 17, 0), start) == 0.0


@pytest.mark.parametrize(
    "raw,expected",
    [("G1", "G1"), ("g1", "G1"), ("primer_grado", "G1"), ("G2", "G2"),
     ("SEGUNDO", "G2"), ("G3", "G3_MAS"), (None, "NO_ESPECIFICADO"), ("", "NO_ESPECIFICADO")],
)
def test_classify_kinship(raw, expected):
    assert classify_kinship(raw) == expected


def test_deadline_predicates():
    assert is_within_general_deadline(date(2026, 9, 28), date(2026, 9, 30)) is True  # 2 hábiles
    assert is_within_general_deadline(date(2026, 9, 27), date(2026, 9, 30)) is False  # 3 hábiles
    assert is_within_fuerza_mayor_deadline(date(2026, 9, 30), date(2026, 10, 5)) is True  # 3 hábiles
    assert is_within_fuerza_mayor_deadline(date(2026, 9, 30), date(2026, 10, 6)) is False  # 4 hábiles


# ===========================================================================
# 2. PLAZO GENERAL 48H HÁBILES (incapacidad con/sin firma)
# ===========================================================================

def test_incapacidad_con_firma_eps_oportuna():
    res = evaluate_excuse(_payload(
        has_attachment=True, attachment_is_eps_official=True))
    assert res.decision == "POSIBLEMENTE_VALIDO"
    assert res.is_timely is True
    assert res.support_valid is True


def test_incapacidad_fin_de_semana_no_consume_plazo():
    """Vie 25 -> Mar 29: 4 días calendario pero solo 2 hábiles -> VÁLIDO.

    El motor BE-05 puro lo marcaría FUERZA_MAYOR_VENCIDA (delta 4 > 3);
    la fachada QA-04 lo rehabilita por cómputo en horas hábiles.
    """
    res = evaluate_excuse(_payload(
        start_date="2026-09-25", end_date="2026-09-25", report_date="2026-09-29",
        has_attachment=True, attachment_is_eps_official=True))
    assert res.decision == "POSIBLEMENTE_VALIDO"
    assert res.is_timely is True


def test_incapacidad_extemporanea_48h_habiles():
    """Dom 27 -> Mié 30: 3 días calendario (motor lo vería oportuno) pero
    3 hábiles > 2 -> INVÁLIDO por 48h hábiles."""
    res = evaluate_excuse(_payload(
        start_date="2026-09-27", end_date="2026-09-27", report_date="2026-09-30",
        has_attachment=True, attachment_is_eps_official=True))
    assert res.decision == "POSIBLEMENTE_INVALIDO"
    assert res.is_timely is False
    assert res.policy_rule_triggered == "INCAPACIDAD_EXTEMPORANEA_48H"


def test_incapacidad_vencida_calendario_y_habiles():
    res = evaluate_excuse(_payload(
        start_date="2026-09-21", end_date="2026-09-21", report_date="2026-09-28",
        has_attachment=True, attachment_is_eps_official=True))
    assert res.decision == "POSIBLEMENTE_INVALIDO"
    assert res.is_timely is False


def test_incapacidad_sin_firma_eps_revision():
    res = evaluate_excuse(_payload(
        has_attachment=True, attachment_is_eps_official=False))
    assert res.decision == "REVISION_MANUAL"
    assert res.escalate_to_hse is True
    assert res.policy_rule_triggered == "INCAPACIDAD_NO_EPS_OFICIAL"


def test_incapacidad_sin_adjunto_invalida():
    res = evaluate_excuse(_payload(has_attachment=False))
    assert res.decision == "POSIBLEMENTE_INVALIDO"
    assert res.policy_rule_triggered == "FALTA_SOPORTE_OBLIGATORIO"


def test_malestar_limite_2_dias():
    r2 = evaluate_excuse(_payload(
        excuse_type="enfermo_sin_incapacidad",
        start_date="2026-09-28", end_date="2026-09-29"))
    assert r2.decision == "POSIBLEMENTE_VALIDO"
    r3 = evaluate_excuse(_payload(
        excuse_type="enfermo_sin_incapacidad",
        start_date="2026-09-28", end_date="2026-09-30"))
    assert r3.decision == "POSIBLEMENTE_INVALIDO"
    assert r3.policy_rule_triggered == "MALESTAR_SUPERA_2_DIAS"


# ===========================================================================
# 3. FUERZA MAYOR 72H: calamidad/luto G1-G2 (nunca INVALIDO directo por soporte)
# ===========================================================================

def test_luto_g1_con_acta_valido_con_acompanamiento():
    res = evaluate_excuse(_payload(
        excuse_type="dificultades_familiares", has_attachment=True,
        kinship_degree="G1"))
    assert res.decision == "POSIBLEMENTE_VALIDO"
    assert res.policy_rule_triggered == "FUERZA_MAYOR_SOPORTADA"
    assert res.escalate_to_hse is True  # acompañamiento, no sanción
    assert res.is_timely is True


def test_luto_g2_sin_soporte_revision_no_invalido():
    """CLAVE QA-04: sin acta pero dentro de 72h -> REVISION, jamás INVALIDO."""
    res = evaluate_excuse(_payload(
        excuse_type="dificultades_familiares", has_attachment=False,
        kinship_degree="G2"))
    assert res.decision == "REVISION_MANUAL"
    assert res.decision != "POSIBLEMENTE_INVALIDO"
    assert res.policy_rule_triggered == "FUERZA_MAYOR_SIN_SOPORTE_PENDIENTE"
    assert res.requires_human_review is True
    assert res.escalate_to_hse is True


@pytest.mark.parametrize("alias", sorted(FUERZA_MAYOR_MOTIVES - {"dificultades_familiares"}))
def test_alias_calamidad_luto_sin_soporte_revision(alias):
    res = evaluate_excuse(_payload(excuse_type=alias, has_attachment=False))
    assert res.decision == "REVISION_MANUAL"
    assert res.policy_rule_triggered == "FUERZA_MAYOR_SIN_SOPORTE_PENDIENTE"


def test_calamidad_limite_3_dias_habiles_vigente():
    # Mié 30 -> Lun 05: 3 hábiles (jue, vie, lun) -> aún vigente.
    res = evaluate_excuse(_payload(
        excuse_type="dificultades_familiares", start_date="2026-09-30",
        end_date="2026-09-30", report_date="2026-10-05",
        has_attachment=False, kinship_degree="G1"))
    assert res.decision == "REVISION_MANUAL"
    assert res.is_timely is True


def test_calamidad_vencida_72h_con_acta():
    # Mié 30 -> Mar 06: 4 hábiles -> vencida aunque tenga acta.
    res = evaluate_excuse(_payload(
        excuse_type="dificultades_familiares", start_date="2026-09-30",
        end_date="2026-09-30", report_date="2026-10-06",
        has_attachment=True, kinship_degree="G1"))
    assert res.decision == "POSIBLEMENTE_INVALIDO"
    assert res.policy_rule_triggered == "FUERZA_MAYOR_VENCIDA"
    assert res.is_timely is False


def test_luto_g3_dentro_plazo_no_invalido_directo():
    res = evaluate_excuse(_payload(
        excuse_type="luto", has_attachment=False, kinship_degree="G3"))
    assert res.decision == "REVISION_MANUAL"
    assert res.policy_rule_triggered == "FUERZA_MAYOR_SIN_SOPORTE_PENDIENTE"


# ===========================================================================
# 4. FALLA TÉCNICA CON/SIN COMPROBANTE
# ===========================================================================

def test_falla_tecnica_con_comprobante_valida():
    res = evaluate_excuse(_payload(excuse_type="falla_tecnica", has_attachment=True))
    assert res.decision == "POSIBLEMENTE_VALIDO"
    assert res.policy_rule_triggered == "FALLA_TECNICA_SOPORTADA"


def test_falla_tecnica_sin_comprobante_revision():
    res = evaluate_excuse(_payload(excuse_type="falla_tecnica", has_attachment=False))
    assert res.decision == "REVISION_MANUAL"
    assert res.policy_rule_triggered == "FALLA_TECNICA_SIN_COMPROBANTE"
    assert res.requires_human_review is True


def test_falla_tecnica_extemporanea_invalida():
    res = evaluate_excuse(_payload(
        excuse_type="falla_tecnica", has_attachment=True,
        start_date="2026-09-21", report_date="2026-09-28"))
    assert res.decision == "POSIBLEMENTE_INVALIDO"
    assert res.policy_rule_triggered == "FALLA_TECNICA_EXTEMPORANEA"


# ===========================================================================
# 5. PREVISIBLES, RECHAZO FULMINANTE, SENSIBLES, UMBRALES
# ===========================================================================

def test_cita_medica_previsible_extemporanea():
    res = evaluate_excuse(_payload(excuse_type="cita_medica", has_attachment=True))
    assert res.decision == "POSIBLEMENTE_INVALIDO"
    assert res.policy_rule_triggered == "PREVISIBLE_EXTEMPORANEO"


def test_cita_medica_con_preaviso_valida():
    res = evaluate_excuse(_payload(
        excuse_type="cita_medica", report_date="2026-09-27", has_attachment=True))
    assert res.is_timely is True
    assert res.decision == "POSIBLEMENTE_VALIDO"


def test_rechazo_fulminante_falta_injustificada():
    res = evaluate_excuse(_payload(excuse_type="falta_injustificada"))
    assert res.decision == "POSIBLEMENTE_INVALIDO"
    assert res.policy_rule_triggered == "FALTA_INJUSTIFICADA"
    assert res.support_valid is False


def test_caso_sensible_escalamiento():
    res = evaluate_excuse(_payload(
        excuse_type="situacion_emocional_critica",
        start_date="2026-09-29", end_date="2026-09-29", report_date="2026-09-29"))
    assert res.decision == "REVISION_MANUAL"
    assert res.escalate_to_hse is True
    assert res.is_sensitive is True
    assert res.policy_rule_triggered == "CASO_SENSIBLE_HSE"


@pytest.mark.parametrize(
    "week,month,expected,area",
    [(0, 0, "NINGUNO", "SOLO_TL"), (2, 2, "UMBRAL_1", "SOLO_TL"),
     (3, 3, "UMBRAL_2", "TL_ESCALA_HSE"), (1, 11, "UMBRAL_3", "HSE_LIDERA"),
     (4, 15, "UMBRAL_4", "COORDINACION_HSE"), (0, 14, "UMBRAL_3", "HSE_LIDERA")],
)
def test_umbrales_progresivos(week, month, expected, area):
    summary = hse_rules.engine.calculate_thresholds("coder-qa04", week, month)
    assert summary.current_threshold == expected
    assert summary.responsible_area == area


def test_motivos_generales_registrados():
    assert "incapacidad_medica" in GENERAL_DEADLINE_MOTIVES
    assert "dificultades_familiares" in FUERZA_MAYOR_MOTIVES


# ===========================================================================
# 6. COTEJO PLATAFORMA HERMANA (mock desacoplado)
# ===========================================================================

def test_sister_platform_absent_confirma_valido():
    from datetime import date as _date
    from backend.app.adapters.sister_platform.mock_service import (
        MockSisterPlatformAttendanceService,
    )
    from backend.app.ports.sister_platform import AttendanceStatus

    mock = MockSisterPlatformAttendanceService(auto_generate=False)
    mock.set_coder_attendance("coder-qa04-absent", _date(2026, 9, 28), AttendanceStatus.ABSENT)
    engine = HSEPolicyEngine(attendance_adapter=mock)
    rules = HSERules(engine=engine)
    res = rules.evaluate_excuse(_payload(
        coder_id="coder-qa04-absent",
        has_attachment=True, attachment_is_eps_official=True,
        verify_external_attendance=True))
    assert res.absence_verified is True
    assert res.external_absence_status == "ABSENT"
    assert res.decision == "POSIBLEMENTE_VALIDO"


def test_sister_platform_presente_contradictorio_invalida():
    from datetime import date as _date
    from backend.app.adapters.sister_platform.mock_service import (
        MockSisterPlatformAttendanceService,
    )
    from backend.app.ports.sister_platform import AttendanceStatus

    mock = MockSisterPlatformAttendanceService(auto_generate=False)
    mock.set_coder_attendance("coder-qa04-present", _date(2026, 9, 28), AttendanceStatus.PRESENT)
    engine = HSEPolicyEngine(attendance_adapter=mock)
    rules = HSERules(engine=engine)
    res = rules.evaluate_excuse(_payload(
        coder_id="coder-qa04-present",
        has_attachment=True, attachment_is_eps_official=True,
        verify_external_attendance=True))
    assert res.external_absence_status == "PRESENT"
    assert res.policy_rule_triggered == "REGISTRO_PRESENTE_CONTRADICTORIO"
    assert res.decision == "POSIBLEMENTE_INVALIDO"


# ===========================================================================
# 7. INTEGRACIÓN API CON HTTPX (ASGI)
# ===========================================================================

@pytest_asyncio.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
async def test_api_evaluate_incapacidad_valida(async_client):
    resp = await async_client.post("/api/v1/policy/evaluate", json={
        "excuse_type": "incapacidad_medica", "start_date": "2026-09-28",
        "end_date": "2026-09-29", "report_date": "2026-09-28",
        "has_attachment": True, "attachment_is_eps_official": True,
        "verify_external_attendance": False})
    assert resp.status_code == 200
    assert resp.json()["decision"] == "POSIBLEMENTE_VALIDO"


@pytest.mark.asyncio
async def test_api_evaluate_48h_habiles_rehabilita_fin_de_semana(async_client):
    resp = await async_client.post("/api/v1/policy/evaluate", json={
        "excuse_type": "incapacidad_medica", "start_date": "2026-09-25",
        "end_date": "2026-09-25", "report_date": "2026-09-29",
        "has_attachment": True, "attachment_is_eps_official": True,
        "verify_external_attendance": False})
    assert resp.status_code == 200
    assert resp.json()["decision"] == "POSIBLEMENTE_VALIDO"


@pytest.mark.asyncio
async def test_api_evaluate_calamidad_sin_soporte_no_invalida(async_client):
    resp = await async_client.post("/api/v1/policy/evaluate", json={
        "excuse_type": "dificultades_familiares", "start_date": "2026-09-28",
        "end_date": "2026-09-28", "report_date": "2026-09-29",
        "has_attachment": False, "kinship_degree": "G1",
        "verify_external_attendance": False})
    assert resp.status_code == 200
    data = resp.json()
    assert data["decision"] == "REVISION_MANUAL"
    assert data["policy_rule_triggered"] == "FUERZA_MAYOR_SIN_SOPORTE_PENDIENTE"


@pytest.mark.asyncio
async def test_api_thresholds(async_client):
    resp = await async_client.get(
        "/api/v1/policy/thresholds/coder-123",
        params={"unjustified_week": 3, "unjustified_month": 3})
    assert resp.status_code == 200
    assert resp.json()["current_threshold"] == "UMBRAL_2"


@pytest.mark.asyncio
async def test_api_motives_catalogo_10(async_client):
    resp = await async_client.get("/api/v1/policy/motives")
    assert resp.status_code == 200
    assert len(resp.json()["motives"]) == 10
