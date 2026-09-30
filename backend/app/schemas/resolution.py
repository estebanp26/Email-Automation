from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class ManualResolutionInput(BaseModel):
    action: str = Field(..., description="APPROVE | DISAPPROVE | REQUEST_MORE_INFO")
    reviewer_id: Optional[str] = Field(default="hse-user-default", description="ID o email del analista HSE / TL")
    reviewer_name: str = Field(default="Equipo HSE Riwi", description="Nombre del analista o TL que valida")
    reviewer_role: str = Field(default="HSE", description="HSE | TEAM_LEADER | ADMIN")
    notes: str = Field(..., description="Observaciones y fundamento de la decisión (Slide 5 PPTX)")
    override_excuse_type: Optional[str] = Field(default=None, description="Modificación del motivo tipificado")
    override_start_date: Optional[str] = None
    override_end_date: Optional[str] = None
    dispatch_notification: bool = Field(default=True, description="Despachar automáticamente correo notificatorio al coder (BE-04)")

class ReconsiderationInput(BaseModel):
    new_action: str = Field(..., description="APPROVE | DISAPPROVE")
    reviewer_name: str
    reconsideration_reason: str = Field(..., description="Motivo de reapertura o nuevo soporte aportado")
    new_attachment_name: Optional[str] = None

class ResolutionAuditEntry(BaseModel):
    action: str
    reviewer_name: str
    reviewer_role: str
    notes: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ResolutionResponse(BaseModel):
    justification_id: str
    status: str
    resolution_mode: str
    has_human_intervention: bool
    hse_decision: str
    hse_notes: str
    hse_reviewer_name: str
    resolved_at: datetime
    notification_dispatched: bool
    notification_details: Optional[Dict[str, Any]] = None
    audit_trail: List[ResolutionAuditEntry] = Field(default_factory=list)
