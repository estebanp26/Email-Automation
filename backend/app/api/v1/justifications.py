from fastapi import APIRouter, HTTPException, status
from typing import List

from ...schemas.resolution import (
    ManualResolutionInput,
    ReconsiderationInput,
    ResolutionAuditEntry,
    ResolutionResponse,
)
from ...services.resolution_service import resolution_service

router = APIRouter(prefix="/justifications", tags=["Resolución Manual & Reconsideración (BE-06)"])


@router.post(
    "/{justification_id}/resolve",
    response_model=ResolutionResponse,
    status_code=status.HTTP_200_OK,
    summary="Resolución Manual por Team Leader / HSE (BE-06)"
)
async def resolve_justification_endpoint(
    justification_id: str,
    payload: ManualResolutionInput
):
    """
    Permite al TL o Analista HSE validar y emitir decisión formal (Slide 4 y 5 PPTX):
    - `APPROVE`: Justificada formalmente.
    - `DISAPPROVE`: No justificada (registra falta en Moodle).
    - `REQUEST_MORE_INFO`: Solicita evidencias adicionales (plazo máx 3 días).
    """
    try:
        return resolution_service.resolve_justification(justification_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error resolviendo justificación: {str(e)}")


@router.post(
    "/{justification_id}/reconsider",
    response_model=ResolutionResponse,
    status_code=status.HTTP_200_OK,
    summary="Reconsideración y Rectificación de Decisión por HSE"
)
async def reconsider_justification_endpoint(
    justification_id: str,
    payload: ReconsiderationInput
):
    """
    Permite la reapertura formal de un caso ante nuevos soportes o descargos (Slide 6 Umbral 4).
    """
    try:
        return resolution_service.reconsider_justification(justification_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/{justification_id}/audit-trail",
    response_model=List[ResolutionAuditEntry],
    summary="Historial Inmutable de Auditoría Humana"
)
async def get_justification_audit_trail(justification_id: str):
    """Retorna la bitácora de intervenciones humanas realizadas sobre la justificación."""
    return resolution_service.get_audit_trail(justification_id)
