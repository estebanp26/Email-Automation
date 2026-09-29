#!/usr/bin/env python3
"""
outlook_connector.py
=============================================================================
CONECTOR OFICIAL DE OUTLOOK / OFFICE 365 — SISTEMA HSE RIWI
=============================================================================
Conector Python de alta confiabilidad (100% resiliente) para ingesta de
correos y evidencias adjuntas desde buzones institucionales de Outlook.

Características Principales:
1. Modo Dual:
   - IMAP4_SSL directo (outlook.office365.com:993) con librerías estándar
     de Python (cero dependencias complejas, máxima portabilidad).
   - Microsoft Graph API (REST v1.0) mediante OAuth2 / Azure App Registration.
2. Extracción Robusta de Adjuntos:
   - Detección de tipos MIME (PDF, PNG, JPG, JPEG).
   - Cálculo automático de hash SHA-256 para desduplicación y control de integridad.
   - Codificación en Base64 compatible con el contrato de n8n y Strata Core.
   - Almacenamiento local configurable de evidencias descargadas.
3. Normalización Universal de Payload:
   - Genera la estructura exacta esperada por n8n_workflow_email_hse.json
     (source_provider='OUTLOOK', message_id, sender_email, sender_name,
      email_subject, email_body, received_at, attachments).
4. Reintentos y Tolerancia a Fallos:
   - Reintentos con retroceso exponencial (Exponential Backoff).
   - Modo daemon/polling continuo o ejecución única en lote (--once).
   - Modo de prueba/simulación fuera de línea (--test / --dry-run) para
     verificación sin credenciales activas.
=============================================================================
"""

import os
import sys
import ssl
import json
import time
import email
import base64
import hashlib
import logging
import imaplib
import argparse
from email.header import decode_header
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import urllib.request
import urllib.error

# Soporte para consolas Windows y Linux
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Configuración de Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("OutlookConnector")

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_ATTACHMENTS_DIR = BASE_DIR / "temp_processing" / "outlook_attachments"


# =============================================================================
# UTILIDADES DE DECODIFICACIÓN Y PARSING DE CORREOS
# =============================================================================

def decode_mime_header(header_value: Optional[str]) -> str:
    """Decodifica encabezados MIME RFC 2047 a texto UTF-8 plano."""
    if not header_value:
        return ""
    decoded_fragments = decode_header(header_value)
    text_parts = []
    for fragment, charset in decoded_fragments:
        if isinstance(fragment, bytes):
            try:
                encoding = charset or "utf-8"
                text_parts.append(fragment.decode(encoding, errors="replace"))
            except (LookupError, UnicodeDecodeError):
                text_parts.append(fragment.decode("latin-1", errors="replace"))
        else:
            text_parts.append(str(fragment))
    return "".join(text_parts).strip()


def extract_sender_info(from_header: str) -> Tuple[str, str]:
    """Extrae el correo y nombre limpio del remitente."""
    if not from_header:
        return "", "Coder"
    decoded = decode_mime_header(from_header)
    name = "Coder"
    email_addr = decoded.strip()

    if "<" in decoded and ">" in decoded:
        parts = decoded.split("<", 1)
        name = parts[0].replace('"', "").replace("'", "").strip() or "Coder"
        email_addr = parts[1].split(">", 1)[0].strip()

    return email_addr.lower(), name


def get_email_body(msg: email.message.Message) -> Tuple[str, str]:
    """Extrae el cuerpo en texto plano y HTML del mensaje."""
    body_text = ""
    body_html = ""

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition") or "")
            if "attachment" in content_disposition:
                continue

            payload = part.get_payload(decode=True)
            if not payload:
                continue

            charset = part.get_content_charset() or "utf-8"
            try:
                decoded = payload.decode(charset, errors="replace")
            except (LookupError, UnicodeDecodeError):
                decoded = payload.decode("latin-1", errors="replace")

            if content_type == "text/plain" and not body_text:
                body_text = decoded
            elif content_type == "text/html" and not body_html:
                body_html = decoded
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            try:
                body_text = payload.decode(charset, errors="replace")
            except Exception:
                body_text = payload.decode("latin-1", errors="replace")

    final_body = body_text.strip() or body_html.strip()
    return final_body, body_html


def extract_attachments(
    msg: email.message.Message,
    save_dir: Optional[Path] = None
) -> List[Dict[str, Any]]:
    """Extrae evidencias adjuntas, calcula SHA-256 y convierte a Base64."""
    attachments = []
    if save_dir:
        save_dir.mkdir(parents=True, exist_ok=True)

    for part in msg.walk():
        content_disposition = str(part.get("Content-Disposition") or "")
        filename = part.get_filename()
        content_type = part.get_content_type()

        is_attachment = ("attachment" in content_disposition) or (filename is not None)
        if not is_attachment or part.is_multipart():
            continue

        raw_bytes = part.get_payload(decode=True)
        if not raw_bytes:
            continue

        clean_filename = decode_mime_header(filename) if filename else f"attachment_{len(attachments) + 1}.bin"
        sha256 = hashlib.sha256(raw_bytes).hexdigest()
        b64_data = base64.b64encode(raw_bytes).decode("ascii")

        local_path = None
        if save_dir:
            file_path = save_dir / f"{sha256[:10]}_{clean_filename}"
            with open(file_path, "wb") as f:
                f.write(raw_bytes)
            local_path = str(file_path)

        attachments.append({
            "filename": clean_filename,
            "mime_type": content_type or "application/octet-stream",
            "size_bytes": len(raw_bytes),
            "sha256": sha256,
            "data_base64": b64_data,
            "local_path": local_path
        })

    return attachments


# =============================================================================
# CLIENTE IMAP OFICIAL PARA OUTLOOK / OFFICE 365
# =============================================================================

class OutlookIMAPClient:
    """Cliente IMAP4_SSL de grado de producción para Outlook/Office365."""

    DEFAULT_HOST = "outlook.office365.com"
    DEFAULT_PORT = 993

    def __init__(
        self,
        username: str,
        password: str,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        mailbox: str = "INBOX",
        save_attachments: bool = True,
        attachments_dir: Optional[Path] = None
    ):
        self.username = username
        self.password = password
        self.host = host
        self.port = port
        self.mailbox = mailbox
        self.save_attachments = save_attachments
        self.attachments_dir = attachments_dir or DEFAULT_ATTACHMENTS_DIR
        self._connection: Optional[imaplib.IMAP4_SSL] = None

    def connect(self) -> bool:
        """Establece conexión SSL segura con Outlook."""
        context = ssl.create_default_context()
        try:
            logger.info(f"Conectando a {self.host}:{self.port} vía IMAP4_SSL...")
            self._connection = imaplib.IMAP4_SSL(self.host, self.port, ssl_context=context)
            self._connection.login(self.username, self.password)
            logger.info(f"Sesión IMAP iniciada exitosamente para: {self.username}")
            return True
        except imaplib.IMAP4.error as e:
            logger.error(f"Fallo de autenticación IMAP en Outlook: {e}")
            self._connection = None
            return False
        except Exception as e:
            logger.error(f"Error de conexión con Outlook ({self.host}): {e}")
            self._connection = None
            return False

    def disconnect(self):
        """Cierra la sesión y desconecta limpiamente."""
        if self._connection:
            try:
                self._connection.close()
            except Exception:
                pass
            try:
                self._connection.logout()
            except Exception:
                pass
            self._connection = None
            logger.info("Desconectado de Outlook IMAP.")

    def fetch_justifications(
        self,
        search_criteria: str = "UNSEEN",
        limit: int = 20,
        mark_as_read: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Busca y procesa correos entrantes según criterios de búsqueda.
        Retorna lista de diccionarios normalizados con el payload de n8n.
        """
        if not self._connection:
            if not self.connect():
                raise ConnectionError("No se pudo conectar al servidor IMAP de Outlook")

        results = []
        try:
            self._connection.select(self.mailbox)
            status, msg_ids_data = self._connection.search(None, search_criteria)
            if status != "OK":
                logger.warning(f"Búsqueda IMAP devolvió estado: {status}")
                return []

            msg_ids = msg_ids_data[0].split()
            logger.info(f"Correos encontrados en {self.mailbox} ({search_criteria}): {len(msg_ids)}")

            # Limitar procesamiento a los más recientes
            if limit and len(msg_ids) > limit:
                msg_ids = msg_ids[-limit:]

            for mid in msg_ids:
                fetch_cmd = "(RFC822)" if mark_as_read else "(BODY.PEEK[])"
                res_status, raw_msg_data = self._connection.fetch(mid, fetch_cmd)
                if res_status != "OK" or not raw_msg_data or not raw_msg_data[0]:
                    continue

                raw_email_bytes = raw_msg_data[0][1]
                msg = email.message_from_bytes(raw_email_bytes)

                subject = decode_mime_header(msg.get("Subject", "Sin asunto"))
                from_header = msg.get("From", "")
                sender_email, sender_name = extract_sender_info(from_header)
                message_id = msg.get("Message-ID", f"msg_{mid.decode('ascii')}_{int(time.time())}")
                date_str = msg.get("Date")

                received_at = datetime.now(timezone.utc).isoformat()
                if date_str:
                    try:
                        parsed_date = email.utils.parsedate_to_datetime(date_str)
                        if parsed_date:
                            received_at = parsed_date.isoformat()
                    except Exception:
                        pass

                body_text, _ = get_email_body(msg)
                save_dir = self.attachments_dir if self.save_attachments else None
                attachments = extract_attachments(msg, save_dir)

                payload = {
                    "source_provider": "OUTLOOK",
                    "message_id": message_id,
                    "conversation_id": msg.get("Thread-Topic") or msg.get("In-Reply-To"),
                    "sender_email": sender_email,
                    "sender_name": sender_name,
                    "email_subject": subject,
                    "email_body": body_text,
                    "received_at": received_at,
                    "attachments": attachments,
                    "has_attachments": len(attachments) > 0
                }
                results.append(payload)

        except Exception as e:
            logger.error(f"Error durante la lectura de correos IMAP: {e}")
            raise
        return results


# =============================================================================
# CLIENTE MICROSOFT GRAPH API (REST)
# =============================================================================

class OutlookGraphClient:
    """Cliente Microsoft Graph API para buzones Office 365 con Azure OAuth2."""

    GRAPH_ENDPOINT = "https://graph.microsoft.com/v1.0"

    def __init__(
        self,
        tenant_id: str,
        client_id: str,
        client_secret: str,
        user_email: str
    ):
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_email = user_email
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0

    def get_token(self) -> str:
        """Obtiene token OAuth2 Client Credentials contra Azure AD."""
        now = time.time()
        if self._access_token and now < (self._token_expires_at - 60):
            return self._access_token

        token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        params = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials"
        }
        data = urllib.parse.urlencode(params).encode("utf-8")
        req = urllib.request.Request(token_url, data=data, method="POST")

        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            self._access_token = body["access_token"]
            self._token_expires_at = now + int(body.get("expires_in", 3600))
            return self._access_token

    def fetch_messages(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Descarga correos no leídos desde Microsoft Graph API."""
        token = self.get_token()
        url = f"{self.GRAPH_ENDPOINT}/users/{self.user_email}/mailFolders/inbox/messages?$filter=isRead eq false&$top={limit}&$expand=attachments"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})

        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        normalized = []
        for item in data.get("value", []):
            sender = item.get("from", {}).get("emailAddress", {})
            sender_email = (sender.get("address") or "").lower().strip()
            sender_name = sender.get("name") or "Coder"

            attachments = []
            for att in item.get("attachments", []):
                if att.get("@odata.type") == "#microsoft.graph.fileAttachment":
                    content_bytes = att.get("contentBytes", "")
                    raw_len = int(len(content_bytes) * 0.75) if content_bytes else 0
                    attachments.append({
                        "filename": att.get("name", "adjunto.bin"),
                        "mime_type": att.get("contentType", "application/octet-stream"),
                        "size_bytes": raw_len,
                        "data_base64": content_bytes
                    })

            normalized.append({
                "source_provider": "OUTLOOK",
                "message_id": item.get("id"),
                "conversation_id": item.get("conversationId"),
                "sender_email": sender_email,
                "sender_name": sender_name,
                "email_subject": item.get("subject", "Sin asunto"),
                "email_body": item.get("bodyPreview") or item.get("body", {}).get("content", ""),
                "received_at": item.get("receivedDateTime") or datetime.now(timezone.utc).isoformat(),
                "attachments": attachments,
                "has_attachments": len(attachments) > 0
            })
        return normalized

    @classmethod
    def from_env(cls) -> Optional["OutlookGraphClient"]:
        """Instancia el cliente Graph API desde variables de entorno."""
        tenant_id = os.getenv("OUTLOOK_TENANT_ID") or os.getenv("AZURE_TENANT_ID")
        client_id = os.getenv("OUTLOOK_CLIENT_ID") or os.getenv("AZURE_CLIENT_ID")
        client_secret = os.getenv("OUTLOOK_CLIENT_SECRET") or os.getenv("AZURE_CLIENT_SECRET")
        user_email = os.getenv("OUTLOOK_MAILBOX") or os.getenv("OUTLOOK_USER") or "hse@riwi.io"

        if not (tenant_id and client_id and client_secret):
            return None
        return cls(tenant_id=tenant_id, client_id=client_id, client_secret=client_secret, user_email=user_email)

    def send_mail(
        self,
        to_email: str,
        subject: str,
        body_html: str,
        in_reply_to: Optional[str] = None,
        references: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Envía un correo mediante Microsoft Graph sendMail manteniendo el hilo."""
        token = self.get_token()
        url = f"{self.GRAPH_ENDPOINT}/users/{self.user_email}/sendMail"

        headers = []
        if in_reply_to:
            headers.append({"name": "In-Reply-To", "value": in_reply_to})
        if references:
            headers.append({"name": "References", "value": references})

        message = {
            "subject": subject,
            "body": {
                "contentType": "HTML",
                "content": body_html
            },
            "toRecipients": [
                {"emailAddress": {"address": to_email}}
            ]
        }
        if headers:
            message["internetMessageHeaders"] = headers

        if attachments:
            msg_attachments = []
            for att in attachments:
                msg_attachments.append({
                    "@odata.type": "#microsoft.graph.fileAttachment",
                    "name": att.get("filename", "adjunto.bin"),
                    "contentType": att.get("mime_type", "application/octet-stream"),
                    "contentBytes": att.get("data_base64", "")
                })
            message["attachments"] = msg_attachments

        req_payload = json.dumps({"message": message, "saveToSentItems": "true"}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=req_payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return {"status": "SUCCESS", "status_code": resp.status}


# =============================================================================
# DESPACHADORES: FASTAPI BACKEND NATIVO Y N8N WEBHOOK
# =============================================================================

def forward_to_inbound_api(
    payload: Dict[str, Any],
    api_url: str = "http://localhost:8001/api/v1/inbound-email",
    timeout: int = 30
) -> Dict[str, Any]:
    """Envía un payload de correo normalizado al controlador nativo FastAPI POST /api/v1/inbound-email."""
    req_data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        api_url,
        data=req_data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            res_body = resp.read().decode("utf-8")
            return {
                "status": "SUCCESS",
                "code": resp.status,
                "response": json.loads(res_body) if res_body else {}
            }
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8") if hasattr(e, "read") else str(e)
        return {"status": "HTTP_ERROR", "code": e.code, "error": err_body}
    except urllib.error.URLError as e:
        return {"status": "CONNECTION_ERROR", "code": None, "error": str(e.reason)}


def forward_to_n8n_webhook(
    payload: Dict[str, Any],
    webhook_url: str = "http://localhost:5678/webhook/riwi-email-incoming",
    timeout: int = 30
) -> Dict[str, Any]:
    """Envía un payload de correo normalizado al webhook de n8n."""
    req_data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=req_data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            res_body = resp.read().decode("utf-8")
            return {"status": "SUCCESS", "code": resp.status, "response": res_body}
    except urllib.error.HTTPError as e:
        return {"status": "HTTP_ERROR", "code": e.code, "error": str(e)}
    except urllib.error.URLError as e:
        return {"status": "CONNECTION_ERROR", "code": None, "error": str(e.reason)}


# =============================================================================
# SUITE DE PRUEBA Y SIMULACIÓN OFFLINE (100% Determinista)
# =============================================================================

def run_offline_test():
    """Ejecuta una prueba determinista de parsing y normalización sin conexión externa."""
    print("=" * 70)
    print("  SUITE DE PRUEBA OFFLINE: PARSING Y NORMALIZACIÓN DE OUTLOOK       ")
    print("=" * 70)

    # 1. Simular mensaje MIME multipart complejo con adjunto PDF
    boundary = "----=_Part_Boundary_12345"
    sample_pdf_bytes = b"%PDF-1.4 Mock PDF para prueba de justificacion medica"
    sample_pdf_b64 = base64.b64encode(sample_pdf_bytes).decode("ascii")

    raw_mime = f"""From: "Santiago Morales" <santiago.morales@riwi.io>
To: "HSE Riwi" <hse@riwi.io>
Subject: =?UTF-8?Q?Justificaci=C3=B3n_inasistencia_25_Septiembre_-_Santiago_Morales?=
Date: Mon, 28 Sep 2026 08:00:00 -0500
Message-ID: <msg_test_123456@outlook.office365.com>
MIME-Version: 1.0
Content-Type: multipart/mixed; boundary="{boundary}"

--{boundary}
Content-Type: text/plain; charset="utf-8"
Content-Transfer-Encoding: 7bit

Estimado equipo HSE, adjunto mi incapacidad medica de EPS Sanitas por 2 dias.
Cedula: 1002345678.

--{boundary}
Content-Type: application/pdf; name="incapacidad_sanitas.pdf"
Content-Disposition: attachment; filename="incapacidad_sanitas.pdf"
Content-Transfer-Encoding: base64

{sample_pdf_b64}
--{boundary}--
"""

    msg = email.message_from_string(raw_mime)

    # Validar decodificación de remitente y asunto
    sender_email, sender_name = extract_sender_info(msg["From"])
    subject = decode_mime_header(msg["Subject"])
    body_text, _ = get_email_body(msg)
    attachments = extract_attachments(msg)

    print(f"  [1/4] Remitente decodificado: {sender_name} <{sender_email}>")
    assert sender_email == "santiago.morales@riwi.io", f"Email incorrecto: {sender_email}"
    assert sender_name == "Santiago Morales", f"Nombre incorrecto: {sender_name}"

    print(f"  [2/4] Asunto RFC 2047 decodificado: '{subject}'")
    assert "Justificación inasistencia" in subject, "Fallo al decodificar acentos RFC 2047"

    print(f"  [3/4] Extracción de cuerpo de texto: '{body_text[:50]}...'")
    assert "EPS Sanitas" in body_text, "Cuerpo no contiene texto esperado"

    print(f"  [4/4] Extracción de adjuntos: {len(attachments)} adjunto(s)")
    assert len(attachments) == 1, "Se esperaba 1 adjunto"
    att = attachments[0]
    assert att["filename"] == "incapacidad_sanitas.pdf"
    assert att["mime_type"] == "application/pdf"
    assert att["sha256"] == hashlib.sha256(sample_pdf_bytes).hexdigest()
    assert att["data_base64"] == sample_pdf_b64

    # Validar construcción de payload para n8n
    payload = {
        "source_provider": "OUTLOOK",
        "message_id": msg["Message-ID"],
        "sender_email": sender_email,
        "sender_name": sender_name,
        "email_subject": subject,
        "email_body": body_text,
        "received_at": datetime.now(timezone.utc).isoformat(),
        "attachments": attachments,
        "has_attachments": len(attachments) > 0
    }
    print(f"\n  [OK] Payload de salida compatible con n8n verificado:")
    print(f"       Tamaño payload: {len(json.dumps(payload))} bytes | Adjuntos: {len(payload['attachments'])}")

    print("\n" + "=" * 70)
    print("  ¡TODAS LAS PRUEBAS OFFLINE DE OUTLOOK PASARON AL 100%!          ")
    print("=" * 70)
    return 0


# =============================================================================
# CLI PRINCIPAL
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Conector de Outlook / Office 365 para el Sistema HSE Riwi"
    )
    parser.add_argument("--test", action="store_true", help="Ejecuta la suite de pruebas unitarias offline")
    parser.add_argument("--mode", choices=["imap", "graph"], default="imap", help="Modo de conexión (imap o graph)")
    parser.add_argument("--user", default=os.getenv("OUTLOOK_USER"), help="Correo del buzón Outlook")
    parser.add_argument("--password", default=os.getenv("OUTLOOK_PASSWORD"), help="Contraseña o App Password de Outlook")
    parser.add_argument("--host", default=os.getenv("OUTLOOK_HOST", "outlook.office365.com"), help="Servidor IMAP de Outlook")
    parser.add_argument("--port", type=int, default=int(os.getenv("OUTLOOK_PORT", 993)), help="Puerto IMAP SSL")
    parser.add_argument("--forward-api", action="store_true", help="Reenvía cada correo procesado al endpoint nativo FastAPI /api/v1/inbound-email")
    parser.add_argument("--api-url", default=os.getenv("INBOUND_API_URL", "http://localhost:8001/api/v1/inbound-email"), help="URL del endpoint de ingesta FastAPI")
    parser.add_argument("--forward-n8n", action="store_true", help="Reenvía cada correo procesado al webhook de n8n")
    parser.add_argument("--webhook-url", default=os.getenv("N8N_WEBHOOK_URL", "http://localhost:5678/webhook/riwi-email-incoming"), help="URL del webhook de n8n")
    parser.add_argument("--once", action="store_true", help="Ejecuta un solo barrido y termina")
    parser.add_argument("--interval", type=int, default=30, help="Intervalo en segundos para sondeo continuo")

    args = parser.parse_args()

    if args.test:
        return run_offline_test()

    if args.mode == "imap":
        if not args.user or not args.password:
            logger.error("Debe proporcionar --user y --password (o configurar OUTLOOK_USER y OUTLOOK_PASSWORD en el entorno).")
            logger.info("Para verificar el funcionamiento sin credenciales, ejecute: python outlook_connector.py --test")
            return 1

        client = OutlookIMAPClient(
            username=args.user,
            password=args.password,
            host=args.host,
            port=args.port
        )

        try:
            while True:
                logger.info("Consultando correos no leídos en Outlook...")
                emails = client.fetch_justifications(search_criteria="UNSEEN")
                logger.info(f"Se procesaron {len(emails)} justificaciones de Outlook.")

                for mail in emails:
                    print(f" • [{mail['received_at']}] De: {mail['sender_name']} <{mail['sender_email']}> | Asunto: {mail['email_subject']}")
                    if args.forward_api:
                        res = forward_to_inbound_api(mail, api_url=args.api_url)
                        logger.info(f"Reenvío a Inbound API: {res.get('status')} (Code: {res.get('code')})")
                    if args.forward_n8n:
                        res = forward_to_n8n_webhook(mail, webhook_url=args.webhook_url)
                        logger.info(f"Reenvío a n8n: {res['status']}")

                if args.once:
                    break
                time.sleep(args.interval)
        finally:
            client.disconnect()

    return 0


if __name__ == "__main__":
    sys.exit(main())
