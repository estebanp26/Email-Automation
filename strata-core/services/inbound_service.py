from __future__ import annotations

import os
import sys
import json
import base64
import hashlib
import logging
import uuid
import re
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from schemas.inbound_dto import InboundEmailDTO, AttachmentDTO

logger = logging.getLogger("InboundEmailService")
if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_ATTACHMENTS_DIR = BASE_DIR / "temp_processing" / "inbound_attachments"
os.makedirs(DEFAULT_ATTACHMENTS_DIR, exist_ok=True)

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    psycopg2 = None


class InboundEmailService:
    """
    Servicio de recepción, desduplicación, almacenamiento seguro de adjuntos
    y persistencia transaccional para eventos de correo entrante.
    """

    def __init__(
        self,
        attachments_dir: Optional[Path] = None,
        db_connection_func: Optional[Any] = None
    ):
        self.attachments_dir = attachments_dir or DEFAULT_ATTACHMENTS_DIR
        self._db_conn_func = db_connection_func
        # Registro transaccional en memoria (garantiza idempotencia y resiliencia offline/testing)
        self._memory_registry: Dict[str, Dict[str, Any]] = {}
        # Cola de eventos recibidos para identificación y validación
        self.event_queue: List[Dict[str, Any]] = []

    def get_db_connection(self):
        """Obtiene conexión a la base de datos si está disponible."""
        if self._db_conn_func:
            try:
                return self._db_conn_func()
            except Exception as e:
                logger.debug(f"No se pudo conectar a la base de datos vía hook: {e}")
                return None

        if not psycopg2:
            return None

        host = os.getenv("POSTGRES_HOST", "localhost")
        port = int(os.getenv("POSTGRES_PORT", "5432"))
        dbname = os.getenv("POSTGRES_DB", "hse_email_automation")
        user = os.getenv("POSTGRES_USER", "hse_admin")
        password = os.getenv("POSTGRES_PASSWORD", "hse_segura_123")

        try:
            return psycopg2.connect(
                host=host,
                port=port,
                dbname=dbname,
                user=user,
                password=password,
                connect_timeout=2
            )
        except Exception as e:
            logger.debug(f"Conexión a PostgreSQL no disponible: {e}")
            return None

    def _ensure_tables_exist(self, conn) -> None:
        """Crea la tabla inbound_emails en PostgreSQL si aún no existe."""
        create_sql = """
        CREATE TABLE IF NOT EXISTS inbound_emails (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            message_id VARCHAR(255) NOT NULL UNIQUE,
            conversation_id VARCHAR(255),
            source_provider VARCHAR(50) NOT NULL DEFAULT 'OUTLOOK',
            sender_email VARCHAR(255) NOT NULL,
            sender_name VARCHAR(150),
            email_subject TEXT NOT NULL,
            email_body TEXT NOT NULL,
            received_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            status VARCHAR(50) NOT NULL DEFAULT 'PENDING_IDENTIFICATION',
            attachments JSONB DEFAULT '[]'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_inbound_emails_message_id ON inbound_emails(message_id);
        CREATE INDEX IF NOT EXISTS idx_inbound_emails_status ON inbound_emails(status);
        """
        try:
            with conn.cursor() as cur:
                cur.execute(create_sql)
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.warning(f"No se pudo verificar/crear tabla inbound_emails: {e}")

    def is_message_already_processed(self, message_id: str) -> bool:
        """
        Verifica si un message_id ya fue registrado previamente
        en la base de datos o en el registro transaccional en memoria.
        Garantiza estricta Idempotencia.
        """
        if not message_id:
            return False

        # 1. Verificación rápida en memoria
        if message_id in self._memory_registry:
            return True

        # 2. Verificación en PostgreSQL si está disponible
        conn = self.get_db_connection()
        if conn:
            try:
                self._ensure_tables_exist(conn)
                with conn.cursor() as cur:
                    # Verificar en tabla inbound_emails
                    cur.execute(
                        "SELECT 1 FROM inbound_emails WHERE message_id = %s LIMIT 1;",
                        (message_id,)
                    )
                    if cur.fetchone():
                        return True

                    # Verificar también en justifications por seguridad
                    cur.execute(
                        "SELECT 1 FROM justifications WHERE message_id = %s LIMIT 1;",
                        (message_id,)
                    )
                    if cur.fetchone():
                        return True
            except Exception as e:
                logger.warning(f"Error consultando existencia de message_id en DB: {e}")
            finally:
                try:
                    conn.close()
                except Exception:
                    pass

        return False

    def sanitize_filename(self, filename: str) -> str:
        """Sanitiza el nombre del archivo para prevenir ataques de Path Traversal."""
        clean_name = os.path.basename(filename or "archivo_adjunto")
        # Eliminar caracteres peligrosos
        clean_name = re.sub(r'[^a-zA-Z0-9_\-\.\(\)]', '_', clean_name)
        if not clean_name:
            clean_name = f"adjunto_{uuid.uuid4().hex[:8]}.bin"
        return clean_name

    def save_attachments_securely(
        self,
        message_id: str,
        attachments: List[AttachmentDTO]
    ) -> List[AttachmentDTO]:
        """
        Decodifica y almacena temporalmente los adjuntos en Base64 en disco seguro,
        calculando su tamaño real en bytes y hash criptográfico SHA-256.
        """
        if not attachments:
            return []

        safe_msg_id = re.sub(r'[^a-zA-Z0-9_\-]', '_', message_id)
        target_dir = self.attachments_dir / safe_msg_id
        target_dir.mkdir(parents=True, exist_ok=True)

        processed_attachments: List[AttachmentDTO] = []

        for index, att in enumerate(attachments):
            safe_filename = self.sanitize_filename(att.filename)
            file_path = target_dir / f"{index}_{safe_filename}"

            raw_bytes = b""
            if att.data_base64:
                try:
                    # Limpiar encabezados de data URI si vienen incluidos (ej: data:application/pdf;base64,...)
                    b64_str = att.data_base64
                    if "," in b64_str and ";base64" in b64_str:
                        b64_str = b64_str.split(",", 1)[1]
                    raw_bytes = base64.b64decode(b64_str)
                except Exception as e:
                    logger.warning(f"Error decodificando Base64 de {att.filename}: {e}")
                    raw_bytes = b""

            if raw_bytes:
                try:
                    with open(file_path, "wb") as f:
                        f.write(raw_bytes)
                    size_bytes = len(raw_bytes)
                    sha256_hash = hashlib.sha256(raw_bytes).hexdigest()
                    saved_path = str(file_path)
                except Exception as e:
                    logger.error(f"Error al escribir archivo en disco {file_path}: {e}")
                    size_bytes = len(raw_bytes)
                    sha256_hash = hashlib.sha256(raw_bytes).hexdigest()
                    saved_path = None
            else:
                size_bytes = att.size_bytes or 0
                sha256_hash = att.sha256_hash
                saved_path = None

            updated_att = AttachmentDTO(
                filename=att.filename,
                mime_type=att.mime_type,
                data_base64=att.data_base64,
                size_bytes=size_bytes,
                temp_path=saved_path,
                sha256_hash=sha256_hash
            )
            processed_attachments.append(updated_att)

        return processed_attachments

    def store_transactional_record(
        self,
        dto: InboundEmailDTO,
        status: str = "PENDING_IDENTIFICATION"
    ) -> Dict[str, Any]:
        """
        Almacena el registro transaccional con estado PENDING_IDENTIFICATION.
        Persiste en PostgreSQL y mantiene réplica en memoria.
        """
        transaction_id = str(uuid.uuid4())
        now_iso = datetime.now(timezone.utc).isoformat()

        attachments_meta = [
            {
                "filename": a.filename,
                "mime_type": a.mime_type,
                "size_bytes": a.size_bytes,
                "temp_path": a.temp_path,
                "sha256_hash": a.sha256_hash
            }
            for a in dto.attachments
        ]

        record = {
            "id": transaction_id,
            "message_id": dto.message_id,
            "conversation_id": dto.conversation_id,
            "source_provider": dto.source_provider,
            "sender_email": str(dto.sender_email),
            "sender_name": dto.sender_name,
            "email_subject": dto.email_subject,
            "email_body": dto.email_body,
            "received_at": dto.received_at or now_iso,
            "status": status,
            "attachments": attachments_meta,
            "created_at": now_iso
        }

        # Guardar en memoria
        self._memory_registry[dto.message_id] = record

        # Guardar en PostgreSQL si está disponible
        conn = self.get_db_connection()
        if conn:
            try:
                self._ensure_tables_exist(conn)
                insert_sql = """
                INSERT INTO inbound_emails (
                    id, message_id, conversation_id, source_provider,
                    sender_email, sender_name, email_subject, email_body,
                    received_at, status, attachments
                ) VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s
                )
                ON CONFLICT (message_id) DO NOTHING
                RETURNING id;
                """
                with conn.cursor() as cur:
                    cur.execute(insert_sql, (
                        transaction_id,
                        dto.message_id,
                        dto.conversation_id,
                        dto.source_provider,
                        str(dto.sender_email),
                        dto.sender_name,
                        dto.email_subject,
                        dto.email_body,
                        dto.received_at,
                        status,
                        json.dumps(attachments_meta)
                    ))
                    res = cur.fetchone()
                    if res:
                        transaction_id = str(res[0])
                        record["id"] = transaction_id
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.error(f"Error al guardar registro transaccional en PostgreSQL: {e}")
            finally:
                try:
                    conn.close()
                except Exception:
                    pass

        return record

    async def enqueue_for_identification_and_validation(
        self,
        dto: InboundEmailDTO,
        transaction_id: str
    ) -> None:
        """
        Encola el evento para posterior procesamiento: identificación de coder
        y evaluación de justificación en Strata Core.
        """
        event = {
            "transaction_id": transaction_id,
            "message_id": dto.message_id,
            "conversation_id": dto.conversation_id,
            "sender_email": str(dto.sender_email),
            "sender_name": dto.sender_name,
            "email_subject": dto.email_subject,
            "enqueued_at": datetime.now(timezone.utc).isoformat(),
            "status": "QUEUED"
        }
        self.event_queue.append(event)
        logger.info(
            f"Evento {dto.message_id} encolado para identificación y validación (Cola: {len(self.event_queue)})"
        )


# Singleton del servicio para toda la aplicación
inbound_service = InboundEmailService()
