import os
import hmac
import hashlib
import logging
from typing import Dict, Any, Union, Optional
from fastapi import APIRouter, BackgroundTasks, Response, Header, Request, status, HTTPException
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


async def verify_inbound_auth(
    authorization: Optional[str] = None,
    x_api_key: Optional[str] = None,
    x_signature_sha256: Optional[str] = None,
    raw_body: bytes = b""
) -> None:
    """Valida la autenticación por clave de API interna (Bearer / X-API-Key) y HMAC."""
    expected_key = os.getenv("INBOUND_API_KEY") or os.getenv("INTERNAL_API_KEY")
    expected_hmac = os.getenv("INBOUND_HMAC_SECRET")

    if expected_key:
        token = None
        if authorization and authorization.lower().startswith("bearer "):
            token = authorization[7:].strip()
        elif x_api_key:
            token = x_api_key.strip()

        if not token or not hmac.compare_digest(token, expected_key):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized: Clave de API interna inválida o ausente en cabeceras Bearer / X-API-Key"
            )

    if expected_hmac:
        computed_sig = hmac.new(expected_hmac.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
        if not x_signature_sha256 or not hmac.compare_digest(x_signature_sha256, computed_sig):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized: Firma HMAC-SHA256 inválida o ausente en X-Signature-SHA256"
            )


@router.post(
    "/inbound-email",
    response_model=Union[InboundEmailResponse, IdempotencyResponse],
    summary="Recepción y normalización de eventos de correo (Outlook y Gmail)",
    description=(
        "Recibe eventos de correo desde adaptadores de Outlook y Gmail, valida autenticación interna, "
        "almacena temporalmente los adjuntos en disco seguro, garantiza idempotencia "
        "y encola el evento para identificación y validación con estado PENDING_IDENTIFICATION."
    )
)
async def receive_inbound_email(
    dto: InboundEmailDTO,
    request: Request,
    background_tasks: BackgroundTasks,
    response: Response,
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None),
    x_signature_sha256: Optional[str] = Header(None)
) -> Union[InboundEmailResponse, IdempotencyResponse]:
    """
    Controlador central de ingesta desacoplada de correos.
    - Valida clave interna Bearer / HMAC si está configurada en el entorno.
    - Retorna HTTP 200 OK con 'Event already processed' si el message_id ya fue recibido.
    - Retorna HTTP 202 Accepted si el correo es nuevo y se encoló con éxito.
    """
    # 0. Verificación de Autenticación Interna (Bearer / HMAC)
    raw_body = await request.body()
    await verify_inbound_auth(
        authorization=authorization,
        x_api_key=x_api_key,
        x_signature_sha256=x_signature_sha256,
        raw_body=raw_body
    )

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
