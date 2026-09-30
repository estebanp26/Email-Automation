from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class CoderExcuseSubmission(BaseModel):
    coder_name: str = Field(..., description="Nombre completo del coder")
    coder_email: str = Field(..., description="Correo del coder")
    document_id: str = Field(..., description="Número de cédula o documento de identidad")
    clan: str = Field(..., description="Clan o ruta técnica")
    shift: str = Field(default="Mañana (6:00 AM - 2:00 PM)", description="Jornada académica")
    category: str = Field(..., description="Uno de los 10 motivos oficiales del PPTX Riwi")
    start_date: str = Field(..., description="Fecha inicial de ausencia (YYYY-MM-DD)")
    end_date: str = Field(..., description="Fecha final de ausencia (YYYY-MM-DD)")
    reason: str = Field(..., description="Explicación detallada del motivo de inasistencia")
    attachment_filename: Optional[str] = None
    attachment_data_base64: Optional[str] = None
    attachment_mime_type: Optional[str] = "application/pdf"

class CoderAttendanceSummary(BaseModel):
    coder_id: str
    coder_name: str
    coder_cedula: str
    coder_route: str
    total_requests: int
    approved_requests: int
    disapproved_requests: int
    pending_requests: int
    unjustified_absences_week: int
    unjustified_absences_month: int
    current_threshold: str
    threshold_level: int
    responsible_area: str
    warning_alert: Optional[str] = None

class DashboardGlobalStats(BaseModel):
    total_requests: int
    approved_count: int
    disapproved_count: int
    pending_count: int
    threshold_alerts_count: int
    sensitive_cases_count: int
