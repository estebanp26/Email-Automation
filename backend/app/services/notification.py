import html
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from ..config import settings
from ..schemas.notification import (
    NotificationDispatchInput,
    NotificationDispatchResult,
    NotificationPreviewRequest,
)


class NotificationService:
    """
    Servicio Nativo de Notificaciones y Plantillas de Correo (BE-04).
    Genera respuestas HTML en el mismo hilo de conversación conforme a las
    políticas de comunicación de la Team Leader de Riwi (Slide 5, 6 y 7 del PPTX).
    """

    def __init__(self):
        self._outbox: List[NotificationDispatchResult] = []

    def _generate_html_template(
        self,
        template_type: str,
        name: str,
        dates: str,
        excuse_type: str,
        notes: Optional[str] = None,
        threshold_level: int = 0
    ) -> Tuple[str, str]:
        """
        Construye el asunto y cuerpo HTML estilizado según el tipo de plantilla.
        """
        clean_name = html.escape(name)
        clean_dates = html.escape(dates)
        clean_motive = html.escape(excuse_type.replace("_", " ").title())
        clean_notes = html.escape(notes or "")

        header_badge = "SISTEMA DE ASISTENCIAS & PERMANENCIA RIWI"
        footer = f"""
            <div style="margin-top: 30px; padding-top: 15px; border-top: 1px solid #E2E8F0; font-size: 12px; color: #64748B;">
                <p>Este es un mensaje institucional generado automáticamente por el Sistema de Justificaciones HSE & Team Leaders de Riwi Barranquilla.</p>
                <p>Copia oficial: <strong>{settings.FORMACION_EMAIL_OFFICIAL}</strong></p>
            </div>
        """

        if template_type.upper() == "APPROVED":
            subject = f"✅ Justificación Aprobada — {clean_motive} [{clean_dates}]"
            content = f"""
            <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 25px; border: 1px solid #E2E8F0; border-radius: 12px; background-color: #FFFFFF;">
                <div style="background-color: #10B981; color: white; padding: 6px 12px; border-radius: 6px; font-weight: bold; font-size: 12px; display: inline-block; margin-bottom: 15px;">
                    ESTADO: JUSTIFICADA
                </div>
                <h2 style="color: #0F172A; margin-top: 0;">Estimado(a) {clean_name},</h2>
                <p style="color: #334155; font-size: 15px; line-height: 1.6;">
                    Te informamos que tu reporte de inasistencia por motivo de <strong>{clean_motive}</strong> correspondiente al periodo <strong>{clean_dates}</strong> ha sido evaluado y <strong>convalidado exitosamente</strong>.
                </p>
                <div style="background-color: #F0FDF4; border-left: 4px solid #10B981; padding: 12px 16px; margin: 20px 0; border-radius: 4px;">
                    <p style="margin: 0; color: #166534; font-size: 14px;">
                        📌 <strong>Regulación de Permanencia (Slide 6 PPTX):</strong> Al ser una falta justificada con soporte válido, <strong>no suma</strong> para los umbrales de inasistencias ni afecta tu permanencia en el programa.
                    </p>
                </div>
                {f'<p style="color: #475569; font-size: 14px;"><strong>Observaciones del evaluador:</strong> {clean_notes}</p>' if notes else ''}
                <p style="color: #334155; font-size: 14px;">Recuerda ponerte al día con las actividades y entregables técnicos correspondientes a las jornadas ausentes.</p>
                {footer}
            </div>
            """

        elif template_type.upper() == "DISAPPROVED":
            subject = f"❌ Inasistencia No Justificada — {clean_motive} [{clean_dates}]"
            content = f"""
            <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 25px; border: 1px solid #E2E8F0; border-radius: 12px; background-color: #FFFFFF;">
                <div style="background-color: #EF4444; color: white; padding: 6px 12px; border-radius: 6px; font-weight: bold; font-size: 12px; display: inline-block; margin-bottom: 15px;">
                    ESTADO: INASISTENCIA INJUSTIFICADA
                </div>
                <h2 style="color: #0F172A; margin-top: 0;">Estimado(a) {clean_name},</h2>
                <p style="color: #334155; font-size: 15px; line-height: 1.6;">
                    Te informamos que tu reporte de inasistencia del <strong>{clean_dates}</strong> <strong>no ha sido convalidado</strong> como falta justificada.
                </p>
                <div style="background-color: #FEF2F2; border-left: 4px solid #EF4444; padding: 12px 16px; margin: 20px 0; border-radius: 4px;">
                    <p style="margin: 0; color: #991B1B; font-size: 14px;">
                        ⚠️ <strong>Motivo de la decisión:</strong> {clean_notes or 'Falta de soporte oficial verificable o reporte extemporáneo conforme al Slide 3 del reglamento de Riwi.'}
                    </p>
                </div>
                <p style="color: #334155; font-size: 14px; line-height: 1.5;">
                    Ten presente que las inasistencias injustificadas se registran en Moodle y activan el <strong>protocolo de umbrales progresivos de permanencia</strong> (1-2 alerta temprana, 3-4 seguimiento con HSE, 10+ comité de coordinación).
                </p>
                {footer}
            </div>
            """

        elif template_type.upper() == "REQUEST_MORE_INFO":
            subject = f"⚠️ Requerimiento de Soporte Oficial — Inasistencia [{clean_dates}]"
            content = f"""
            <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 25px; border: 1px solid #E2E8F0; border-radius: 12px; background-color: #FFFFFF;">
                <div style="background-color: #F59E0B; color: white; padding: 6px 12px; border-radius: 6px; font-weight: bold; font-size: 12px; display: inline-block; margin-bottom: 15px;">
                    ACCIÓN REQUERIDA: SOPORTE PENDIENTE
                </div>
                <h2 style="color: #0F172A; margin-top: 0;">Estimado(a) {clean_name},</h2>
                <p style="color: #334155; font-size: 15px; line-height: 1.6;">
                    Hemos recibido tu reporte de inasistencia por <strong>{clean_motive}</strong> ({clean_dates}). Para poder evaluar y convalidar la ausencia, <strong>se requiere que aportes el soporte documental correspondiente</strong>.
                </p>
                <div style="background-color: #FFFBEB; border-left: 4px solid #F59E0B; padding: 12px 16px; margin: 20px 0; border-radius: 4px;">
                    <p style="margin: 0; color: #92400E; font-size: 14px;">
                        🕒 <strong>Plazo reglamentario (Slide 3 PPTX):</strong> Cuentas con un plazo máximo de <strong>tres (3) días hábiles posteriores</strong> a la inasistencia para adjuntar el certificado en formato oficial de tu EPS/IPS o soporte legal.
                    </p>
                </div>
                {f'<p style="color: #475569; font-size: 14px;"><strong>Detalle solicitado:</strong> {clean_notes}</p>' if notes else ''}
                <p style="color: #334155; font-size: 14px;">Por favor responde a este mismo correo adjuntando el documento en formato PDF o imagen legible.</p>
                {footer}
            </div>
            """

        elif template_type.upper() == "CODER_NOT_FOUND":
            subject = "ℹ️ Solicitud de Información de Matrícula — Riwi Barranquilla"
            content = f"""
            <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 25px; border: 1px solid #E2E8F0; border-radius: 12px; background-color: #FFFFFF;">
                <div style="background-color: #6366F1; color: white; padding: 6px 12px; border-radius: 6px; font-weight: bold; font-size: 12px; display: inline-block; margin-bottom: 15px;">
                    CODER NO IDENTIFICADO
                </div>
                <h2 style="color: #0F172A; margin-top: 0;">Estimado remitente,</h2>
                <p style="color: #334155; font-size: 15px; line-height: 1.6;">
                    Hemos recibido tu correo sobre una justificación de inasistencia; sin embargo, tu dirección electrónica <strong>no coincide con ningún estudiante registrado</strong> en la base de datos de Riwi.
                </p>
                <div style="background-color: #EEF2FF; border-left: 4px solid #6366F1; padding: 12px 16px; margin: 20px 0; border-radius: 4px;">
                    <p style="margin: 0; color: #3730A3; font-size: 14px;">
                        📝 <strong>Información mínima requerida (Slide 4 PPTX):</strong>
                        <br>• Nombre completo y número de cédula (ID)
                        <br>• Clan, jornada y cohorte
                        <br>• Fechas de la inasistencia y motivo
                        <br>• Soporte documental y fecha de reintegro
                    </p>
                </div>
                <p style="color: #334155; font-size: 14px;">Por favor responde a este correo suministrando tu número de documento y Clan para poder tramitar la solicitud.</p>
                {footer}
            </div>
            """

        elif template_type.upper() == "HSE_ALERT":
            subject = f"🚨 Alerta de Permanencia HSE — Umbral {threshold_level} Activado [{clean_name}]"
            content = f"""
            <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 25px; border: 1px solid #E2E8F0; border-radius: 12px; background-color: #FFFFFF;">
                <div style="background-color: #8B5CF6; color: white; padding: 6px 12px; border-radius: 6px; font-weight: bold; font-size: 12px; display: inline-block; margin-bottom: 15px;">
                    NOTIFICACIÓN INTERNA EQUIPO HSE
                </div>
                <h2 style="color: #0F172A; margin-top: 0;">Alerta de Seguimiento y Permanencia</h2>
                <p style="color: #334155; font-size: 15px; line-height: 1.6;">
                    Se ha detectado un evento que requiere la intervención del equipo de <strong>HSE / Acompañamiento Psicosocial</strong>:
                </p>
                <ul style="color: #334155; font-size: 14px; line-height: 1.6;">
                    <li><strong>Estudiante:</strong> {clean_name}</li>
                    <li><strong>Novedad / Motivo:</strong> {clean_motive}</li>
                    <li><strong>Periodo:</strong> {clean_dates}</li>
                    <li><strong>Umbral de Riesgo:</strong> Nivel {threshold_level}</li>
                </ul>
                <div style="background-color: #F5F3FF; border-left: 4px solid #8B5CF6; padding: 12px 16px; margin: 20px 0; border-radius: 4px;">
                    <p style="margin: 0; color: #5B21B6; font-size: 14px;">
                        📋 <strong>Protocolo Exigido:</strong> {clean_notes or 'Contacto formal con el coder y documentación de compromisos según los lineamientos de Team Leader Riwi.'}
                    </p>
                </div>
                {footer}
            </div>
            """
        else:
            subject = f"Notificación de Asistencia Riwi — {clean_name}"
            content = f"<p>Estimado(a) {clean_name}, hemos recibido tu comunicación sobre el periodo {clean_dates}.</p>{footer}"

        return subject, content

    def dispatch(self, payload: NotificationDispatchInput) -> NotificationDispatchResult:
        """
        Construye y despacha el correo notificatorio. Soporta formato thread-aware.
        """
        dispatch_id = f"disp-{uuid.uuid4()}"
        dates_str = f"{payload.start_date or ''} al {payload.end_date or ''}".strip(" al") or "Periodo Actual"

        subject, html_body = self._generate_html_template(
            template_type=payload.template_type,
            name=payload.recipient_name,
            dates=dates_str,
            excuse_type=payload.excuse_type or "inasistencia",
            notes=payload.notes,
            threshold_level=payload.threshold_level or 0
        )

        # Thread-aware: Si viene asunto original, prefijar con 'Re: '
        if payload.original_subject:
            clean_sub = payload.original_subject
            if not clean_sub.lower().startswith("re:"):
                clean_sub = f"Re: {clean_sub}"
            subject = clean_sub

        result = NotificationDispatchResult(
            dispatch_id=dispatch_id,
            status="SENT",
            recipient=payload.recipient_email,
            subject=subject,
            html_body=html_body,
            in_reply_to=payload.in_reply_to_message_id,
            dispatched_at=datetime.now(timezone.utc)
        )

        self._outbox.append(result)
        return result

    def preview_template(self, req: NotificationPreviewRequest) -> Dict[str, str]:
        """Genera una vista previa del asunto y HTML para revisión previa."""
        dates_str = f"{req.start_date} al {req.end_date}"
        sub, html_content = self._generate_html_template(
            template_type=req.template_type,
            name=req.recipient_name,
            dates=dates_str,
            excuse_type=req.excuse_type,
            notes=req.notes,
            threshold_level=req.threshold_level
        )
        return {"subject": sub, "html_body": html_content}

    def list_outbox(self, limit: int = 50) -> List[NotificationDispatchResult]:
        """Consulta el buzón de salida histórico."""
        return sorted(self._outbox, key=lambda x: x.dispatched_at, reverse=True)[:limit]


notification_service = NotificationService()
