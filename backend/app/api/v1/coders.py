from fastapi import APIRouter, HTTPException, Query, status
from typing import List, Optional

from ...schemas.coder import (
    CoderBase,
    CoderIdentificationQuery,
    CoderIdentificationResult,
)
from ...schemas.coder_portal import (
    CoderExcuseSubmission,
    CoderAttendanceSummary,
)
from ...schemas.dropout_risk import (
    CoderDropoutRiskResponse,
)
from ...schemas.justification import (
    JustificationRecord,
    PipelineExecutionResult,
)
from ...services.coder_resolver import coder_resolver
from ...services.portal_service import portal_service
from ...services.dropout_risk_engine import calculate_coder_risk_score

router = APIRouter(prefix="/coders", tags=["Coders & Portal de Excusas (BE-02 / BE-07)"])


@router.post(
    "/resolve",
    response_model=CoderIdentificationResult,
    status_code=status.HTTP_200_OK,
    summary="Identificación de Coder en Cascada (BE-02)"
)
async def resolve_coder(query: CoderIdentificationQuery):
    """
    Ejecuta la cascada determinista de 4 niveles para asociar un remitente con un coder registrado:
    1. Match exacto por Email.
    2. Match exacto por Cédula (7-10 dígitos).
    3. Match de similitud por Nombre Completo (>= 82% confianza).
    4. Fallback: CODER_NOT_FOUND.
    """
    return coder_resolver.identify_coder(query)


@router.get(
    "/count",
    summary="Total de coders registrados en el índice"
)
async def get_coders_count():
    """Retorna la cantidad total de coders cargados en el índice de resolución."""
    return {
        "total_coders": len(coder_resolver._coders_list),
        "status": "ready"
    }


@router.post(
    "/excuses",
    response_model=PipelineExecutionResult,
    status_code=status.HTTP_201_CREATED,
    summary="Radicación Directa de Excusa por el Coder (BE-07)"
)
async def submit_coder_excuse(submission: CoderExcuseSubmission):
    """
    Permite al coder radicar formalmente su inasistencia desde el Portal Web / Moodle:
    - Captura información mínima obligatoria (Slide 4 PPTX).
    - Canaliza automáticamente el caso por el pipeline de evaluación determinista.
    """
    return portal_service.submit_excuse(submission)


@router.get(
    "/excuses",
    response_model=List[JustificationRecord],
    summary="Historial de Excusas del Coder"
)
async def list_coder_excuses(
    coder_email: Optional[str] = Query(None, description="Filtrar por correo del coder"),
    coder_cedula: Optional[str] = Query(None, description="Filtrar por cédula del coder")
):
    """Retorna las justificaciones radicadas por un estudiante."""
    return portal_service.get_coder_excuses(coder_email=coder_email, coder_cedula=coder_cedula)


@router.get(
    "/{coder_identifier}/attendance-summary",
    response_model=CoderAttendanceSummary,
    summary="Semáforo de Asistencia y Nivel de Umbral del Coder (Slide 6 y 7)"
)
async def get_coder_attendance_summary(coder_identifier: str):
    """
    Retorna el resumen de faltas justificadas, injustificadas y el nivel de umbral activo (Umbrales 1 al 4).
    """
    return portal_service.get_attendance_summary(coder_identifier)


@router.get(
    "/search",
    response_model=List[CoderBase],
    summary="Búsqueda rápida de coders por término"
)
async def search_coders(q: str = Query(..., min_length=2, description="Cédula, nombre o correo")):
    """Búsqueda rápida en el catálogo de coders para autocompletado en el frontend."""
    term = q.strip().lower()
    results = []
    for c in coder_resolver._coders_list:
        if term in c.full_name.lower() or term in c.cedula or term in c.email.lower() or (c.route and term in c.route.lower()):
            results.append(c)
            if len(results) >= 20:
                break
    return results


@router.get(
    "/{coder_id}/risk-score",
    response_model=CoderDropoutRiskResponse,
    summary="Predictive Coder Dropout Risk Score (IA-EXT-01)"
)
async def get_coder_dropout_risk_score(coder_id: str):
    """
    Calcula el Score de Riesgo de Deserción Escolar (0-100) y Semáforo de Permanencia:
    - Analiza frecuencia y recencia de ausencias (ventanas de 30 y 14 días).
    - Proporción de inasistencias injustificadas vs justificadas.
    - Mapea el nivel de alerta con los umbrales reglamentarios de Riwi (U1, U2, U3, U4).
    - Entrega recomendación accionable para el Team Leader y Bienestar HSE.
    """
    clean_id = coder_id.strip().lower()
    coder = (
        coder_resolver._coders_by_email.get(clean_id)
        or coder_resolver._coders_by_cedula.get(clean_id)
    )
    if not coder:
        for c in coder_resolver._coders_list:
            if c.id == coder_id:
                coder = c
                break

    coder_name = coder.full_name if coder else "Coder Riwi"
    c_id = coder.id if coder else coder_id

    # Consultar justificaciones radicadas en el sistema
    excuses = portal_service.get_coder_excuses(
        coder_email=coder.email if coder else (clean_id if "@" in clean_id else None),
        coder_cedula=coder.cedula if coder else (clean_id if "@" not in clean_id else None)
    )
    approved = sum(1 for e in excuses if e.status == "APPROVED")
    disapproved = sum(1 for e in excuses if e.status == "DISAPPROVED")
    pending = sum(1 for e in excuses if e.status in ["REVISION_MANUAL", "PENDIENTE_DECISION_TL", "CODER_NOT_FOUND"])
    justifications_count = {
        "approved": approved,
        "disapproved": disapproved,
        "pending": pending
    }

    # Transformar historial de justificaciones en eventos de asistencia
    attendance_history = []
    for e in excuses:
        attendance_history.append({
            "date": e.created_at[:10] if isinstance(e.created_at, str) else str(e.created_at),
            "status": "JUSTIFIED_ABSENCE" if e.status == "APPROVED" else "UNJUSTIFIED_ABSENCE",
            "justified": e.status == "APPROVED",
        })

    # Si el adaptador de plataforma hermana tiene registros reales, los incorporamos
    try:
        from ...services.hse_engine import hse_engine
        adapter = hse_engine.attendance_adapter
        if hasattr(adapter, "_attendance_db"):
            records = adapter._attendance_db.get(c_id, [])
            for r in records:
                attendance_history.append({
                    "date": str(r.attendance_date),
                    "status": r.status.value if hasattr(r.status, "value") else str(r.status),
                    "justified": r.status in ("EXCUSED", "PRESENT")
                })
    except Exception:
        pass

    risk_data = calculate_coder_risk_score(
        attendance_history=attendance_history,
        justifications_count=justifications_count,
        coder_id=c_id,
        coder_name=coder_name,
    )
    return CoderDropoutRiskResponse(**risk_data)
