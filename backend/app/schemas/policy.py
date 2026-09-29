from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field

class PolicyEvaluationInput(BaseModel):
    coder_id: Optional[str] = None
    excuse_type: str = Field(..., description="Uno de los 10 motivos oficiales del PPTX Riwi")
    start_date: str = Field(..., description="Fecha inicial de la inasistencia (YYYY-MM-DD)")
    end_date: str = Field(..., description="Fecha final de la inasistencia (YYYY-MM-DD)")
    report_date: Optional[str] = Field(default=None, description="Fecha en que se envió el reporte (YYYY-MM-DD)")
    has_attachment: bool = Field(default=False, description="Indica si adjuntó soporte documental")
    attachment_is_eps_official: bool = Field(default=False, description="Indica si el soporte es una incapacidad médica oficial de EPS/IPS")
    is_sensitive: bool = Field(default=False, description="Indica si contiene datos sensibles de salud mental o calamidad íntima")
    unjustified_history_week: int = Field(default=0, description="Inasistencias injustificadas acumuladas esta semana")
    unjustified_history_month: int = Field(default=0, description="Inasistencias injustificadas acumuladas este mes")
    verify_external_attendance: bool = Field(default=True, description="Indica si debe consultar el adaptador de la plataforma hermana")

class PolicyEvaluationResult(BaseModel):
    decision: str = Field(..., description="POSIBLEMENTE_VALIDO | POSIBLEMENTE_INVALIDO | REVISION_MANUAL")
    confidence: float = Field(..., ge=0.0, le=1.0)
    days_calculated: int
    is_timely: bool
    timeliness_notes: str
    support_valid: bool
    support_notes: str
    escalate_to_hse: bool
    is_sensitive: bool
    requires_human_review: bool
    policy_rule_triggered: str
    recommendation_summary: str
    # Integración Plataforma Hermana (CONN-03 / EPIC-06)
    absence_verified: bool = Field(default=False, description="True si la inasistencia (ABSENT) fue confirmada en la plataforma hermana")
    external_absence_status: Optional[str] = Field(default=None, description="Estado reportado por la plataforma hermana: ABSENT, PRESENT, NO_RECORDS")
    sister_platform_notes: Optional[str] = Field(default=None, description="Detalles del cotejo realizado con el adaptador de asistencia")

class AttendanceThresholdSummary(BaseModel):
    coder_id: str
    unjustified_absences_week: int
    unjustified_absences_month: int
    current_threshold: str = Field(..., description="NINGUNO | UMBRAL_1 | UMBRAL_2 | UMBRAL_3 | UMBRAL_4")
    threshold_level: int = Field(..., ge=0, le=4)
    responsible_area: str = Field(..., description="SOLO_TL | TL_ESCALA_HSE | HSE_LIDERA | COORDINACION_HSE")
    action_required: str
    warning_alert: Optional[str] = None
