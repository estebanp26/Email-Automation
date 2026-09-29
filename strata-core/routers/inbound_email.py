from __future__ import annotations

import logging
from typing import Dict, Any, Union
from fastapi import APIRouter, BackgroundTasks, Response, status, HTTPException
from fastapi.responses import JSONResponse

from schemas.inbound_dto import (
    InboundEmailDTO,
    InboundEmailResponse,
    IdempotencyResponse
)
from services.inbound_service import inbound_service

logger = logging.getLogger("InboundEmailRouter")

router = APIRouter(
    prefix="/api/v1",
    tags=["Inbound Email"]
)


@router.post(
    "/inbound-email",
    response_model=Union[InboundEmailResponse, IdempotencyResponse],
    summary="Recepción y normalización de eventos de correo (Outlook y Gmail)",
    description=(
        "Recibe eventos de correo desde adaptadores de Outlook y Gmail, valida su esquema, "
        "almacena temporalmente los adjuntos en disco seguro, garantiza idempotencia "
        "y encola el evento para identificación y validación con estado PENDING_IDENTIFICATION."
    )
)
async def receive_inbound_email(
    dto: InboundEmailDTO,
    background_tasks: BackgroundTasks,
    response: Response
) -> Union[InboundEmailResponse, IdempotencyResponse]:
    """
    Controlador central de ingesta desacoplada de correos.
    - Retorna HTTP 200 OK con 'Event already processed' si el message_id ya fue recibido.
    - Retorna HTTP 202 Accepted si el correo es nuevo y se encoló con éxito.
    """
    # 1. Detección y rechazo de payload duplicado (Garantía de Idempotencia)
    if inbound_service.is_message_already_processed(dto.message_id):
        logger.info(f"Idempotencia detectada: Correo duplicado con message_id '{dto.message_id}'.")
        response.status_code = status.HTTP_200_OK
        return IdempotencyResponse(
            status="OK",
            message="Event already processed",
            message_id=dto.message_id
        )

    # 2. Almacenamiento seguro y temporal de archivos adjuntos en disco
    saved_attachments = inbound_service.save_attachments_securely(
        message_id=dto.message_id,
        attachments=dto.attachments
    )
    dto.attachments = saved_attachments

    # 3. Almacenamiento de registro transaccional con estado PENDING_IDENTIFICATION
    record = inbound_service.store_transactional_record(
        dto=dto,
        status="PENDING_IDENTIFICATION"
    )

    # 4. Encolamiento asíncrono para identificación del coder y validación con Strata Core
    background_tasks.add_task(
        inbound_service.enqueue_for_identification_and_validation,
        dto=dto,
        transaction_id=record["id"]
    )

    # 5. Respuesta HTTP 202 Accepted
    response.status_code = status.HTTP_202_ACCEPTED
    return InboundEmailResponse(
        status="ACCEPTED",
        message="Event queued for identification and validation",
        message_id=dto.message_id,
        conversation_id=dto.conversation_id,
        transaction_id=record["id"],
        state="PENDING_IDENTIFICATION",
        attachments_count=len(saved_attachments)
    )


@router.get(
    "/inbound-email/queue",
    summary="Consultar eventos encolados para validación"
)
async def get_queued_inbound_events():
    """Retorna la lista de eventos encolados en espera de validación."""
    return {
        "total_queued": len(inbound_service.event_queue),
        "events": inbound_service.event_queue
    }
