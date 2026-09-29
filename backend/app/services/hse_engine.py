from datetime import date, datetime
from typing import Optional, Tuple

from ..schemas.policy import (
    PolicyEvaluationInput,
    PolicyEvaluationResult,
    AttendanceThresholdSummary,
)

PREVISIBLE_MOTIVES = [
    "cita_medica",
    "jornada_laboral",
    "jornada_estudio",
    "tramite_institucional"
]

MANDATORY_SUPPORT_MOTIVES = [
    "incapacidad_medica",
    "cita_medica",
    "tramite_institucional"
]


class HSEPolicyEngine:
    """
    Motor Determinista de Reglas de Asistencia y Permanencia HSE (BE-05).
    Traduce fielmente a código los lineamientos de la Team Leader de Riwi:
    - Validación de los 10 motivos oficiales de inasistencia.
    - Oportunidad temporal: Previsible vs Imprevisto vs Fuerza Mayor (máx 3 días).
    - Límite de 2 días para malestar sin incapacidad médica.
    - Tratamiento confidencial de situaciones sensibles (salud mental/emocional).
    - Evaluación de los 4 umbrales progresivos (Semanales y Mensuales).
    """

    @classmethod
    def parse_date(cls, date_str: str) -> date:
        try:
            return datetime.strptime(date_str[:10], "%Y-%m-%d").date()
        except Exception:
            return date.today()

    @classmethod
    def calculate_days(cls, start_d: date, end_d: date) -> int:
        if end_d < start_d:
            return 1
        return (end_d - start_d).days + 1

    def evaluate_excuse(self, payload: PolicyEvaluationInput) -> PolicyEvaluationResult:
        start_d = self.parse_date(payload.start_date)
        end_d = self.parse_date(payload.end_date)
        report_d = self.parse_date(payload.report_date) if payload.report_date else date.today()

        days = self.calculate_days(start_d, end_d)
        motive = payload.excuse_type.strip().lower()

        is_timely = True
        timeliness_notes = "Reporte presentado dentro de los plazos reglamentarios."
        support_valid = True
        support_notes = "Soporte documental validado conforme a la política."
        escalate_to_hse = False
        is_sensitive = payload.is_sensitive or (motive == "situacion_emocional_critica")
        decision = "POSIBLEMENTE_VALIDO"
        rule_triggered = "REGLA_GENERAL"
        confidence = 0.90

        # 1. Regla de Sensibilidad y Salud Mental (Slide 5 & 8 PPTX)
        if is_sensitive:
            decision = "REVISION_MANUAL"
            escalate_to_hse = True
            rule_triggered = "CASO_SENSIBLE_HSE"
            confidence = 0.95
            support_notes = "Caso clasificado como confidencial/sensible. Remitir directamente a HSE para acompañamiento humano."

        # 2. Regla de Oportunidad Temporal (Slide 3 PPTX)
        # Previsibles: antes de la jornada
        if motive in PREVISIBLE_MOTIVES:
            if report_d > start_d:
                is_timely = False
                timeliness_notes = f"Inasistencia previsible reportada extemporáneamente ({report_d} posterior al inicio {start_d}). Debió reportarse antes de la jornada."
                decision = "POSIBLEMENTE_INVALIDO"
                rule_triggered = "PREVISIBLE_EXTEMPORANEO"

        # Fuerza mayor / Incapacidades: máximo 3 días posteriores
        elif motive in ["incapacidad_medica", "dificultades_familiares"]:
            delta_days = (report_d - start_d).days
            if delta_days > 3:
                is_timely = False
                timeliness_notes = f"Reporte extemporáneo ({delta_days} días transcurridos). Supera el plazo máximo de tres (3) días hábiles posteriores (Slide 3 PPTX)."
                decision = "POSIBLEMENTE_INVALIDO"
                rule_triggered = "FUERZA_MAYOR_VENCIDA"

        # 3. Regla de Malestar sin Incapacidad (Slide 3 & 8 PPTX: Máximo 2 días)
        if motive == "enfermo_sin_incapacidad":
            if days > 2:
                support_valid = False
                escalate_to_hse = True
                decision = "POSIBLEMENTE_INVALIDO"
                rule_triggered = "MALESTAR_SUPERA_2_DIAS"
                support_notes = f"Malestar sin incapacidad reportado por {days} días. La política de Riwi limita a máximo dos (2) días sin soporte médico formal; periodos mayores exigen incapacidad oficial de EPS o revisión de HSE."

        # 4. Regla de Soportes Exigibles (Slide 3 & 4 PPTX)
        if motive in MANDATORY_SUPPORT_MOTIVES:
            if not payload.has_attachment:
                support_valid = False
                decision = "POSIBLEMENTE_INVALIDO"
                rule_triggered = "FALTA_SOPORTE_OBLIGATORIO"
                support_notes = f"El motivo '{motive}' exige adjuntar soporte documental verificable. No se aportó ningún adjunto."
            elif motive == "incapacidad_medica" and not payload.attachment_is_eps_official:
                decision = "REVISION_MANUAL"
                escalate_to_hse = True
                rule_triggered = "INCAPACIDAD_NO_EPS_OFICIAL"
                support_notes = "Se adjuntó documento, pero no se validó formalmente como Incapacidad Oficial de EPS/IPS (posible fórmula o recibo). Requiere revisión de la Team Leader / HSE."

        # 5. Regla de Falta Injustificada
        if motive == "falta_injustificada":
            decision = "POSIBLEMENTE_INVALIDO"
            support_valid = False
            rule_triggered = "FALTA_INJUSTIFICADA"
            support_notes = "Ausencia sin causa válida o sin reporte oportuno conforme al Slide 2 del PPTX."

        # Resumen de recomendación
        rec_summary = (
            f"Veredicto: {decision}. Motivo: '{motive}' ({days} día(s)). "
            f"Oportunidad: {'Oportuno' if is_timely else 'Extemporáneo'}. "
            f"Soporte: {'Válido' if support_valid else 'Inválido/Incompleto'}. "
            f"Escalamiento HSE: {'SÍ' if escalate_to_hse else 'NO'}."
        )

        return PolicyEvaluationResult(
            decision=decision,
            confidence=confidence,
            days_calculated=days,
            is_timely=is_timely,
            timeliness_notes=timeliness_notes,
            support_valid=support_valid,
            support_notes=support_notes,
            escalate_to_hse=escalate_to_hse,
            is_sensitive=is_sensitive,
            requires_human_review=(decision == "REVISION_MANUAL" or escalate_to_hse),
            policy_rule_triggered=rule_triggered,
            recommendation_summary=rec_summary
        )

    def calculate_thresholds(
        self,
        coder_id: str,
        unjustified_week: int,
        unjustified_month: int
    ) -> AttendanceThresholdSummary:
        """
        Calcula el nivel de umbral de permanencia del coder según inasistencias injustificadas acumuladas (Slides 6 y 7).
        """
        # Umbral 4: 15+ inasistencias / mes -> Proceso de Retiro
        if unjustified_month >= 15:
            return AttendanceThresholdSummary(
                coder_id=coder_id,
                unjustified_absences_week=unjustified_week,
                unjustified_absences_month=unjustified_month,
                current_threshold="UMBRAL_4",
                threshold_level=4,
                responsible_area="COORDINACION_HSE",
                action_required="Proceso de Retiro: Coordinación HSE notifica inicio del proceso formal con reunión de descargos y decisión definitiva.",
                warning_alert="CRÍTICO: Coder en Umbral 4 de Retiro por acumulación >= 15 faltas injustificadas en el mes."
            )

        # Umbral 3: 10–14 inasistencias / mes -> Llamado de Atención / Plan de Mejora
        if unjustified_month >= 10:
            return AttendanceThresholdSummary(
                coder_id=coder_id,
                unjustified_absences_week=unjustified_week,
                unjustified_absences_month=unjustified_month,
                current_threshold="UMBRAL_3",
                threshold_level=3,
                responsible_area="HSE_LIDERA",
                action_required="Llamado de Atención / Plan de Mejora: HSE emite llamado formal escrito + Plan de compromiso de asistencia con seguimiento semanal por Coordinación.",
                warning_alert="ALTO RIESGO: Coder en Umbral 3 (10–14 faltas en el mes). HSE lidera intervención formal."
            )

        # Umbral 2: 3–4 inasistencias / semana -> Seguimiento Activo
        if unjustified_week >= 3:
            return AttendanceThresholdSummary(
                coder_id=coder_id,
                unjustified_absences_week=unjustified_week,
                unjustified_absences_month=unjustified_month,
                current_threshold="UMBRAL_2",
                threshold_level=2,
                responsible_area="TL_ESCALA_HSE",
                action_required="Seguimiento Activo: TL Desarrollo escala a HSE. HSE realiza contacto formal con el coder y documenta compromisos.",
                warning_alert="ALERTA: Coder superó Umbral 2 (3–4 faltas en la semana). Escalamiento obligatorio a HSE."
            )

        # Umbral 1: 1–2 inasistencias / semana -> Alerta Temprana
        if unjustified_week >= 1:
            return AttendanceThresholdSummary(
                coder_id=coder_id,
                unjustified_absences_week=unjustified_week,
                unjustified_absences_month=unjustified_month,
                current_threshold="UMBRAL_1",
                threshold_level=1,
                responsible_area="SOLO_TL",
                action_required="Alerta Temprana: TL Desarrollo valida la comunicación del coder y gestiona directamente. Registra en Moodle. HSE no interviene.",
                warning_alert=None
            )

        # Sin umbral activo
        return AttendanceThresholdSummary(
            coder_id=coder_id,
            unjustified_absences_week=0,
            unjustified_absences_month=unjustified_month,
            current_threshold="NINGUNO",
            threshold_level=0,
            responsible_area="SOLO_TL",
            action_required="Asistencia regular sin sanciones ni umbrales activos.",
            warning_alert=None
        )


hse_engine = HSEPolicyEngine()
