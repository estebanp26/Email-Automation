from fastapi import APIRouter, Query, status
from typing import List

from ...schemas.notification import (
    NotificationDispatchInput,
    NotificationDispatchResult,
    NotificationPreviewRequest,
)
from ...services.notification import notification_service

router = APIRouter(prefix="/notifications", tags=["Notificaciones & Plantillas de Correo (BE-04)"])


@router.post(
    "/dispatch",
    response_model=NotificationDispatchResult,
    status_code=status.HTTP_200_OK,
    summary="Despacho de Notificación por Correo (BE-04)"
)
async def dispatch_notification(payload: NotificationDispatchInput):
    """
    Construye y despacha una notificación HTML profesional conforme al protocolo Riwi:
    - `APPROVED`: Justificada (recuerda que no cuenta para umbrales).
    - `DISAPPROVED`: Rechazada (advierte sobre registro Moodle y umbrales).
    - `REQUEST_MORE_INFO`: Requerimiento con plazo máx de 3 días hábiles.
    - `CODER_NOT_FOUND`: Solicitud formal de matrícula y cédula.
    - `HSE_ALERT`: Alerta interna de permanencia a HSE.
    """
    return notification_service.dispatch(payload)


@router.post(
    "/preview",
    summary="Vista Previa de Plantilla HTML"
)
async def preview_notification_template(req: NotificationPreviewRequest):
    """Genera la vista previa del asunto y del HTML renderizado sin despacharlo."""
    return notification_service.preview_template(req)


@router.get(
    "/outbox",
    response_model=List[NotificationDispatchResult],
    summary="Historial de Correos Despachados (Outbox)"
)
async def get_notification_outbox(limit: int = Query(25, ge=1, le=100)):
    """Retorna la lista de notificaciones despachadas por el sistema."""
    return notification_service.list_outbox(limit=limit)
