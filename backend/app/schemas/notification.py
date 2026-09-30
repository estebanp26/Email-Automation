from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class NotificationDispatchInput(BaseModel):
    recipient_email: str = Field(..., description="Correo del destinatario (coder o HSE)")
    recipient_name: str = Field(..., description="Nombre del destinatario")
    template_type: str = Field(..., description="APPROVED | DISAPPROVED | REQUEST_MORE_INFO | CODER_NOT_FOUND | HSE_ALERT")
    justification_id: Optional[str] = None
    coder_cedula: Optional[str] = None
    coder_route: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    excuse_type: Optional[str] = None
    notes: Optional[str] = None
    threshold_level: Optional[int] = 0
    in_reply_to_message_id: Optional[str] = None
    original_subject: Optional[str] = None
    cc_emails: Optional[List[str]] = Field(default_factory=list)

class NotificationDispatchResult(BaseModel):
    dispatch_id: str
    status: str = Field(..., description="SENT | SIMULATED | FAILED")
    recipient: str
    subject: str
    html_body: str
    in_reply_to: Optional[str] = None
    dispatched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class NotificationPreviewRequest(BaseModel):
    template_type: str
    recipient_name: str = "Coder Riwi"
    excuse_type: str = "incapacidad_medica"
    start_date: str = "2026-09-28"
    end_date: str = "2026-09-29"
    notes: Optional[str] = None
    threshold_level: int = 0
