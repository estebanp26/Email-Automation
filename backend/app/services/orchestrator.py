import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Union

from ..config import settings
from ..schemas.email import RawEmailInput, NormalizedEmail
from ..schemas.coder import CoderIdentificationResult
from ..schemas.policy import PolicyEvaluationInput, PolicyEvaluationResult
from ..schemas.justification import JustificationRecord, PipelineExecutionResult

from .ingestion import email_normalizer
from .coder_resolver import coder_resolver
from .hse_engine import hse_engine


class JustificationOrchestrator:
    """
    Orquestador Asíncrono del Pipeline de Justificaciones (BE-03).
    Coordina secuencial y asíncronamente:
    1. Ingesta y normalización (BE-01)
    2. Identificación del Coder en cascada (BE-02)
    3. Validación y clasificación de evidencias
    4. Evaluación determinista de políticas y umbrales HSE (BE-05)
    5. Persistencia y auditoría del registro
    """

    def __init__(self):
        self._justifications_db: Dict[str, JustificationRecord] = {}
        self._seed_sample_records()

    def _seed_sample_records(self):
        """Inicializa registros base para pruebas del dashboard y portal."""
        sample_id = "just-c6357532-2555-4a40-a4ff-bd148a8036b2"
        self._justifications_db[sample_id] = JustificationRecord(
            id=sample_id,
            coder_id="coder-1000000001",
            coder_full_name="Jose Luis Acevedo Vargas",
            coder_cedula="1000000001",
            coder_route="Node.js Backend",
            sender_email="jose.acevedo@riwi.io",
            sender_name="Jose Luis Acevedo",
            subject="Justificante Incapacidad Médica - Jose Acevedo",
            cleaned_body="Buenos días Team Leader, adjunto incapacidad EPS Sura por gastroenteritis del 2026-09-28 al 2026-09-29.",
            excuse_type="incapacidad_medica",
            start_date="2026-09-28",
            end_date="2026-09-29",
            days_count=2,
            status="APPROVED",
            decision="POSIBLEMENTE_VALIDO",
            ai_confidence=0.96,
            ai_reasoning="Incapacidad médica formal verificada con soporte oficial EPS Sura.",
            policy_rule_triggered="REGLA_GENERAL",
            is_sensitive=False,
            escalate_to_hse=False,
            current_threshold="NINGUNO",
            threshold_level=0,
            has_formacion_cc=True,
            attachments_count=1,
            resolution_mode="AUTOMATIC_AI",
            has_human_intervention=False,
            created_at=datetime.now(timezone.utc)
        )

    def process_pipeline(self, email_input: Union[RawEmailInput, NormalizedEmail]) -> PipelineExecutionResult:
        """
        Ejecuta el pipeline completo de evaluación y persistencia.
        """
        start_time = time.time()
        pipeline_id = f"pipe-{uuid.uuid4()}"
        notes: List[str] = []

        # 1. Ingesta y Normalización
        if isinstance(email_input, RawEmailInput):
            norm_email = email_normalizer.normalize(email_input)
            notes.append("Correo normalizado a partir de RawEmailInput.")
        else:
            norm_email = email_input
            notes.append("Correo normalizado recibido directamente.")

        # 2. Identificación del Coder en Cascada
        coder_res = coder_resolver.resolve_from_normalized_email(norm_email)
        notes.append(f"Identificación de Coder: {coder_res.identification_status} vía {coder_res.matched_by}.")

        # Si el Coder no se encuentra en el catálogo
        if coder_res.identification_status == "CODER_NOT_FOUND":
            rec_id = f"just-{uuid.uuid4()}"
            record = JustificationRecord(
                id=rec_id,
                coder_id=None,
                coder_full_name=norm_email.sender_name or "Coder No Identificado",
                coder_cedula="SIN_CEDULA",
                coder_route="No Asignada",
                sender_email=norm_email.sender_email,
                sender_name=norm_email.sender_name,
                subject=norm_email.clean_subject,
                cleaned_body=norm_email.cleaned_body,
                excuse_type=norm_email.preliminary_extraction.suspected_motive or "no_identificado",
                start_date=norm_email.preliminary_extraction.detected_start_date or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                end_date=norm_email.preliminary_extraction.detected_end_date or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                days_count=1,
                status="CODER_NOT_FOUND",
                decision="REVISION_MANUAL",
                ai_confidence=0.0,
                ai_reasoning="Remitente no encontrado en el catálogo de coders. Requiere verificación de matrícula.",
                policy_rule_triggered="CODER_NO_ENCONTRADO",
                is_sensitive=norm_email.preliminary_extraction.is_sensitive,
                escalate_to_hse=True,
                current_threshold="NINGUNO",
                threshold_level=0,
                has_formacion_cc=norm_email.has_formacion_cc,
                attachments_count=len(norm_email.attachments),
                resolution_mode="AUTOMATIC_AI",
                has_human_intervention=False,
                created_at=datetime.now(timezone.utc)
            )
            self._justifications_db[record.id] = record
            elapsed_ms = (time.time() - start_time) * 1000

            return PipelineExecutionResult(
                pipeline_id=pipeline_id,
                execution_status="COMPLETED",
                justification=record,
                execution_time_ms=round(elapsed_ms, 2),
                notes=notes + ["Solicitud pausada: esperando datos de matrícula del coder."]
            )

        # Coder identificado
        coder = coder_res.coder
        start_d_str = norm_email.preliminary_extraction.detected_start_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        end_d_str = norm_email.preliminary_extraction.detected_end_date or start_d_str
        excuse_motive = norm_email.preliminary_extraction.suspected_motive or "falta_injustificada"

        # 3. Validación de Soportes y Archivos
        has_att = len(norm_email.attachments) > 0
        is_eps_official = False
        if has_att:
            for att in norm_email.attachments:
                fname_lower = att.filename.lower()
                if any(k in fname_lower for k in ["eps", "sura", "sanitas", "incapacidad", "medica", "salud"]):
                    is_eps_official = True
                    break
            # Si no tiene palabra clave en el nombre pero es PDF en un motivo de incapacidad, asumimos posible EPS
            if not is_eps_official and excuse_motive == "incapacidad_medica" and norm_email.attachments[0].mime_type == "application/pdf":
                is_eps_official = True

        # 4. Evaluación Determinista de Políticas HSE (BE-05)
        policy_input = PolicyEvaluationInput(
            coder_id=coder.id,
            excuse_type=excuse_motive,
            start_date=start_d_str,
            end_date=end_d_str,
            report_date=norm_email.received_at.strftime("%Y-%m-%d"),
            has_attachment=has_att,
            attachment_is_eps_official=is_eps_official,
            is_sensitive=norm_email.preliminary_extraction.is_sensitive
        )
        policy_res = hse_engine.evaluate_excuse(policy_input)
        notes.append(f"Evaluación de políticas: {policy_res.decision} (Regla: {policy_res.policy_rule_triggered}).")

        # 5. Cálculo de Umbrales Progresivos (Slide 6 y 7 PPTX)
        threshold_info = hse_engine.calculate_thresholds(coder.id, unjustified_week=0, unjustified_month=0)

        # 6. Veredicto Final y Estado del Ciclo de Vida
        if policy_res.is_sensitive:
            final_status = "REVISION_MANUAL"
        elif policy_res.decision == "POSIBLEMENTE_VALIDO":
            final_status = "APPROVED"
        elif policy_res.decision == "POSIBLEMENTE_INVALIDO":
            final_status = "DISAPPROVED"
        else:
            final_status = "REVISION_MANUAL"

        rec_id = f"just-{uuid.uuid4()}"
        record = JustificationRecord(
            id=rec_id,
            coder_id=coder.id,
            coder_full_name=coder.full_name,
            coder_cedula=coder.cedula,
            coder_route=coder.route or norm_email.preliminary_extraction.detected_clan or "TypeScript Fullstack",
            sender_email=norm_email.sender_email,
            sender_name=norm_email.sender_name,
            subject=norm_email.clean_subject,
            cleaned_body=norm_email.cleaned_body,
            excuse_type=excuse_motive,
            start_date=start_d_str,
            end_date=end_d_str,
            days_count=policy_res.days_calculated,
            status=final_status,
            decision=policy_res.decision,
            ai_confidence=policy_res.confidence,
            ai_reasoning=policy_res.recommendation_summary,
            policy_rule_triggered=policy_res.policy_rule_triggered,
            is_sensitive=policy_res.is_sensitive,
            escalate_to_hse=policy_res.escalate_to_hse,
            current_threshold=threshold_info.current_threshold,
            threshold_level=threshold_info.threshold_level,
            has_formacion_cc=norm_email.has_formacion_cc,
            attachments_count=len(norm_email.attachments),
            resolution_mode="AUTOMATIC_AI",
            has_human_intervention=False,
            created_at=datetime.now(timezone.utc)
        )

        self._justifications_db[record.id] = record
        elapsed_ms = (time.time() - start_time) * 1000

        return PipelineExecutionResult(
            pipeline_id=pipeline_id,
            execution_status="COMPLETED",
            justification=record,
            execution_time_ms=round(elapsed_ms, 2),
            notes=notes
        )

    def list_records(self, status: Optional[str] = None, clan: Optional[str] = None) -> List[JustificationRecord]:
        """Consulta registros de justificaciones con filtros."""
        records = list(self._justifications_db.values())
        if status:
            records = [r for r in records if r.status.upper() == status.upper()]
        if clan:
            records = [r for r in records if clan.lower() in r.coder_route.lower()]
        return sorted(records, key=lambda x: x.created_at, reverse=True)

    def get_record_by_id(self, justification_id: str) -> Optional[JustificationRecord]:
        """Obtiene un registro por su ID único."""
        return self._justifications_db.get(justification_id)


orchestrator = JustificationOrchestrator()
