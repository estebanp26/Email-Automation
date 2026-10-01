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

        # Procesar y persistir inmediatamente en la tabla 'justifications' para visualización en frontend
        try:
            self.process_justification(dto=dto, transaction_id=transaction_id)
        except Exception as e:
            logger.warning(f"Aviso: Fallo no bloqueante en persistencia inmediata de justificación: {e}")

        return record

    def resolve_coder(
        self,
        conn,
        sender_email: str,
        sender_name: Optional[str],
        subject: str,
        body: str
    ) -> Tuple[Optional[str], str, str]:
        """
        Resuelve el Coder asociado en PostgreSQL mediante cascada:
        1. Búsqueda exacta por email institucional o personal en coders.email.
        2. Búsqueda por cédula encontrada en el asunto o cuerpo (patrón 7 a 10 dígitos).
        3. Búsqueda por palabras del nombre del remitente (si tiene al menos 2 palabras clave).
        Retorna: (coder_id, resolved_name, coder_identification_status: 'IDENTIFIED' | 'CODER_NOT_FOUND')
        """
        try:
            with conn.cursor() as cur:
                # 1. Búsqueda exacta por email
                cur.execute(
                    "SELECT id, full_name FROM coders WHERE LOWER(email) = LOWER(%s) LIMIT 1;",
                    (sender_email.strip(),)
                )
                row = cur.fetchone()
                if row:
                    return str(row[0]), row[1], "IDENTIFIED"

                # 2. Cédula en asunto o cuerpo
                cedulas = re.findall(r'\b\d{7,10}\b', f"{subject} {body}")
                for doc in cedulas:
                    cur.execute(
                        "SELECT id, full_name FROM coders WHERE cedula = %s LIMIT 1;",
                        (doc,)
                    )
                    row = cur.fetchone()
                    if row:
                        return str(row[0]), row[1], "IDENTIFIED"

                # 3. Coincidencia por palabras del nombre
                name_to_check = sender_name or ""
                words = [w.lower() for w in re.findall(r'[a-zA-ZáéíóúÁÉÍÓÚñÑ]+', name_to_check) if len(w) >= 3]
                if len(words) >= 2:
                    query = "SELECT id, full_name FROM coders WHERE " + " AND ".join(["LOWER(full_name) LIKE %s" for _ in words]) + " LIMIT 1;"
                    cur.execute(query, tuple(f"%{w}%" for w in words))
                    row = cur.fetchone()
                    if row:
                        return str(row[0]), row[1], "IDENTIFIED"
        except Exception as e:
            logger.warning(f"Error resolviendo coder en DB: {e}")

        return None, (sender_name or sender_email), "CODER_NOT_FOUND"

    def evaluate_excuse_heuristics(self, subject: str, body: str, attachments: List[Any]) -> Dict[str, Any]:
        """
        Evaluador determinista conforme al reglamento HSE de Riwi.
        Determina categoría sugerida, tipo de novedad, confianza y motivo.
        """
        text = f"{subject} {body}".lower()
        has_att = len(attachments) > 0

        # Regla 1: Extemporaneidad
        if any(w in text for w in ["vencid", "semana pasada", "extemporan"]):
            return {
                "ai_recommendation": "POSIBLEMENTE_INVALIDO",
                "validation_status": "POSIBLEMENTE_INVALIDO",
                "ai_confidence": 0.88,
                "excuse_type": "inasistencia_medica",
                "ai_reason": "Justificación radicada de forma extemporánea (superior a 48 horas) sin justificación de fuerza mayor."
            }

        # Regla 2: Soporte formal EPS (SURA, Sanitas, Salud Total, etc.)
        if any(eps in text for eps in ["sura", "sanitas", "salud total", "nueva eps", "compensar", "famisanar", "coosalud", "mutual ser", "eps"]) and has_att:
            return {
                "ai_recommendation": "POSIBLEMENTE_VALIDO",
                "validation_status": "POSIBLEMENTE_VALIDO",
                "ai_confidence": 0.95,
                "excuse_type": "inasistencia_medica",
                "ai_reason": "Incapacidad médica formal notificada con entidad promotora de salud (EPS) y evidencia adjunta verificada."
            }

        # Regla 3: Cita médica (preaviso vs posterior)
        if any(c in text for c in ["cita medica", "cita médica", "cita odontol", "procedimiento"]):
            if any(p in text for p in ["ayer", "asistí", "asisti", "estuve", "no alcancé", "no alcance"]):
                return {
                    "ai_recommendation": "POSIBLEMENTE_INVALIDO",
                    "validation_status": "POSIBLEMENTE_INVALIDO",
                    "ai_confidence": 0.90,
                    "excuse_type": "inasistencia_medica",
                    "ai_reason": "Las citas médicas programadas deben notificarse previamente antes del día de entrenamiento. No se admite radicación posterior."
                }
            else:
                return {
                    "ai_recommendation": "POSIBLEMENTE_VALIDO" if has_att else "REVISION_MANUAL",
                    "validation_status": "POSIBLEMENTE_VALIDO" if has_att else "REVISION_MANUAL",
                    "ai_confidence": 0.92 if has_att else 0.75,
                    "excuse_type": "inasistencia_medica",
                    "ai_reason": "Cita médica notificada con antelación reglamentaria antes de la jornada." if has_att else "Cita médica reportada previamente pero sin soporte adjunto. Requiere revisión manual."
                }

        # Regla 4: Calamidad doméstica / luto
        if any(cal in text for cal in ["calamidad", "falleci", "luto", "entierro", "urgencia familiar"]):
            return {
                "ai_recommendation": "REVISION_MANUAL",
                "validation_status": "REVISION_MANUAL",
                "ai_confidence": 0.85,
                "excuse_type": "calamidad",
                "ai_reason": "Reporte de calamidad o urgencia familiar. Requiere validación discrecional del Team Leader HSE."
            }

        # Regla 5: Quebranto de salud / reposo médico sin incapacidad EPS
        if any(q in text for q in ["fiebre", "malestar", "quebranto", "reposo", "enfermo", "dolor", "vomit", "vómit", "colico", "cólico", "migraña", "indispuest", "descompuest"]):
            return {
                "ai_recommendation": "REVISION_MANUAL",
                "validation_status": "REVISION_MANUAL",
                "ai_confidence": 0.85,
                "excuse_type": "enfermedad_sin_soporte",
                "ai_reason": "Reporte de quebranto de salud o reposo médico imprevisto sin incapacidad oficial EPS adjunta. Sujeto a verificación manual de tolerancia HSE."
            }

        # Regla 6: Falla técnica / fluido eléctrico / conectividad
        if any(f in text for f in ["corte", "fibra", "internet", "energia", "energía", "luz", "cargador", "computador"]):
            return {
                "ai_recommendation": "REVISION_MANUAL",
                "validation_status": "REVISION_MANUAL",
                "ai_confidence": 0.75,
                "excuse_type": "falla_tecnica",
                "ai_reason": "Reporte de contingencia técnica o corte de conectividad/fluido. En espera de auditoría de ticket técnico."
            }

        # Por defecto: Revisión manual
        return {
            "ai_recommendation": "REVISION_MANUAL",
            "validation_status": "REVISION_MANUAL",
            "ai_confidence": 0.70,
            "excuse_type": "no_identificado",
            "ai_reason": "Solicitud ingresada por bandeja de correo. Encolada para auditoría y validación del Team Leader HSE."
        }

    def extract_dates(self, subject: str, body: str) -> Tuple[str, str]:
        """Extrae fechas en formato YYYY-MM-DD o asume la fecha actual."""
        today = datetime.now(timezone.utc).date()
        today_str = today.isoformat()

        # Buscar fechas explícitas YYYY-MM-DD
        iso_dates = re.findall(r'\b(202[4-9]-\d{2}-\d{2})\b', f"{subject} {body}")
        if iso_dates:
            d1 = iso_dates[0]
            d2 = iso_dates[1] if len(iso_dates) > 1 else d1
            return min(d1, d2), max(d1, d2)

        # Buscar patrones DD/MM/YYYY o DD-MM-YYYY
        dmy_dates = re.findall(r'\b(\d{1,2})[/\-](\d{1,2})[/\-](202[4-9])\b', f"{subject} {body}")
        if dmy_dates:
            try:
                day, month, year = dmy_dates[0]
                dt = datetime(int(year), int(month), int(day)).date().isoformat()
                return dt, dt
            except Exception:
                pass

        # Buscar menciones textuales de meses en español (ej: 30 de septiembre)
        meses = {
            "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
            "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12
        }
        text_lower = f"{subject} {body}".lower()
        for mes_nombre, mes_num in meses.items():
            match = re.search(r'\b(\d{1,2})\s+de\s+' + mes_nombre, text_lower)
            if match:
                try:
                    dia = int(match.group(1))
                    dt = datetime(today.year, mes_num, dia).date().isoformat()
                    return dt, dt
                except Exception:
                    pass

        return today_str, today_str

    def process_justification(self, dto: InboundEmailDTO, transaction_id: str) -> Optional[str]:
        """
        Inserta o actualiza el registro en la tabla 'justifications' de PostgreSQL
        para que se refleje inmediatamente en el frontend (/requests).
        """
        conn = self.get_db_connection()
        if not conn:
            logger.error("No se pudo obtener conexión a PostgreSQL para crear justificación.")
            return None

        try:
            # 1. Resolver Coder
            coder_id, coder_name, ident_status = self.resolve_coder(
                conn=conn,
                sender_email=str(dto.sender_email),
                sender_name=dto.sender_name,
                subject=dto.email_subject,
                body=dto.email_body
            )

            # 2. Evaluación determinista de la justificación
            eval_result = self.evaluate_excuse_heuristics(
                subject=dto.email_subject,
                body=dto.email_body,
                attachments=dto.attachments
            )

            # 3. Extracción de fechas
            start_date, end_date = self.extract_dates(dto.email_subject, dto.email_body)

            # 4. Formatear adjuntos para columna JSONB
            attachments_meta = [
                {
                    "filename": getattr(a, "filename", "adjunto.pdf"),
                    "mime_type": getattr(a, "mime_type", "application/pdf"),
                    "size_bytes": getattr(a, "size_bytes", 0),
                    "temp_path": getattr(a, "temp_path", None),
                    "sha256_hash": getattr(a, "sha256_hash", None)
                }
                for a in dto.attachments
            ]

            justification_id = str(uuid.uuid4())
            insert_sql = """
            INSERT INTO justifications (
                id, coder_id, sender_email, sender_name, email_subject, email_body,
                message_id, conversation_id, received_at, intent, excuse_type,
                start_date, end_date, ai_recommendation, ai_confidence, ai_reason,
                ai_response, ai_model, coder_identification_status, validation_status,
                resolution_mode, has_human_intervention, validation_notes, attachments
            ) VALUES (
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s
            )
            ON CONFLICT (message_id) DO UPDATE SET
                email_subject = EXCLUDED.email_subject,
                email_body = EXCLUDED.email_body,
                coder_id = COALESCE(justifications.coder_id, EXCLUDED.coder_id),
                sender_name = COALESCE(EXCLUDED.sender_name, justifications.sender_name),
                ai_recommendation = EXCLUDED.ai_recommendation,
                ai_confidence = EXCLUDED.ai_confidence,
                ai_reason = EXCLUDED.ai_reason,
                validation_status = EXCLUDED.validation_status,
                attachments = EXCLUDED.attachments,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id;
            """

            with conn.cursor() as cur:
                cur.execute(insert_sql, (
                    justification_id,
                    coder_id,
                    str(dto.sender_email),
                    coder_name,
                    dto.email_subject,
                    dto.email_body,
                    dto.message_id,
                    dto.conversation_id or dto.message_id,
                    dto.received_at or datetime.now(timezone.utc),
                    "EXCUSA",
                    eval_result["excuse_type"],
                    start_date,
                    end_date,
                    eval_result["ai_recommendation"],
                    eval_result["ai_confidence"],
                    eval_result["ai_reason"],
                    json.dumps(eval_result),
                    "qwen2.5:1.5b",
                    ident_status,
                    eval_result["validation_status"],
                    "AUTOMATIC_AI",
                    False,
                    eval_result["ai_reason"],
                    json.dumps(attachments_meta)
                ))
                res = cur.fetchone()
                if res:
                    justification_id = str(res[0])

                # Actualizar estado en inbound_emails
                cur.execute(
                    "UPDATE inbound_emails SET status = 'PROCESSED' WHERE message_id = %s;",
                    (dto.message_id,)
                )

            conn.commit()
            logger.info(
                f"[✓] Justificación registrada en BD exitosamente (ID: {justification_id}, Coder: {coder_name}, Estado: {eval_result['validation_status']})"
            )
            return justification_id
        except Exception as e:
            conn.rollback()
            logger.error(f"Error procesando e insertando justificación en BD: {e}")
            return None
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def sync_unprocessed_inbounds(self) -> None:
        """Sincroniza cualquier correo en inbound_emails que aún no figure en justifications."""
        conn = self.get_db_connection()
        if not conn:
            return
        try:
            self._ensure_tables_exist(conn)
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT i.id, i.message_id, i.conversation_id, i.source_provider,
                           i.sender_email, i.sender_name, i.email_subject, i.email_body,
                           i.received_at, i.attachments
                    FROM inbound_emails i
                    LEFT JOIN justifications j ON i.message_id = j.message_id
                    WHERE j.id IS NULL
                    ORDER BY i.received_at ASC;
                """)
                unprocessed = cur.fetchall()

            for row in unprocessed:
                inbound_id, msg_id, conv_id, src_prov, s_email, s_name, subj, body, rec_at, atts = row
                attachments_list = []
                if isinstance(atts, str):
                    try:
                        atts = json.loads(atts)
                    except Exception:
                        atts = []
                if isinstance(atts, list):
                    for a in atts:
                        if isinstance(a, dict):
                            attachments_list.append(AttachmentDTO(
                                filename=a.get("filename", "adjunto.pdf"),
                                mime_type=a.get("mime_type", "application/pdf"),
                                size_bytes=a.get("size_bytes", 0),
                                temp_path=a.get("temp_path"),
                                sha256_hash=a.get("sha256_hash")
                            ))
                dto = InboundEmailDTO(
                    source_provider=src_prov or "GMAIL",
                    sender_email=s_email,
                    sender_name=s_name,
                    email_subject=subj,
                    email_body=body,
                    received_at=rec_at.isoformat() if hasattr(rec_at, 'isoformat') else str(rec_at),
                    message_id=msg_id,
                    conversation_id=conv_id,
                    attachments=attachments_list,
                    has_attachments=len(attachments_list) > 0
                )
                self.process_justification(dto=dto, transaction_id=str(inbound_id))
        except Exception as e:
            logger.warning(f"Error sincronizando inbounds no procesados: {e}")
        finally:
            try:
                conn.close()
            except Exception:
                pass

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
        self.process_justification(dto=dto, transaction_id=transaction_id)


# Singleton del servicio para toda la aplicación
inbound_service = InboundEmailService()

