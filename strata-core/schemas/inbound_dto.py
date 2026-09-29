from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Union, Any, Dict
from pydantic import BaseModel, Field, EmailStr, field_validator, model_validator


class AttachmentDTO(BaseModel):
    """Esquema de transferencia para adjuntos de correo."""
    filename: str = Field(..., description="Nombre del archivo adjunto")
    mime_type: Optional[str] = Field("application/octet-stream", description="Tipo MIME del adjunto")
    data_base64: Optional[str] = Field(None, description="Contenido binario codificado en Base64")
    size_bytes: Optional[int] = Field(0, description="Tamaño del archivo en bytes")
    temp_path: Optional[str] = Field(None, description="Ruta segura temporal en disco")
    sha256_hash: Optional[str] = Field(None, description="Hash SHA-256 para integridad y deduplicación")

    @model_validator(mode="before")
    @classmethod
    def normalize_attachment_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Normalizar alias comunes (name, contentType, base64)
            filename = data.get("filename") or data.get("name") or "adjunto.bin"
            mime_type = data.get("mime_type") or data.get("contentType") or "application/octet-stream"
            data_base64 = data.get("data_base64") or data.get("base64") or data.get("contentBytes")
            size_bytes = data.get("size_bytes") or data.get("size") or 0
            return {
                "filename": filename,
                "mime_type": mime_type,
                "data_base64": data_base64,
                "size_bytes": size_bytes,
                "temp_path": data.get("temp_path"),
                "sha256_hash": data.get("sha256_hash")
            }
        return data


class InboundEmailDTO(BaseModel):
    """
    DTO para eventos de correo entrante desde adaptadores de Outlook y Gmail.
    Estandariza los datos y garantiza la generación de identificadores únicos.
    """
    source_provider: str = Field("OUTLOOK", description="Proveedor del correo: OUTLOOK o GMAIL")
    message_id: Optional[str] = Field(None, description="Identificador único del mensaje")
    conversation_id: Optional[str] = Field(None, description="Identificador único del hilo o conversación")
    sender_email: EmailStr = Field(..., description="Dirección de correo electrónico del remitente")
    sender_name: Optional[str] = Field("Coder", description="Nombre del remitente")
    email_subject: str = Field(..., description="Asunto del correo")
    email_body: str = Field(..., description="Cuerpo del mensaje")
    received_at: Optional[Union[datetime, str]] = Field(None, description="Marca de tiempo de recepción")
    attachments: List[AttachmentDTO] = Field(default_factory=list, description="Lista de archivos adjuntos")
    has_attachments: Optional[bool] = Field(None, description="Indica si el correo incluye adjuntos")

    @model_validator(mode="before")
    @classmethod
    def remap_raw_fields(cls, data: Any) -> Any:
        """Permite compatibilidad total con formatos raw de conectores o Webhooks."""
        if not isinstance(data, dict):
            return data

        d = data.copy()

        # Remapeo de remitente
        if "sender_email" not in d:
            from_field = d.get("from") or d.get("from_email") or d.get("sender") or ""
            if "<" in from_field and ">" in from_field:
                parts = from_field.split("<", 1)
                if "sender_name" not in d and parts[0].strip():
                    d["sender_name"] = parts[0].strip().strip('"').strip("'")
                d["sender_email"] = parts[1].split(">", 1)[0].strip()
            else:
                d["sender_email"] = from_field.strip()

        # Remapeo de nombre
        if not d.get("sender_name"):
            d["sender_name"] = d.get("name") or "Coder"

        # Remapeo de asunto
        if "email_subject" not in d:
            d["email_subject"] = d.get("subject") or d.get("title") or "Sin asunto"

        # Remapeo de cuerpo
        if "email_body" not in d:
            d["email_body"] = d.get("body") or d.get("text") or d.get("snippet") or d.get("content") or ""

        # Remapeo de message_id y conversation_id
        if "message_id" not in d or not d.get("message_id"):
            d["message_id"] = d.get("id") or d.get("messageId")

        if "conversation_id" not in d or not d.get("conversation_id"):
            d["conversation_id"] = d.get("threadId") or d.get("conversationId")

        # Remapeo de fecha
        if "received_at" not in d or not d.get("received_at"):
            d["received_at"] = d.get("date") or d.get("timestamp")

        # Proveedor por defecto según presencia de threadId (Gmail) o provider explícito
        if "source_provider" not in d:
            if d.get("threadId"):
                d["source_provider"] = "GMAIL"
            else:
                d["source_provider"] = "OUTLOOK"

        return d

    @field_validator("source_provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        prov = v.strip().upper() if v else "OUTLOOK"
        if prov not in ("OUTLOOK", "GMAIL", "IMAP"):
            prov = "OUTLOOK"
        return prov

    @model_validator(mode="after")
    def set_identifiers_and_defaults(self) -> InboundEmailDTO:
        # Generar message_id único si viene vacío o nulo
        if not self.message_id or not str(self.message_id).strip():
            self.message_id = f"msg_{uuid.uuid4().hex}"
        else:
            self.message_id = str(self.message_id).strip()

        # Generar conversation_id único si viene vacío o nulo
        if not self.conversation_id or not str(self.conversation_id).strip():
            self.conversation_id = f"conv_{uuid.uuid4().hex}"
        else:
            self.conversation_id = str(self.conversation_id).strip()

        # Normalizar received_at a formato ISO string
        if not self.received_at:
            self.received_at = datetime.now(timezone.utc).isoformat()
        elif isinstance(self.received_at, datetime):
            self.received_at = self.received_at.isoformat()
        else:
            self.received_at = str(self.received_at).strip()

        # Bandera de adjuntos
        if self.has_attachments is None:
            self.has_attachments = len(self.attachments) > 0

        return self


class InboundEmailResponse(BaseModel):
    """Respuesta HTTP 202 Accepted para ingesta exitosa."""
    status: str = Field("ACCEPTED", description="Estado de la solicitud")
    message: str = Field("Event queued for identification and validation", description="Mensaje de confirmación")
    message_id: str = Field(..., description="ID único del correo")
    conversation_id: str = Field(..., description="ID de la conversación")
    transaction_id: Optional[str] = Field(None, description="UUID del registro transaccional")
    state: str = Field("PENDING_IDENTIFICATION", description="Estado del flujo transaccional")
    attachments_count: int = Field(0, description="Cantidad de adjuntos procesados")


class IdempotencyResponse(BaseModel):
    """Respuesta HTTP 200 OK para detección de idempotencia (correo duplicado)."""
    status: str = Field("OK", description="Estado de idempotencia")
    message: str = Field("Event already processed", description="Mensaje de detección de duplicado")
    message_id: str = Field(..., description="ID del correo duplicado detectado")
