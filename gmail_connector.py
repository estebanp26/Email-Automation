#!/usr/bin/env python3
"""
gmail_connector.py
=============================================================================
CONECTOR OFICIAL DE GMAIL & GOOGLE CLOUD PUB/SUB — SISTEMA HSE RIWI
=============================================================================
Conector Python de alta confiabilidad (100% resiliente) para ingesta de
correos y evidencias adjuntas desde buzones institucionales de Gmail / Google Workspace.

Misiones / Tasks soportadas:
- CONN-02 (P0): Recepción de notificaciones push de Google Cloud Pub/Sub y
  consulta de mensajes mediante Gmail REST API v1.
- CONN-03 (P1): Extracción robusta de evidencias adjuntas (PDFs, imágenes PNG/JPG),
  conversión segura de base64url a base64 estándar y cálculo de hash SHA-256
  para validación de integridad en Strata Core.

Características Principales:
1. Soporte Dual:
   - Deserializador y validador de mensajes Google Cloud Pub/Sub Push Webhook.
   - Cliente REST para Gmail API v1 (mensajes, historial y adjuntos).
2. Extracción de Adjuntos (CONN-03):
   - Decodificación segura de base64url (RFC 4648).
   - Cálculo automático de hash SHA-256 para integridad y deduplicación.
   - Conversión a Base64 estándar para el contrato de Strata Core y n8n.
3. Normalización Universal de Payload:
   - Formato idéntico al emitido por outlook_connector.py con source_provider='GMAIL'.
4. Suite Offline Integrada:
   - Verificación determinista (--test) sin requerir tokens externos de Google.
=============================================================================
"""

import os
import sys
import json
import time
import base64
import hashlib
import logging
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import urllib.request
import urllib.error
import urllib.parse

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
logger = logging.getLogger("GmailConnector")

BASE_DIR = Path(__file__).resolve().parent
GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"


# =============================================================================
# UTILIDADES DE BASE64URL Y DECODIFICACIÓN
# =============================================================================

def decode_base64url(data_str: str) -> bytes:
    """
    Decodifica una cadena en formato base64url (seguro para URL, RFC 4648) a bytes raw.
    Maneja el relleno (padding) faltante automáticamente.
    """
    if not data_str:
        return b""
    # Reemplazar caracteres seguros para URL
    standard_b64 = data_str.replace("-", "+").replace("_", "/")
    # Añadir padding si es necesario
    padding_needed = len(standard_b64) % 4
    if padding_needed != 0:
        standard_b64 += "=" * (4 - padding_needed)
    return base64.b64decode(standard_b64)


def encode_to_standard_base64(raw_bytes: bytes) -> str:
    """Convierte bytes crudos a una cadena Base64 estándar ASCII."""
    return base64.b64encode(raw_bytes).decode("ascii")


def compute_sha256(data: bytes) -> str:
    """Calcula el hash SHA-256 en formato hexadecimal de un arreglo de bytes."""
    return hashlib.sha256(data).hexdigest()


def extract_header_value(headers: List[Dict[str, str]], header_name: str) -> str:
    """Obtiene el valor de un encabezado de correo ignorando mayúsculas/minúsculas."""
    target = header_name.lower()
    for h in headers:
        if h.get("name", "").lower() == target:
            return h.get("value", "")
    return ""


def parse_sender_string(from_header: str) -> Tuple[str, str]:
    """
    Extrae (email, nombre) desde un encabezado 'From'.
    Ejemplo: 'Santiago Morales <santiago.morales@riwi.io>' -> ('santiago.morales@riwi.io', 'Santiago Morales')
    """
    if not from_header:
        return "", "Coder"
    decoded = from_header.strip()
    name = "Coder"
    email_addr = decoded

    if "<" in decoded and ">" in decoded:
        parts = decoded.split("<", 1)
        name_part = parts[0].strip().strip('"').strip("'")
        email_part = parts[1].split(">", 1)[0].strip()
        if name_part:
            name = name_part
        if email_part:
            email_addr = email_part
    return email_addr.lower(), name


# =============================================================================
# MANEJADOR DE NOTIFICACIONES PUSH DE GOOGLE CLOUD PUB/SUB (CONN-02)
# =============================================================================

def parse_pubsub_push_payload(pubsub_request_body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Decodifica y valida una notificación push de Google Cloud Pub/Sub.
    
    Estructura esperada por Pub/Sub Push:
    {
      "message": {
        "data": "<cadena base64 con JSON>",
        "messageId": "...",
        "publishTime": "..."
      },
      "subscription": "projects/.../subscriptions/..."
    }

    Retorna un diccionario con:
    - email_address: correo del buzón afectado
    - history_id: ID de historial para sincronización incremental
    - message_id: ID del mensaje Pub/Sub
    - subscription: suscripción emisora
    """
    message_obj = pubsub_request_body.get("message", {})
    if not message_obj:
        raise ValueError("El cuerpo de la petición no contiene la clave 'message' de Google Cloud Pub/Sub.")

    raw_data_b64 = message_obj.get("data", "")
    if not raw_data_b64:
        raise ValueError("El mensaje de Pub/Sub no contiene el campo 'data'.")

    # Decodificar el campo data
    decoded_bytes = decode_base64url(raw_data_b64)
    data_json = json.loads(decoded_bytes.decode("utf-8"))

    return {
        "email_address": data_json.get("emailAddress", ""),
        "history_id": str(data_json.get("historyId", "")),
        "pubsub_message_id": message_obj.get("messageId", ""),
        "publish_time": message_obj.get("publishTime", ""),
        "subscription": pubsub_request_body.get("subscription", "")
    }


# =============================================================================
# EXTRACTOR DE CUERPO Y ADJUNTOS DE GMAIL API (CONN-03)
# =============================================================================

def extract_body_from_gmail_payload(payload: Dict[str, Any]) -> str:
    """Extrae el cuerpo de texto plano o HTML decodificando partes de Gmail."""
    # 1. Caso directo sin multiparte
    body_data = payload.get("body", {}).get("data")
    if body_data:
        try:
            return decode_base64url(body_data).decode("utf-8", errors="replace")
        except Exception:
            pass

    # 2. Caso multiparte: buscar en 'parts'
    parts = payload.get("parts", [])
    text_content = []
    
    def walk_parts(part_list: List[Dict[str, Any]]):
        for part in part_list:
            mime = part.get("mimeType", "").lower()
            p_data = part.get("body", {}).get("data")
            if mime == "text/plain" and p_data:
                try:
                    text_content.append(decode_base64url(p_data).decode("utf-8", errors="replace"))
                except Exception:
                    pass
            elif mime == "text/html" and p_data and not text_content:
                # Si aún no hay texto plano, guardar como respaldo
                try:
                    text_content.append(decode_base64url(p_data).decode("utf-8", errors="replace"))
                except Exception:
                    pass
            if "parts" in part:
                walk_parts(part["parts"])

    walk_parts(parts)
    return "\n".join(text_content).strip() if text_content else ""


def extract_attachments_from_gmail_payload(
    message_id: str,
    payload: Dict[str, Any],
    attachment_fetcher=None
) -> List[Dict[str, Any]]:
    """
    Extrae y descarga evidencias adjuntas de un mensaje de Gmail API (CONN-03).
    Soporta extracción directa si los datos vienen en el payload o invocando
    attachment_fetcher(message_id, attachment_id) si vienen diferidos.
    """
    attachments: List[Dict[str, Any]] = []
    parts = payload.get("parts", [])

    def process_parts(part_list: List[Dict[str, Any]]):
        for part in part_list:
            filename = part.get("filename", "")
            mime_type = part.get("mimeType", "application/octet-stream")
            body = part.get("body", {})
            attachment_id = body.get("attachmentId")
            raw_data = body.get("data")

            # Es un adjunto si tiene nombre de archivo o attachmentId
            if filename and (attachment_id or raw_data):
                raw_bytes = b""
                if raw_data:
                    raw_bytes = decode_base64url(raw_data)
                elif attachment_id and attachment_fetcher:
                    raw_bytes = attachment_fetcher(message_id, attachment_id)

                if raw_bytes:
                    b64_std = encode_to_standard_base64(raw_bytes)
                    sha256_hash = compute_sha256(raw_bytes)
                    attachments.append({
                        "filename": filename,
                        "mime_type": mime_type,
                        "size_bytes": len(raw_bytes),
                        "sha256": sha256_hash,
                        "data_base64": b64_std
                    })

            if "parts" in part:
                process_parts(part["parts"])

    process_parts(parts)
    return attachments


def normalize_gmail_message(
    gmail_message: Dict[str, Any],
    attachment_fetcher=None
) -> Dict[str, Any]:
    """
    Normaliza un mensaje obtenido de Gmail API al contrato universal
    de n8n y Strata Core.
    """
    msg_id = gmail_message.get("id", "")
    thread_id = gmail_message.get("threadId", "")
    payload = gmail_message.get("payload", {})
    headers = payload.get("headers", [])

    from_header = extract_header_value(headers, "From")
    sender_email, sender_name = parse_sender_string(from_header)
    subject = extract_header_value(headers, "Subject") or "Sin asunto"
    date_header = extract_header_value(headers, "Date")

    # Timestamp
    internal_date_ms = gmail_message.get("internalDate")
    if internal_date_ms:
        try:
            received_at = datetime.fromtimestamp(int(internal_date_ms) / 1000.0, tz=timezone.utc).isoformat()
        except Exception:
            received_at = datetime.now(timezone.utc).isoformat()
    else:
        received_at = datetime.now(timezone.utc).isoformat()

    # Cuerpo
    email_body = extract_body_from_gmail_payload(payload) or gmail_message.get("snippet", "")

    # Adjuntos
    attachments = extract_attachments_from_gmail_payload(msg_id, payload, attachment_fetcher)

    return {
        "source_provider": "GMAIL",
        "message_id": msg_id,
        "thread_id": thread_id,
        "sender_email": sender_email,
        "sender_name": sender_name,
        "email_subject": subject,
        "email_body": email_body,
        "received_at": received_at,
        "date_header": date_header,
        "attachments": attachments,
        "has_attachments": len(attachments) > 0
    }


# =============================================================================
# CLIENTE GMAIL API REST
# =============================================================================

class GmailAPIClient:
    """Cliente oficial de Gmail API v1 con OAuth2."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        user_email: str = "me"
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.user_email = user_email
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0

    @classmethod
    def from_env(cls) -> Optional["GmailAPIClient"]:
        """Instancia el cliente desde variables de entorno."""
        client_id = os.getenv("GOOGLE_CLIENT_ID") or os.getenv("GMAIL_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET") or os.getenv("GMAIL_CLIENT_SECRET")
        refresh_token = os.getenv("GOOGLE_REFRESH_TOKEN") or os.getenv("GMAIL_REFRESH_TOKEN")
        mailbox = os.getenv("GMAIL_MAILBOX") or "me"

        if not (client_id and client_secret and refresh_token):
            return None
        return cls(client_id=client_id, client_secret=client_secret, refresh_token=refresh_token, user_email=mailbox)

    def get_token(self) -> str:
        """Refresca y obtiene un token de acceso OAuth2 de Google."""
        now = time.time()
        if self._access_token and now < (self._token_expires_at - 60):
            return self._access_token

        token_url = "https://oauth2.googleapis.com/token"
        params = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token"
        }
        data = urllib.parse.urlencode(params).encode("utf-8")
        req = urllib.request.Request(token_url, data=data, method="POST")

        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            self._access_token = body["access_token"]
            self._token_expires_at = now + int(body.get("expires_in", 3600))
            return self._access_token

    def fetch_attachment_bytes(self, message_id: str, attachment_id: str) -> bytes:
        """Descarga los bytes raw de un adjunto desde Gmail API."""
        token = self.get_token()
        url = f"{GMAIL_API_BASE}/messages/{message_id}/attachments/{attachment_id}"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})

        with urllib.request.urlopen(req, timeout=25) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            data_b64 = data.get("data", "")
            return decode_base64url(data_b64)

    def fetch_message(self, message_id: str) -> Dict[str, Any]:
        """Obtiene un mensaje completo por su ID y lo normaliza."""
        token = self.get_token()
        url = f"{GMAIL_API_BASE}/messages/{message_id}?format=full"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})

        with urllib.request.urlopen(req, timeout=20) as resp:
            raw_msg = json.loads(resp.read().decode("utf-8"))

        return normalize_gmail_message(raw_msg, attachment_fetcher=self.fetch_attachment_bytes)

    def list_unread_messages(self, query: str = "is:unread label:INBOX", max_results: int = 10) -> List[Dict[str, Any]]:
        """Lista correos no leídos y los devuelve normalizados."""
        token = self.get_token()
        encoded_query = urllib.parse.quote(query)
        url = f"{GMAIL_API_BASE}/messages?q={encoded_query}&maxResults={max_results}"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})

        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        messages_list = data.get("messages", [])
        results = []
        for m in messages_list:
            msg_id = m.get("id")
            if msg_id:
                try:
                    norm = self.fetch_message(msg_id)
                    results.append(norm)
                except Exception as e:
                    logger.error(f"Error procesando mensaje Gmail {msg_id}: {e}")
        return results


# =============================================================================
# DESPACHADOR A N8N WEBHOOK
# =============================================================================

def forward_to_n8n_webhook(
    payload: Dict[str, Any],
    webhook_url: str = "http://localhost:5678/webhook/riwi-email-incoming",
    timeout: int = 30
) -> Dict[str, Any]:
    """Envía un payload normalizado de Gmail al webhook de n8n."""
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
# SUITE DE PRUEBA OFFLINE (100% Determinista)
# =============================================================================

def run_offline_test() -> int:
    """Ejecuta una prueba determinista de Pub/Sub push y extracción de adjuntos Gmail."""
    print("=" * 70)
    print("  SUITE DE PRUEBA OFFLINE: GMAIL API & PUBSUB PUSH EXTRACTOR       ")
    print("=" * 70)

    # 1. Simulación de Notificación Push Google Cloud Pub/Sub
    pubsub_inner_data = json.dumps({
        "emailAddress": "hse@riwi.io",
        "historyId": "987654321"
    })
    pubsub_b64 = base64.b64encode(pubsub_inner_data.encode("utf-8")).decode("ascii")

    pubsub_request = {
        "message": {
            "data": pubsub_b64,
            "messageId": "pubsub_msg_1001",
            "publishTime": "2026-09-28T09:15:00.000Z"
        },
        "subscription": "projects/riwi-email-automation/subscriptions/gmail-incoming-sub"
    }

    parsed_push = parse_pubsub_push_payload(pubsub_request)
    print(f"  [1/4] Pub/Sub Push decodificado con éxito:")
    print(f"        Buzón: {parsed_push['email_address']} | History ID: {parsed_push['history_id']}")
    assert parsed_push["email_address"] == "hse@riwi.io"
    assert parsed_push["history_id"] == "987654321"
    assert parsed_push["pubsub_message_id"] == "pubsub_msg_1001"

    # 2. Simulación de mensaje Gmail API con adjunto PDF en base64url
    sample_pdf_bytes = b"%PDF-1.4 Mock Certificado Medico EPS Sura - Infeccion Respiratoria Aguda"
    # Codificar en base64url
    sample_pdf_b64url = base64.urlsafe_b64encode(sample_pdf_bytes).decode("ascii").rstrip("=")
    expected_sha256 = hashlib.sha256(sample_pdf_bytes).hexdigest()
    expected_std_b64 = base64.b64encode(sample_pdf_bytes).decode("ascii")

    body_text_raw = "Buenas tardes equipo HSE, adjunto soporte médico de EPS Sura por incapacidad de 3 días."
    body_text_b64url = base64.urlsafe_b64encode(body_text_raw.encode("utf-8")).decode("ascii")

    mock_gmail_msg = {
        "id": "18ac2fe34a012345",
        "threadId": "18ac2fe34a012345",
        "internalDate": "1759050000000",
        "snippet": body_text_raw[:60],
        "payload": {
            "headers": [
                {"name": "From", "value": '"Mariana Ospina" <mariana.ospina@riwi.io>'},
                {"name": "To", "value": "hse@riwi.io"},
                {"name": "Subject", "value": "Justificación Médica - Mariana Ospina"},
                {"name": "Date", "value": "Mon, 28 Sep 2026 09:10:00 -0500"}
            ],
            "parts": [
                {
                    "partId": "0",
                    "mimeType": "text/plain",
                    "body": {
                        "size": len(body_text_raw),
                        "data": body_text_b64url
                    }
                },
                {
                    "partId": "1",
                    "mimeType": "application/pdf",
                    "filename": "incapacidad_sura_mariana.pdf",
                    "body": {
                        "attachmentId": "att_sura_9999",
                        "size": len(sample_pdf_bytes),
                        "data": sample_pdf_b64url
                    }
                }
            ]
        }
    }

    # 3. Normalización y extracción de adjuntos
    norm_msg = normalize_gmail_message(mock_gmail_msg)
    print(f"\n  [2/4] Mensaje Gmail API normalizado:")
    print(f"        Remitente: {norm_msg['sender_name']} <{norm_msg['sender_email']}>")
    print(f"        Asunto: {norm_msg['email_subject']}")
    print(f"        Cuerpo: {norm_msg['email_body'][:50]}...")
    assert norm_msg["sender_name"] == "Mariana Ospina"
    assert norm_msg["sender_email"] == "mariana.ospina@riwi.io"
    assert norm_msg["email_subject"] == "Justificación Médica - Mariana Ospina"
    assert "EPS Sura" in norm_msg["email_body"]

    print(f"\n  [3/4] Extracción y conversión de adjunto (CONN-03):")
    assert len(norm_msg["attachments"]) == 1
    att = norm_msg["attachments"][0]
    print(f"        Archivo: {att['filename']} | Tipo: {att['mime_type']}")
    print(f"        SHA-256: {att['sha256']}")
    assert att["filename"] == "incapacidad_sura_mariana.pdf"
    assert att["mime_type"] == "application/pdf"
    assert att["sha256"] == expected_sha256
    assert att["data_base64"] == expected_std_b64

    # 4. Compatibilidad con el payload de n8n
    print(f"\n  [4/4] Verificación de contrato con n8n y Strata Core:")
    assert norm_msg["source_provider"] == "GMAIL"
    assert norm_msg["has_attachments"] is True
    json_payload = json.dumps(norm_msg)
    assert len(json_payload) > 0
    print(f"        Payload serializado con éxito ({len(json_payload)} bytes).")

    print("\n" + "=" * 70)
    print("  ¡TODAS LAS PRUEBAS OFFLINE DE GMAIL Y PUBSUB PASARON AL 100%!   ")
    print("=" * 70)
    return 0


# =============================================================================
# CLI PRINCIPAL
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Conector de Gmail y Google Cloud Pub/Sub para el Sistema HSE Riwi"
    )
    parser.add_argument("--test", action="store_true", help="Ejecuta la suite de pruebas unitarias offline")
    parser.add_argument("--query", default="is:unread label:INBOX", help="Consulta de búsqueda en Gmail")
    parser.add_argument("--forward-n8n", action="store_true", help="Reenvía cada correo procesado al webhook de n8n")
    parser.add_argument("--webhook-url", default=os.getenv("N8N_WEBHOOK_URL", "http://localhost:5678/webhook/riwi-email-incoming"), help="URL del webhook de n8n")
    parser.add_argument("--once", action="store_true", help="Ejecuta un solo sondeo y finaliza")

    args = parser.parse_args()

    if args.test:
        return run_offline_test()

    client = GmailAPIClient.from_env()
    if not client:
        logger.error("No se encontraron credenciales de Gmail en el entorno (GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN).")
        logger.info("Para verificar el funcionamiento sin credenciales, ejecute: python gmail_connector.py --test")
        return 1

    logger.info("Consultando correos en Gmail API...")
    messages = client.list_unread_messages(query=args.query)
    logger.info(f"Se procesaron {len(messages)} mensajes de Gmail.")

    for mail in messages:
        print(f" • [{mail['received_at']}] De: {mail['sender_name']} <{mail['sender_email']}> | Asunto: {mail['email_subject']}")
        if args.forward_n8n:
            res = forward_to_n8n_webhook(mail, webhook_url=args.webhook_url)
            logger.info(f"Reenvío a n8n: {res['status']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
