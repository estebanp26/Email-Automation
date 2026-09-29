from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any, List

from ...schemas.email import (
    RawEmailInput,
    NormalizedEmail,
    EmailIngestResponse,
)
from ...services.ingestion import email_normalizer

router = APIRouter(prefix="/emails", tags=["Emails & Ingesta (BE-01)"])


@router.get("/health", summary="Estado del módulo de ingesta")
async def email_service_health():
    """Retorna el estado operativo del servicio nativo de ingesta de correos."""
    return {
        "status": "healthy",
        "service": "BE-01 Email Ingestion & Normalization",
        "supported_providers": ["OUTLOOK", "GMAIL", "SIMULATION", "PORTAL"],
        "max_attachment_mb": 15,
        "official_cc": "formacion.barranquilla@riwi.io"
    }


@router.post(
    "/ingest",
    response_model=EmailIngestResponse,
    status_code=status.HTTP_200_OK,
    summary="Ingesta y normalización nativa de correos (BE-01)"
)
async def ingest_email(payload: RawEmailInput):
    """
    Punto de entrada nativo para correos entrantes de Outlook Graph, Gmail Pub/Sub o Conectores.
    
    Aplica el pipeline de normalización:
    1. Limpieza y desduplicación de remitentes y asuntos (RFC 822).
    2. Stripping de firmas, HTML y citas de hilos anteriores.
    3. Validación y hash SHA-256 de adjuntos médicos y soportes.
    4. Comprobación de copia obligatoria a `formacion.barranquilla@riwi.io` (Slide 5 PPTX).
    5. Extracción preliminar de cédula, fechas, clan y motivo tipificado.
    """
    try:
        response = email_normalizer.ingest(payload)
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Error en el proceso de normalización del correo: {str(e)}"
        )


@router.post(
    "/simulate",
    response_model=EmailIngestResponse,
    status_code=status.HTTP_200_OK,
    summary="Simulación de correo entrante para pruebas y Frontend"
)
async def simulate_incoming_email(scenario: str = "incapacidad_sura"):
    """
    Genera y procesa un correo simulado con escenarios basados en el PPTX de Asistencias Riwi:
    - `incapacidad_sura`: Incapacidad médica oficial con EPS y copia a formación.
    - `malestar_sin_soporte`: Reporte de malestar físico sin certificado médico.
    - `situacion_sensible`: Caso de salud mental o crisis emocional (Slide 5 PPTX).
    - `injustificada_sin_cc`: Correo sin cédula ni copia al correo institucional.
    """
    scenarios: Dict[str, RawEmailInput] = {
        "incapacidad_sura": RawEmailInput(
            source_provider="OUTLOOK",
            message_id="sim-msg-001",
            conversation_id="sim-conv-001",
            sender_email="carlos.perez@riwi.io",
            sender_name="Carlos Andrés Pérez",
            recipient_email="teamleader@riwi.io",
            cc_emails=["formacion.barranquilla@riwi.io"],
            subject="Re: Justificación Inasistencia - Carlos Pérez - Clan Turing",
            body="""
            Buenos días Team Leader,
            
            Por medio del presente correo me permito informar que no pude asistir el día 2026-09-28 debido a una gastroenteritis aguda.
            Mi documento de identidad es CC 1045892341, pertenezco al Clan Turing en la jornada de la mañana.
            Adjunto la incapacidad médica oficial emitida por EPS Sura por 2 días.
            Mi fecha estimada de reintegro es el 2026-09-30.
            
            Quedo atento a su respuesta.
            
            Saludos cordiales,
            Carlos Pérez
            
            El lun, 21 sept 2026 a las 8:00, Team Leader <tl@riwi.io> escribió:
            > Recordatorio semanal de asistencia...
            """,
            attachments=[{
                "filename": "incapacidad_sura_20260928.pdf",
                "mime_type": "application/pdf",
                "data_base64": "JVBERi0xLjQKJcTl8uXr...Cg==",
                "size_bytes": 1024
            }]
        ),
        "malestar_sin_soporte": RawEmailInput(
            source_provider="GMAIL",
            message_id="sim-msg-002",
            sender_email="laura.gomez@riwi.io",
            sender_name="Laura Gómez",
            recipient_email="tl@riwi.io",
            cc_emails=["formacion.barranquilla@riwi.io"],
            subject="Aviso inasistencia - Laura Gómez",
            body="""
            Hola TL, hoy 2026-09-29 amanecí con mucho malestar general y dolor de cabeza fuerte.
            No tengo incapacidad médica de EPS porque es de 1 día y estoy tomando medicamentos en casa.
            Mi cédula es 1082938475 del clan Lovelace mañana.
            """,
            attachments=[]
        ),
        "situacion_sensible": RawEmailInput(
            source_provider="OUTLOOK",
            message_id="sim-msg-003",
            sender_email="andres.mendoza@riwi.io",
            sender_name="Andrés Mendoza",
            recipient_email="tl@riwi.io",
            cc_emails=["formacion.barranquilla@riwi.io"],
            subject="Situación urgente personal - Andrés Mendoza",
            body="""
            Estimado TL, estoy atravesando por una crisis de pánico severa y colapso emocional debido a una situación de salud mental delicada en mi entorno familiar.
            Mi documento es 1140889922 del clan Gosling.
            Agradezco la mayor reserva y confidencialidad posible.
            """
        ),
        "injustificada_sin_cc": RawEmailInput(
            source_provider="SIMULATION",
            message_id="sim-msg-004",
            sender_email="usuario.externo@gmail.com",
            subject="No pude ir a clase",
            body="Ayer no fui porque me quedé sin transporte y no alcancé a llegar a tiempo."
        )
    }

    selected = scenarios.get(scenario, scenarios["incapacidad_sura"])
    return email_normalizer.ingest(selected)
