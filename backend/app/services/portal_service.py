from datetime import datetime, timezone
from typing import Dict, List, Optional

from ..schemas.email import RawEmailInput, RawAttachmentInput
from ..schemas.coder_portal import (
    CoderExcuseSubmission,
    CoderAttendanceSummary,
    DashboardGlobalStats,
)
from ..schemas.justification import JustificationRecord, PipelineExecutionResult

from .orchestrator import orchestrator
from .coder_resolver import coder_resolver
from .hse_engine import hse_engine


class CoderPortalService:
    """
    Servicio de Gestión de Excusas del Coder y Portal Moodle (BE-07).
    Permite radicar novedades desde la interfaz web, consultar el historial individual
    y monitorear el semáforo de permanencia y umbrales (Slide 6 y 7 PPTX).
    """

    def submit_excuse(self, submission: CoderExcuseSubmission) -> PipelineExecutionResult:
        """
        Recibe la radicación web y la canaliza por el pipeline oficial.
        """
        attachments = []
        if submission.attachment_data_base64:
            attachments.append(
                RawAttachmentInput(
                    filename=submission.attachment_filename or "soporte_radicado.pdf",
                    mime_type=submission.attachment_mime_type or "application/pdf",
                    data_base64=submission.attachment_data_base64
                )
            )

        structured_body = f"""
Justificación radicada a través de Campus / Portal Coder Riwi:

• Coder: {submission.coder_name}
• Documento de Identidad: CC {submission.document_id}
• Clan / Ruta: {submission.clan}
• Jornada: {submission.shift}
• Tipo de Novedad: {submission.category}
• Fechas de Ausencia: {submission.start_date} al {submission.end_date}

• Motivo Declarado:
{submission.reason}
        """.strip()

        raw_email = RawEmailInput(
            source_provider="PORTAL",
            sender_email=submission.coder_email.strip().lower(),
            sender_name=submission.coder_name.strip(),
            recipient_email="formacion.barranquilla@riwi.io",
            cc_emails=["formacion.barranquilla@riwi.io"],
            subject=f"[Portal Coder - {submission.category}] {submission.coder_name} - {submission.clan}",
            body=structured_body,
            attachments=attachments
        )

        return orchestrator.process_pipeline(raw_email)

    def get_coder_excuses(
        self,
        coder_email: Optional[str] = None,
        coder_cedula: Optional[str] = None
    ) -> List[JustificationRecord]:
        """Consulta el historial de justificaciones de un estudiante."""
        all_records = list(orchestrator._justifications_db.values())
        filtered = []

        for r in all_records:
            match = False
            if coder_email and r.sender_email.lower() == coder_email.strip().lower():
                match = True
            if coder_cedula and r.coder_cedula.strip() == coder_cedula.strip():
                match = True
            if match or (not coder_email and not coder_cedula):
                filtered.append(r)

        return sorted(filtered, key=lambda x: x.created_at, reverse=True)

    def get_attendance_summary(self, coder_identifier: str) -> CoderAttendanceSummary:
        """
        Calcula el resumen de asistencia y el nivel de umbral del coder (Slide 6 y 7 PPTX).
        """
        # Identificar al coder por cédula o correo
        clean_id = coder_identifier.strip().lower()
        coder = coder_resolver._coders_by_email.get(clean_id) or coder_resolver._coders_by_cedula.get(clean_id)

        coder_name = coder.full_name if coder else "Coder Estudiante"
        coder_cedula = coder.cedula if coder else coder_identifier
        coder_route = coder.route if coder else "TypeScript Fullstack"
        coder_id = coder.id if coder else f"coder-{coder_identifier}"

        # Obtener justificaciones del coder
        excuses = self.get_coder_excuses(
            coder_email=coder.email if coder else (clean_id if "@" in clean_id else None),
            coder_cedula=coder.cedula if coder else (clean_id if "@" not in clean_id else None)
        )

        total = len(excuses)
        approved = sum(1 for e in excuses if e.status == "APPROVED")
        disapproved = sum(1 for e in excuses if e.status == "DISAPPROVED")
        pending = sum(1 for e in excuses if e.status in ["REVISION_MANUAL", "PENDIENTE_DECISION_TL", "CODER_NOT_FOUND"])

        # Solo las inasistencias injustificadas suman a los umbrales (Slide 6 PPTX)
        threshold_info = hse_engine.calculate_thresholds(
            coder_id=coder_id,
            unjustified_week=disapproved,
            unjustified_month=disapproved
        )

        return CoderAttendanceSummary(
            coder_id=coder_id,
            coder_name=coder_name,
            coder_cedula=coder_cedula,
            coder_route=coder_route,
            total_requests=total,
            approved_requests=approved,
            disapproved_requests=disapproved,
            pending_requests=pending,
            unjustified_absences_week=disapproved,
            unjustified_absences_month=disapproved,
            current_threshold=threshold_info.current_threshold,
            threshold_level=threshold_info.threshold_level,
            responsible_area=threshold_info.responsible_area,
            warning_alert=threshold_info.warning_alert
        )

    def get_dashboard_global_stats(self) -> DashboardGlobalStats:
        """Calcula las métricas operativas globales para el panel de Team Leaders y HSE."""
        all_records = list(orchestrator._justifications_db.values())
        total = len(all_records)
        approved = sum(1 for r in all_records if r.status == "APPROVED")
        disapproved = sum(1 for r in all_records if r.status == "DISAPPROVED")
        pending = sum(1 for r in all_records if r.status in ["REVISION_MANUAL", "PENDIENTE_DECISION_TL", "CODER_NOT_FOUND"])
        alerts = sum(1 for r in all_records if r.threshold_level > 0 or r.escalate_to_hse)
        sensitive = sum(1 for r in all_records if r.is_sensitive)

        return DashboardGlobalStats(
            total_requests=total,
            approved_count=approved,
            disapproved_count=disapproved,
            pending_count=pending,
            threshold_alerts_count=alerts,
            sensitive_cases_count=sensitive
        )


portal_service = CoderPortalService()
