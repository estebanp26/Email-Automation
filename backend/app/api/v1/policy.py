from fastapi import APIRouter, status
from typing import Dict, Any, List

from ...schemas.policy import (
    PolicyEvaluationInput,
    PolicyEvaluationResult,
    AttendanceThresholdSummary,
)
from ...services.hse_engine import hse_engine
from ...services.hse_rules import hse_rules as hse_rules_facade

router = APIRouter(prefix="/policy", tags=["Políticas HSE & Umbrales (BE-05)"])


@router.post(
    "/evaluate",
    response_model=PolicyEvaluationResult,
    status_code=status.HTTP_200_OK,
    summary="Evaluación Determinista de Políticas HSE (BE-05)"
)
async def evaluate_policy(payload: PolicyEvaluationInput):
    """
    Evalúa una justificación contra las reglas de la Presentación de Asistencias de Riwi:
    - 10 motivos oficiales
    - Ventana temporal en horas hábiles (48h general / 72h fuerza mayor, QA-04)
    - Límite de 2 días para malestar sin incapacidad
    - Detección de casos confidenciales sensibles
    - Calamidad/luto como FUERZA_MAYOR (nunca inválido directo por falta de soporte)
    """
    return hse_rules_facade.evaluate_excuse(payload)


@router.get(
    "/thresholds/{coder_id}",
    response_model=AttendanceThresholdSummary,
    summary="Cálculo de Umbrales Progresivos de Permanencia (Slide 6 y 7)"
)
async def get_coder_thresholds(
    coder_id: str,
    unjustified_week: int = 0,
    unjustified_month: int = 0
):
    """
    Calcula el umbral de permanencia activo (Umbral 1 a 4) según inasistencias injustificadas acumuladas.
    """
    return hse_engine.calculate_thresholds(coder_id, unjustified_week, unjustified_month)


@router.get(
    "/motives",
    summary="Catálogo oficial de los 10 motivos de inasistencia (Slide 8 PPTX)"
)
async def list_official_motives():
    """Retorna el catálogo oficial de motivos y sus condiciones de soporte."""
    return {
        "motives": [
            {"id": "incapacidad_medica", "name": "Incapacidad médica", "requires_attachment": True, "eps_official": True, "max_days_without_cert": 0},
            {"id": "enfermo_sin_incapacidad", "name": "Enfermo sin incapacidad", "requires_attachment": False, "max_days_without_cert": 2},
            {"id": "cita_medica", "name": "Cita médica", "requires_attachment": True, "previsible": True},
            {"id": "dificultades_familiares", "name": "Dificultades familiares", "requires_attachment": False, "fuerza_mayor": True},
            {"id": "problemas_economicos", "name": "Problemas económicos", "requires_attachment": False, "escalate_hse": True},
            {"id": "jornada_laboral", "name": "Jornada laboral", "requires_attachment": True, "previsible": True},
            {"id": "jornada_estudio", "name": "Jornada de estudio", "requires_attachment": True, "previsible": True},
            {"id": "situacion_emocional_critica", "name": "Situación emocional crítica", "requires_attachment": False, "sensitive": True, "escalate_hse": True},
            {"id": "tramite_institucional", "name": "Trámite institucional", "requires_attachment": True, "previsible": True},
            {"id": "falta_injustificada", "name": "Falta Injustificada", "requires_attachment": False, "always_invalid": True}
        ]
    }
