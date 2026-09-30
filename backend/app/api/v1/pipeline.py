from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from typing import List, Optional

from ...schemas.email import RawEmailInput, NormalizedEmail
from ...schemas.justification import (
    JustificationRecord,
    PipelineProcessRequest,
    PipelineExecutionResult,
)
from ...services.orchestrator import orchestrator

router = APIRouter(prefix="/pipeline", tags=["Pipeline & Orquestación Asíncrona (BE-03)"])


@router.post(
    "/process",
    response_model=PipelineExecutionResult,
    status_code=status.HTTP_200_OK,
    summary="Ejecución Síncrona del Pipeline de Justificaciones (BE-03)"
)
async def process_justification_pipeline(request: PipelineProcessRequest):
    """
    Ejecuta el ciclo de vida completo de una novedad:
    1. Normalización del correo.
    2. Identificación del Coder en cascada.
    3. Evaluación de soportes y políticas HSE.
    4. Cálculo de umbrales y veredicto.
    5. Persistencia del registro.
    """
    input_data = request.normalized_email or request.raw_email
    if not input_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe proporcionar 'raw_email' o 'normalized_email' en el cuerpo de la petición."
        )
    return orchestrator.process_pipeline(input_data)


@router.post(
    "/queue",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Encolamiento Asíncrono de Justificación (Background Task)"
)
async def queue_justification_pipeline(
    raw_email: RawEmailInput,
    background_tasks: BackgroundTasks
):
    """
    Encola el procesamiento del correo en segundo plano para no bloquear la respuesta HTTP.
    """
    background_tasks.add_task(orchestrator.process_pipeline, raw_email)
    return {
        "status": "QUEUED",
        "message": "Correo encolado para procesamiento asíncrono en segundo plano.",
        "sender": raw_email.sender_email
    }


@router.get(
    "/records",
    response_model=List[JustificationRecord],
    summary="Listado de justificaciones procesadas"
)
async def list_justification_records(
    status: Optional[str] = Query(None, description="APPROVED, DISAPPROVED, REVISION_MANUAL, CODER_NOT_FOUND"),
    clan: Optional[str] = Query(None, description="Filtro por clan o ruta de formación")
):
    """Retorna las justificaciones procesadas con filtros opcionales de estado o clan."""
    return orchestrator.list_records(status=status, clan=clan)


@router.get(
    "/records/{justification_id}",
    response_model=JustificationRecord,
    summary="Detalle de una justificación por ID"
)
async def get_justification_record(justification_id: str):
    """Consulta los detalles de auditoría completa de una justificación específica."""
    rec = orchestrator.get_record_by_id(justification_id)
    if not rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró la justificación con ID '{justification_id}'."
        )
    return rec
