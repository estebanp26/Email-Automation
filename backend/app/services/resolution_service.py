from datetime import datetime, timezone
from typing import Dict, List, Optional

from ..schemas.resolution import (
    ManualResolutionInput,
    ReconsiderationInput,
    ResolutionAuditEntry,
    ResolutionResponse,
)
from ..schemas.notification import NotificationDispatchInput
from .orchestrator import orchestrator
from .notification import notification_service


class ResolutionService:
    """
    Servicio de Resolución Manual y Reconsideración por HSE (BE-06).
    Permite al Team Leader o Analista HSE validar, rectificar, aprobar, rechazar
    o solicitar soportes adicionales conforme al Slide 4 y 5 del PPTX:
    'Avisar no garantiza que la falta quede justificada. El TL Desarrollo valida según la información suministrada.'
    'El TL Desarrollo contestará el correo con la respuesta de si se requiere mayor información o se considera justificada.'
    """

    def __init__(self):
        self._audit_history: Dict[str, List[ResolutionAuditEntry]] = {}

    def resolve_justification(
        self,
        justification_id: str,
        payload: ManualResolutionInput
    ) -> ResolutionResponse:
        record = orchestrator.get_record_by_id(justification_id)
        if not record:
            raise ValueError(f"No se encontró la justificación con ID '{justification_id}'.")

        action_norm = payload.action.upper().strip()
        template_type = "APPROVED"

        if action_norm in ["APPROVE", "APPROVED"]:
            record.status = "APPROVED"
            record.decision = "JUSTIFICADA_POR_TL"
            template_type = "APPROVED"
        elif action_norm in ["DISAPPROVE", "DISAPPROVED", "REJECT"]:
            record.status = "DISAPPROVED"
            record.decision = "INJUSTIFICADA_POR_TL"
            template_type = "DISAPPROVED"
        elif action_norm in ["REQUEST_MORE_INFO", "REQUEST_CORRECTION"]:
            record.status = "REVISION_MANUAL"
            record.decision = "SOPORTE_PENDIENTE"
            template_type = "REQUEST_MORE_INFO"
        else:
            record.status = "REVISION_MANUAL"
            record.decision = action_norm
            template_type = "REQUEST_MORE_INFO"

        # Aplicar modificaciones opcionales de TL
        if payload.override_excuse_type:
            record.excuse_type = payload.override_excuse_type
        if payload.override_start_date:
            record.start_date = payload.override_start_date
        if payload.override_end_date:
            record.end_date = payload.override_end_date

        record.resolution_mode = "MANUAL_HSE"
        record.has_human_intervention = True

        # Registrar entrada de auditoría
        audit_entry = ResolutionAuditEntry(
            action=action_norm,
            reviewer_name=payload.reviewer_name,
            reviewer_role=payload.reviewer_role,
            notes=payload.notes,
            timestamp=datetime.now(timezone.utc)
        )
        if justification_id not in self._audit_history:
            self._audit_history[justification_id] = []
        self._audit_history[justification_id].append(audit_entry)

        # Despachar notificación automática por correo al coder si está habilitado (Slide 5 PPTX)
        notif_dispatched = False
        notif_details = None

        if payload.dispatch_notification and record.sender_email:
            notif_input = NotificationDispatchInput(
                recipient_email=record.sender_email,
                recipient_name=record.coder_full_name,
                template_type=template_type,
                justification_id=record.id,
                start_date=record.start_date,
                end_date=record.end_date,
                excuse_type=record.excuse_type,
                notes=payload.notes,
                original_subject=record.subject,
                in_reply_to_message_id=record.id
            )
            disp_res = notification_service.dispatch(notif_input)
            notif_dispatched = True
            notif_details = {
                "dispatch_id": disp_res.dispatch_id,
                "template": template_type,
                "recipient": disp_res.recipient,
                "subject": disp_res.subject
            }

        return ResolutionResponse(
            justification_id=record.id,
            status=record.status,
            resolution_mode=record.resolution_mode,
            has_human_intervention=record.has_human_intervention,
            hse_decision=action_norm,
            hse_notes=payload.notes,
            hse_reviewer_name=payload.reviewer_name,
            resolved_at=audit_entry.timestamp,
            notification_dispatched=notif_dispatched,
            notification_details=notif_details,
            audit_trail=self._audit_history[justification_id]
        )

    def reconsider_justification(
        self,
        justification_id: str,
        payload: ReconsiderationInput
    ) -> ResolutionResponse:
        """
        Permite al equipo HSE o Team Leader reabrir o rectificar una decisión anterior.
        """
        record = orchestrator.get_record_by_id(justification_id)
        if not record:
            raise ValueError(f"No se encontró la justificación con ID '{justification_id}'.")

        new_act = payload.new_action.upper().strip()
        record.status = "APPROVED" if new_act == "APPROVE" else "DISAPPROVED"
        record.decision = f"RECONSIDERADO_{new_act}"
        record.resolution_mode = "MANUAL_HSE"
        record.has_human_intervention = True

        note_text = f"[RECONSIDERACIÓN]: {payload.reconsideration_reason}"
        if payload.new_attachment_name:
            note_text += f" (Nuevo soporte presentado: {payload.new_attachment_name})"

        audit_entry = ResolutionAuditEntry(
            action=f"RECONSIDERATION_{new_act}",
            reviewer_name=payload.reviewer_name,
            reviewer_role="HSE_COORDINATION",
            notes=note_text,
            timestamp=datetime.now(timezone.utc)
        )
        if justification_id not in self._audit_history:
            self._audit_history[justification_id] = []
        self._audit_history[justification_id].append(audit_entry)

        # Despacho de notificación de actualización
        notif_input = NotificationDispatchInput(
            recipient_email=record.sender_email,
            recipient_name=record.coder_full_name,
            template_type=record.status,
            justification_id=record.id,
            start_date=record.start_date,
            end_date=record.end_date,
            excuse_type=record.excuse_type,
            notes=note_text,
            original_subject=f"Reconsideración - {record.subject}"
        )
        disp_res = notification_service.dispatch(notif_input)

        return ResolutionResponse(
            justification_id=record.id,
            status=record.status,
            resolution_mode=record.resolution_mode,
            has_human_intervention=True,
            hse_decision=new_act,
            hse_notes=note_text,
            hse_reviewer_name=payload.reviewer_name,
            resolved_at=audit_entry.timestamp,
            notification_dispatched=True,
            notification_details={
                "dispatch_id": disp_res.dispatch_id,
                "template": record.status,
                "recipient": disp_res.recipient
            },
            audit_trail=self._audit_history[justification_id]
        )

    def get_audit_trail(self, justification_id: str) -> List[ResolutionAuditEntry]:
        return self._audit_history.get(justification_id, [])


resolution_service = ResolutionService()
