import re
import uuid
import base64
import hashlib
import html
from datetime import datetime, timezone
from email.utils import parseaddr
from typing import List, Tuple, Optional, Dict, Any
from pathlib import Path

from ..config import settings
from ..schemas.email import (
    RawEmailInput,
    RawAttachmentInput,
    NormalizedAttachment,
    PreliminaryExtraction,
    NormalizedEmail,
    EmailIngestResponse,
)

# 10 Motivos Oficiales tipificados en la Presentación PPTX Riwi HSE
OFFICIAL_MOTIVES_KEYWORDS = {
    "incapacidad_medica": [
        r"\bincapacidad\b", r"\beps\b", r"\bips\b", r"\bsura\b", r"\bsanitas\b",
        r"\bnueva eps\b", r"\bsalud total\b", r"\bcompensar\b", r"\borden medica\b",
        r"\borden médica\b", r"\blicencia medica\b", r"\blicencia médica\b", r"\breposo\b"
    ],
    "enfermo_sin_incapacidad": [
        r"\bmalestar\b", r"\bindispuesto\b", r"\bindispuesta\b", r"\bfiebre\b",
        r"\bdolor\b", r"\bmigraña\b", r"\bvómito\b", r"\bvomito\b", r"\bgripa\b",
        r"\bgripe\b", r"\bestomago\b", r"\bestómago\b", r"\benfermo sin incapacidad\b"
    ],
    "cita_medica": [
        r"\bcita medica\b", r"\bcita médica\b", r"\bodontologia\b", r"\bodontología\b",
        r"\bcontrol medico\b", r"\bcontrol médico\b", r"\bespecialista\b", r"\blaboratorio\b",
        r"\btoma de muestra\b"
    ],
    "dificultades_familiares": [
        r"\bcalamidad\b", r"\bfallecimiento\b", r"\bduelo\b", r"\bluto\b",
        r"\bfamiliar\b", r"\burgencia familiar\b", r"\bemergencia familiar\b",
        r"\bsepelio\b", r"\bentierro\b"
    ],
    "problemas_economicos": [
        r"\beconomico\b", r"\beconómico\b", r"\btransporte\b", r"\bpasajes\b",
        r"\bsin dinero\b", r"\balimentacion\b", r"\balimentación\b", r"\bsin recursos\b"
    ],
    "jornada_laboral": [
        r"\btrabajo\b", r"\blaboral\b", r"\bturno\b", r"\bempleo\b", r"\bempresa\b",
        r"\bjornada de trabajo\b", r"\bhorario laboral\b"
    ],
    "jornada_estudio": [
        r"\buniversidad\b", r"\bparcial\b", r"\bevaluacion\b", r"\bevaluación\b",
        r"\bclase obligatoria\b", r"\bacademico\b", r"\bacadémico\b", r"\bcolegio\b",
        r"\bexamen\b", r"\bsemestre\b"
    ],
    "situacion_emocional_critica": [
        r"\bcrisis\b", r"\bpanico\b", r"\bpánico\b", r"\bansiedad\b", r"\bdepresion\b",
        r"\bdepresión\b", r"\bsalud mental\b", r"\bpsicologia\b", r"\bpsicología\b",
        r"\bpsiquiatria\b", r"\bpsiquiatría\b", r"\bcolapso emocional\b"
    ],
    "tramite_institucional": [
        r"\btramite\b", r"\btrámite\b", r"\bbanco\b", r"\balcaldia\b", r"\balcaldía\b",
        r"\bnotaria\b", r"\bnotaría\b", r"\bfiscalia\b", r"\bfiscalía\b", r"\bjuzgado\b",
        r"\bregistraduria\b", r"\bregistraduría\b", r"\brenovacion\b", r"\brenovación\b"
    ],
}

KNOWN_CLANS = [
    "turing", "gosling", "lovelace", "hopper", "van rossum", "ritchie",
    "berners-lee", "hamilton", "gates", "cooper", "neumann", "torvalds",
    "clarke", "kay", "knuth", "shannon", "minsky", "dijkstra", "cerf",
    "kahn", "lamport", "milner", "backus", "chomsky", "babbage"
]

MIME_TYPE_MAP = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}


class EmailNormalizationService:
    """
    Servicio de Ingesta y Normalización de Correos Electrónicos (BE-01).
    Transforma payloads heterogéneos de Outlook, Gmail o Simulación en una entidad canónica
    cumpliendo estrictamente las directrices del PPTX de Asistencias Riwi.
    """

    @classmethod
    def clean_sender(cls, sender_email: str, sender_name: Optional[str] = None) -> Tuple[str, str]:
        """Extrae el email y el nombre legible eliminando encapsulamientos RFC 822."""
        raw_combined = f"{sender_name or ''} <{sender_email}>" if sender_name else sender_email
        parsed_name, parsed_email = parseaddr(raw_combined)

        clean_email = (parsed_email or sender_email).strip().lower()
        # Eliminar posibles corchetes o comillas residuales
        clean_email = re.sub(r"[<>'\"]", "", clean_email).strip()

        if parsed_name and parsed_name.strip():
            clean_name = parsed_name.strip().strip("'\"")
        elif sender_name and sender_name.strip():
            clean_name = sender_name.strip().strip("'\"")
        else:
            # Deducir nombre a partir del prefijo del correo (ej. carlos.perez -> Carlos Perez)
            local_part = clean_email.split("@")[0]
            clean_name = " ".join([p.capitalize() for p in re.split(r"[._\-]", local_part) if p])

        return clean_email, clean_name

    @classmethod
    def clean_subject(cls, subject: str) -> Tuple[str, str]:
        """Limpia prefijos de respuesta/reenvío y corchetes corporativos."""
        raw_subject = subject.strip()
        # Quitar prefijos sucesivos de Re, Fwd, RV, RES
        pattern = r"^(?:(?:re|fwd|rv|res)[\s:]*|\[[^\]]+\]\s*)+"
        clean_sub = re.sub(pattern, "", raw_subject, flags=re.IGNORECASE).strip()
        return raw_subject, clean_sub

    @classmethod
    def clean_html_and_text(cls, body: str) -> str:
        """Convierte HTML a texto plano estructurado y decodifica entidades."""
        if not body:
            return ""

        text = body
        # Si contiene etiquetas HTML, limpiarlas
        if re.search(r"<(?:html|body|div|p|br|table|span)", text, flags=re.IGNORECASE):
            # Reemplazar saltos de línea y párrafos
            text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
            text = re.sub(r"</(?:p|div|tr|li|h[1-6])>", "\n", text, flags=re.IGNORECASE)
            # Eliminar bloques de script y style
            text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
            # Eliminar cualquier etiqueta HTML remanente
            text = re.sub(r"<[^>]+>", " ", text)

        # Decodificar entidades HTML (&aacute; -> á, &nbsp; -> ' ', etc.)
        text = html.unescape(text)

        # Normalizar retornos de carro de Windows (\r\n -> \n)
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Quitar citas de hilos anteriores (historial de correo)
        thread_cut_patterns = [
            r"\n\s*-+\s*Mensaje original\s*-+",
            r"\n\s*De:\s*.*?\n\s*Enviado el:\s*",
            r"\n\s*From:\s*.*?\n\s*Sent:\s*",
            r"\n\s*On\s+.*?\s+wrote:\s*\n",
            r"\n\s*El\s+.*?\s+escribi[óo]:\s*\n",
            r"\n\s*_{10,}\s*\n",
        ]
        for pat in thread_cut_patterns:
            parts = re.split(pat, text, maxsplit=1, flags=re.IGNORECASE)
            if len(parts) > 1:
                text = parts[0]

        # Compactar espacios y saltos de línea repetidos
        lines = [line.strip() for line in text.split("\n")]
        # Mantener párrafos con un único salto intermedio
        cleaned = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
        return cleaned

    @classmethod
    def check_formacion_cc(cls, recipient: Optional[str], cc_emails: List[str]) -> Tuple[List[str], bool]:
        """
        Valida si el correo incluyó copia obligatoria a formacion.barranquilla@riwi.io (Slide 5 PPTX).
        """
        target = settings.FORMACION_EMAIL_OFFICIAL.lower().strip()
        cleaned_cc = []
        has_formacion = False

        if recipient and target in recipient.lower():
            has_formacion = True

        for c in cc_emails:
            parsed_c = cls.clean_sender(c)[0]
            if parsed_c:
                cleaned_cc.append(parsed_c)
                if target in parsed_c:
                    has_formacion = True

        return cleaned_cc, has_formacion

    @classmethod
    def normalize_attachment(cls, raw: RawAttachmentInput) -> NormalizedAttachment:
        """Valida, calcula hash SHA-256 e infiere MIME type del adjunto."""
        filename = Path(raw.filename).name.strip()
        ext = Path(filename).suffix.lower()

        # Determinar MIME type si no viene o es genérico
        mime = raw.mime_type or MIME_TYPE_MAP.get(ext, "application/octet-stream")
        if mime == "application/octet-stream" and ext in MIME_TYPE_MAP:
            mime = MIME_TYPE_MAP[ext]

        # Validar y decodificar Base64
        error = None
        byte_len = 0
        sha256 = ""
        is_valid = True

        try:
            # Aceptar base64url o base64 estándar con o sin relleno
            padded = raw.data_base64 + "=" * (-len(raw.data_base64) % 4)
            data_bytes = base64.b64decode(padded, altchars="-_" if "-" in raw.data_base64 else None)
            byte_len = len(data_bytes)
            sha256 = hashlib.sha256(data_bytes).hexdigest()
        except Exception as e:
            is_valid = False
            error = f"Error decodificando base64: {str(e)}"
            sha256 = hashlib.sha256(raw.data_base64.encode("utf-8")).hexdigest()

        if is_valid:
            # Validar tamaño máximo
            if byte_len > settings.MAX_ATTACHMENT_SIZE_BYTES:
                is_valid = False
                error = f"Adjunto excede el tamaño máximo permitido ({settings.MAX_ATTACHMENT_SIZE_BYTES // (1024*1024)}MB)"

            # Validar extensiones permitidas para evidencias oficiales
            if ext not in settings.ALLOWED_ATTACHMENT_EXTENSIONS:
                is_valid = False
                error = f"Extensión no permitida '{ext}'. Formatos admitidos: {', '.join(settings.ALLOWED_ATTACHMENT_EXTENSIONS)}"

        return NormalizedAttachment(
            filename=filename,
            mime_type=mime,
            size_bytes=byte_len or (raw.size_bytes or 0),
            sha256_hash=sha256,
            data_base64=raw.data_base64,
            is_valid_evidence=is_valid,
            validation_error=error
        )

    @classmethod
    def extract_preliminary_data(cls, text: str, subject: str) -> PreliminaryExtraction:
        """
        Extrae heurísticamente:
        1. Cédula del coder (7 a 10 dígitos)
        2. Fechas de inasistencia (formato numérico o textual)
        3. Clan y jornada
        4. Motivo presunto según los 10 motivos de la Presentación PPTX
        5. Detección de casos de salud mental / confidenciales sensibles
        """
        full_content = f"{subject}\n{text}"

        # 1. Cédula (7 a 10 dígitos con prefijo opcional cc, id, cedula, documento)
        detected_cedula = None
        cedula_match = re.search(r"(?:c[ée]dula|cc|doc(?:umento)?|id)?[:\s#]*\b(\d{7,10})\b", full_content, flags=re.IGNORECASE)
        if cedula_match:
            detected_cedula = cedula_match.group(1)

        # 2. Fechas (YYYY-MM-DD o DD/MM/YYYY o DD-MM-YYYY)
        dates_found = re.findall(r"\b(?:\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\b", full_content)
        unique_dates = list(dict.fromkeys(dates_found))
        start_date = unique_dates[0] if unique_dates else None
        end_date = unique_dates[1] if len(unique_dates) > 1 else start_date

        # 3. Clan
        detected_clan = None
        for clan in KNOWN_CLANS:
            if re.search(r"\b" + clan + r"\b", full_content, flags=re.IGNORECASE):
                detected_clan = f"Clan {clan.capitalize()}"
                break
        if not detected_clan:
            clan_gen_match = re.search(r"\bclan\s+([a-zA-Z0-9_\-]+)\b", full_content, flags=re.IGNORECASE)
            if clan_gen_match:
                detected_clan = f"Clan {clan_gen_match.group(1).capitalize()}"

        # 4. Jornada (Mañana / Tarde)
        detected_shift = None
        if re.search(r"\b(?:mañana|morn(?:ing)?|6\s*:\s*00|am)\b", full_content, flags=re.IGNORECASE):
            detected_shift = "Mañana (6:00 AM - 2:00 PM)"
        elif re.search(r"\b(?:tarde|afternoon|pm|2\s*:\s*00)\b", full_content, flags=re.IGNORECASE):
            detected_shift = "Tarde (2:00 PM - 10:00 PM)"

        # 5. Motivo presunto (Catálogo de 10 del PPTX)
        suspected_motive = "falta_injustificada"
        for motive, patterns in OFFICIAL_MOTIVES_KEYWORDS.items():
            for pat in patterns:
                if re.search(pat, full_content, flags=re.IGNORECASE):
                    suspected_motive = motive
                    break
            if suspected_motive != "falta_injustificada":
                break

        # 6. Sensibilidad (Slide 5 PPTX: 'Si contiene información que se considera sensible, remitir a HSE')
        is_sensitive = suspected_motive == "situacion_emocional_critica" or bool(
            re.search(r"\b(?:psic[oó]log|psiquiatr|crisis de p[aá]nico|depresi[oó]n grave|fallecimiento|violencia|abuso)\b", full_content, flags=re.IGNORECASE)
        )

        return PreliminaryExtraction(
            detected_cedula=detected_cedula,
            detected_dates=unique_dates,
            detected_start_date=start_date,
            detected_end_date=end_date,
            detected_clan=detected_clan,
            detected_shift=detected_shift,
            suspected_motive=suspected_motive,
            is_sensitive=is_sensitive
        )

    def normalize(self, raw: RawEmailInput) -> NormalizedEmail:
        """
        Ejecuta el pipeline completo de normalización para una entrada de correo.
        """
        # Identificador único de mensaje
        message_id = raw.message_id or f"riwi-msg-{uuid.uuid4()}"

        # Remitente
        clean_email, clean_name = self.clean_sender(raw.sender_email, raw.sender_name)

        # Destinatarios y copia oficial
        clean_recipient = self.clean_sender(raw.recipient_email)[0] if raw.recipient_email else None
        clean_cc, has_formacion_cc = self.check_formacion_cc(clean_recipient, raw.cc_emails or [])

        # Asunto
        raw_sub, clean_sub = self.clean_subject(raw.subject)

        # Cuerpo
        cleaned_body = self.clean_html_and_text(raw.body)

        # Fecha de recepción
        if isinstance(raw.received_at, datetime):
            recv_at = raw.received_at
        elif isinstance(raw.received_at, str):
            try:
                recv_at = datetime.fromisoformat(raw.received_at.replace("Z", "+00:00"))
            except Exception:
                recv_at = datetime.now(timezone.utc)
        else:
            recv_at = datetime.now(timezone.utc)

        # Adjuntos
        normalized_attachments = [
            self.normalize_attachment(att) for att in (raw.attachments or [])
        ]

        # Extracción preliminar guiada por las reglas del PPTX
        preliminary = self.extract_preliminary_data(cleaned_body, clean_sub)

        return NormalizedEmail(
            source_provider=raw.source_provider.upper(),
            message_id=message_id,
            conversation_id=raw.conversation_id,
            sender_email=clean_email,
            sender_name=clean_name,
            recipient_email=clean_recipient,
            cc_emails=clean_cc,
            has_formacion_cc=has_formacion_cc,
            subject=raw_sub,
            clean_subject=clean_sub,
            raw_body=raw.body,
            cleaned_body=cleaned_body,
            received_at=recv_at,
            attachments=normalized_attachments,
            preliminary_extraction=preliminary
        )

    def ingest(self, raw: RawEmailInput) -> EmailIngestResponse:
        """
        Punto de entrada de ingestión. Devuelve el payload canónico con advertencias operativas.
        """
        normalized = self.normalize(raw)
        warnings: List[str] = []

        if not normalized.has_formacion_cc:
            warnings.append(
                f"Protocolo Riwi (Slide 5 PPTX): El correo no incluyó copia a {settings.FORMACION_EMAIL_OFFICIAL}."
            )

        if not normalized.preliminary_extraction.detected_cedula:
            warnings.append(
                "Información mínima (Slide 4 PPTX): No se detectó número de cédula en el asunto o cuerpo del mensaje."
            )

        if normalized.preliminary_extraction.is_sensitive:
            warnings.append(
                "Tratamiento Sensible (Slide 5 PPTX): Caso clasificado con contenido sensible/emocional. Derivación inmediata a HSE."
            )

        for att in normalized.attachments:
            if not att.is_valid_evidence:
                warnings.append(f"Adjunto '{att.filename}' no válido como evidencia: {att.validation_error}")

        status = "warning" if warnings else "success"
        ingestion_id = f"ingest-{uuid.uuid4()}"

        return EmailIngestResponse(
            status=status,
            ingestion_id=ingestion_id,
            normalized_email=normalized,
            warnings=warnings,
            processed_at=datetime.now(timezone.utc)
        )


email_normalizer = EmailNormalizationService()
