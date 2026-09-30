from datetime import datetime, timezone
from typing import List, Optional, Union
from pydantic import BaseModel, Field, EmailStr

class RawAttachmentInput(BaseModel):
    filename: str
    mime_type: Optional[str] = None
    data_base64: str
    size_bytes: Optional[int] = None

class RawEmailInput(BaseModel):
    source_provider: str = Field(default="SIMULATION", description="OUTLOOK, GMAIL, SIMULATION, PORTAL")
    message_id: Optional[str] = Field(default=None, description="Identificador único del mensaje RFC")
    conversation_id: Optional[str] = Field(default=None, description="Identificador de hilo o conversación")
    sender_email: str = Field(..., description="Correo del remitente")
    sender_name: Optional[str] = Field(default=None, description="Nombre descriptivo del remitente")
    recipient_email: Optional[str] = Field(default=None, description="Buzón institucional receptor")
    cc_emails: Optional[List[str]] = Field(default_factory=list, description="Lista de correos en copia (CC)")
    subject: str = Field(..., description="Asunto original del correo")
    body: str = Field(..., description="Cuerpo del correo en texto plano o HTML")
    received_at: Optional[Union[str, datetime]] = Field(default=None, description="Fecha y hora de recepción")
    attachments: Optional[List[RawAttachmentInput]] = Field(default_factory=list, description="Archivos adjuntos")

class NormalizedAttachment(BaseModel):
    filename: str
    mime_type: str
    size_bytes: int
    sha256_hash: str
    data_base64: Optional[str] = None
    is_valid_evidence: bool = True
    validation_error: Optional[str] = None

class PreliminaryExtraction(BaseModel):
    detected_cedula: Optional[str] = None
    detected_dates: List[str] = Field(default_factory=list)
    detected_start_date: Optional[str] = None
    detected_end_date: Optional[str] = None
    detected_clan: Optional[str] = None
    detected_shift: Optional[str] = None
    suspected_motive: Optional[str] = None
    is_sensitive: bool = False

class NormalizedEmail(BaseModel):
    source_provider: str
    message_id: str
    conversation_id: Optional[str] = None
    sender_email: str
    sender_name: str
    recipient_email: Optional[str] = None
    cc_emails: List[str] = Field(default_factory=list)
    has_formacion_cc: bool = Field(
        default=False, 
        description="Indica si se incluyó con copia formal a formacion.barranquilla@riwi.io (Slide 5 PPTX)"
    )
    subject: str
    clean_subject: str
    raw_body: str
    cleaned_body: str
    received_at: datetime
    attachments: List[NormalizedAttachment] = Field(default_factory=list)
    preliminary_extraction: PreliminaryExtraction

class EmailIngestResponse(BaseModel):
    status: str = Field(default="success", description="success | warning | error")
    ingestion_id: str
    normalized_email: NormalizedEmail
    warnings: List[str] = Field(default_factory=list)
    processed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
