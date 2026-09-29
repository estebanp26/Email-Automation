from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from .email import RawEmailInput, NormalizedEmail
from .coder import CoderBase, CoderIdentificationResult
from .policy import PolicyEvaluationResult, AttendanceThresholdSummary

class JustificationRecord(BaseModel):
    id: str = Field(..., description="ID único de la justificación")
    coder_id: Optional[str] = None
    coder_full_name: str
    coder_cedula: str
    coder_route: str
    sender_email: str
    sender_name: str
    subject: str
    cleaned_body: str
    excuse_type: str
    start_date: str
    end_date: str
    days_count: int
    status: str = Field(..., description="APPROVED | DISAPPROVED | REVISION_MANUAL | CODER_NOT_FOUND")
    decision: str
    ai_confidence: float
    ai_reasoning: str
    policy_rule_triggered: str
    is_sensitive: bool = False
    escalate_to_hse: bool = False
    current_threshold: str = "NINGUNO"
    threshold_level: int = 0
    has_formacion_cc: bool = True
    attachments_count: int = 0
    resolution_mode: str = "AUTOMATIC_AI"
    has_human_intervention: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class PipelineProcessRequest(BaseModel):
    raw_email: Optional[RawEmailInput] = None
    normalized_email: Optional[NormalizedEmail] = None
    run_async: bool = False

class PipelineExecutionResult(BaseModel):
    pipeline_id: str
    execution_status: str = Field(..., description="COMPLETED | QUEUED | FAILED")
    justification: Optional[JustificationRecord] = None
    execution_time_ms: float
    notes: List[str] = Field(default_factory=list)
