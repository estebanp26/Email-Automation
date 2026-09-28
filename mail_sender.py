#!/usr/bin/env python3
"""
mail_sender.py
=============================================================================
DESPACHADOR MULTI-PROVEEDOR DE CORREOS HSE (SMTP / GRAPH / GMAIL) — CONN-04
=============================================================================
Módulo de alta confiabilidad para emisión y respuesta formal de correos HSE.
Garantiza la trazabilidad en el mismo hilo de conversación del coder mediante
cabeceras RFC 2822: In-Reply-To, References y normalización de asunto 'Re: '.

Proveedores Soportados:
1. SMTP Estándar (STARTTLS o SSL) usando smtplib nativo.
2. Microsoft Graph API (POST /users/{id}/sendMail).
3. Gmail API v1 (POST /users/me/messages/send).

Plantillas Institucionales HSE:
- POSIBLEMENTE_VALIDO / APROBADO: Registro exitoso de contingencia.
- POSIBLEMENTE_INVALIDO / DENEGADO: Notificación fundamentada.
- REVISION_MANUAL / SOLICITAR_SOPORTE: Requerimiento de subsanación.
=============================================================================
"""

import os
import sys
import json
import base64
import smtplib
import argparse
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import Dict, Any, List, Optional
import urllib.request
import urllib.error

# Soporte para consolas Windows y Linux
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("MailSender")


# =============================================================================
# UTILIDADES DE CABECERAS Y NORMALIZACIÓN DE HILO
# =============================================================================

def format_reply_subject(original_subject: str) -> str:
    """Añade 'Re: ' al asunto si no lo tiene ya."""
    cleaned = (original_subject or "Justificación de Inasistencia").strip()
    if cleaned.lower().startswith("re:"):
        return cleaned
    return f"Re: {cleaned}"


def build_mime_message(
    sender_email: str,
    recipient_email: str,
    subject: str,
    body_text: str,
    body_html: Optional[str] = None,
    in_reply_to: Optional[str] = None,
    references: Optional[str] = None,
    attachments: Optional[List[Dict[str, Any]]] = None
) -> MIMEMultipart:
    """
    Construye un mensaje MIME estándar RFC 2822 con soporte para hilo de conversación.
    """
    msg = MIMEMultipart("mixed")
    msg["From"] = sender_email
    msg["To"] = recipient_email
    msg["Subject"] = format_reply_subject(subject)

    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
        if not references:
            references = in_reply_to
    if references:
        msg["References"] = references

    # Contenedor alternativo de texto / HTML
    body_container = MIMEMultipart("alternative")
    body_container.attach(MIMEText(body_text, "plain", "utf-8"))
    if body_html:
        body_container.attach(MIMEText(body_html, "html", "utf-8"))
    msg.attach(body_container)

    # Adjuntos opcionales
    if attachments:
        for att in attachments:
            part = MIMEBase("application", "octet-stream")
            b64_data = att.get("data_base64", "")
            raw_bytes = base64.b64decode(b64_data)
            part.set_payload(raw_bytes)
            encoders.encode_base64(part)
            filename = att.get("filename", "adjunto.pdf")
            part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
            msg.attach(part)

    return msg


# =============================================================================
# PLANTILLAS DE CORREO HSE
# =============================================================================

def generate_hse_email_template(
    decision_action: str,
    coder_name: str,
    justification_id: str,
    affected_date: str,
    excuse_type: str,
    hse_notes: str,
    reviewer_name: str = "Equipo de Bienestar HSE Riwi"
) -> Dict[str, str]:
    """
    Genera el texto plano y el HTML formateado para la respuesta de HSE.
    decision_action: 'APPROVED' | 'DISAPPROVED' | 'REQUEST_CORRECTION'
    """
    badge_color = "#20B486" if decision_action == "APPROVED" else "#FF5C67" if decision_action == "DISAPPROVED" else "#F5B83D"
    badge_title = "JUSTIFICACIÓN APROBADA" if decision_action == "APPROVED" else "JUSTIFICACIÓN RECHAZADA" if decision_action == "DISAPPROVED" else "REQUERIMIENTO DE SOPORTE"

    plain_text = f"""Estimado(a) {coder_name},

Le notificamos la resolución de su solicitud de justificación de inasistencia (ID: {justification_id}).

Estado: {badge_title}
Fecha Afectada: {affected_date}
Tipo de Novedad: {excuse_type}
Observaciones HSE: {hse_notes}

Revisado por: {reviewer_name}
Equipo de Habilidades Socioemocionales (HSE) — RIWI
"""

    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #F8F9FD; margin: 0; padding: 20px; }}
    .card {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 16px; border: 1px solid #E8EAF2; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }}
    .header {{ background: #171B3A; color: #ffffff; padding: 24px; text-align: center; }}
    .badge {{ display: inline-block; background-color: {badge_color}; color: #ffffff; font-weight: bold; padding: 6px 14px; border-radius: 20px; font-size: 13px; margin-top: 8px; }}
    .content {{ padding: 28px; color: #17203A; line-height: 1.6; font-size: 14px; }}
    .details-box {{ background-color: #F6F7FB; border-left: 4px solid {badge_color}; border-radius: 8px; padding: 14px 18px; margin: 20px 0; }}
    .footer {{ background-color: #F8F9FD; padding: 16px 28px; text-align: center; color: #7C8499; font-size: 12px; border-top: 1px solid #E8EAF2; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="header">
      <h2 style="margin:0; font-size: 20px;">RIWI — Notificación de Novedad HSE</h2>
      <div class="badge">{badge_title}</div>
    </div>
    <div class="content">
      <p>Hola <strong>{coder_name}</strong>,</p>
      <p>Se ha emitido una resolución para su solicitud de contingencia formativa / justificación.</p>
      
      <div class="details-box">
        <p style="margin: 4px 0;"><strong>ID de Solicitud:</strong> {justification_id}</p>
        <p style="margin: 4px 0;"><strong>Fecha Afectada:</strong> {affected_date}</p>
        <p style="margin: 4px 0;"><strong>Motivo / Novedad:</strong> {excuse_type}</p>
        <p style="margin: 4px 0;"><strong>Observaciones del Evaluador:</strong> {hse_notes}</p>
      </div>

      <p style="margin-top: 20px;">Si tiene dudas o requiere aportar información adicional, responda directamente a este mismo correo sin modificar el asunto.</p>
      <p>Atentamente,<br><strong>{reviewer_name}</strong><br>Área de Bienestar y HSE RIWI</p>
    </div>
    <div class="footer">
      Este es un mensaje institucional generado por el Sistema de Automatización HSE RIWI.
    </div>
  </div>
</body>
</html>
"""
    return {"text": plain_text, "html": html}


# =============================================================================
# TRANSPORTES DE ENVÍO (CONN-04)
# =============================================================================

class SMTPSender:
    """Envío de correos mediante protocolo estándar SMTP con STARTTLS."""

    def __init__(
        self,
        host: str,
        port: int = 587,
        username: str = "",
        password: str = "",
        use_tls: bool = True
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_tls = use_tls

    @classmethod
    def from_env(cls) -> "SMTPSender":
        return cls(
            host=os.getenv("SMTP_HOST", "smtp.office365.com"),
            port=int(os.getenv("SMTP_PORT", 587)),
            username=os.getenv("SMTP_USER") or os.getenv("OUTLOOK_USER", "hse@riwi.io"),
            password=os.getenv("SMTP_PASSWORD") or os.getenv("OUTLOOK_PASSWORD", ""),
            use_tls=os.getenv("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes")
        )

    def send(self, msg: MIMEMultipart) -> Dict[str, Any]:
        """Envía el mensaje MIME a través del servidor SMTP."""
        if not self.username or not self.password:
            raise ValueError("Credenciales SMTP incompletas (configure SMTP_USER y SMTP_PASSWORD).")

        server = smtplib.SMTP(self.host, self.port, timeout=20)
        try:
            if self.use_tls:
                server.starttls()
            server.login(self.username, self.password)
            server.send_message(msg)
            return {"status": "SUCCESS", "provider": "SMTP", "message": "Correo enviado vía SMTP"}
        finally:
            try:
                server.quit()
            except Exception:
                pass


class GraphMailSender:
    """Envío de correos mediante Microsoft Graph API sendMail."""

    def __init__(self, graph_client=None):
        self.client = graph_client

    def send(
        self,
        to_email: str,
        subject: str,
        body_html: str,
        in_reply_to: Optional[str] = None,
        references: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        if not self.client:
            raise ValueError("Cliente Microsoft Graph no inicializado.")
        res = self.client.send_mail(
            to_email=to_email,
            subject=format_reply_subject(subject),
            body_html=body_html,
            in_reply_to=in_reply_to,
            references=references,
            attachments=attachments
        )
        res["provider"] = "MICROSOFT_GRAPH"
        return res


class GmailSendSender:
    """Envío de correos mediante Gmail REST API v1 messages.send."""

    def __init__(self, gmail_client=None):
        self.client = gmail_client

    def send(self, msg: MIMEMultipart) -> Dict[str, Any]:
        if not self.client:
            raise ValueError("Cliente Gmail API no inicializado.")
        token = self.client.get_token()
        raw_msg_bytes = msg.as_bytes()
        raw_b64url = base64.urlsafe_b64encode(raw_msg_bytes).decode("ascii")

        url = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
        payload = json.dumps({"raw": raw_b64url}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return {
                "status": "SUCCESS",
                "provider": "GMAIL_API",
                "id": data.get("id"),
                "threadId": data.get("threadId")
            }


# =============================================================================
# ENVIADOR UNIFICADO DE ALTA CONFIABILIDAD
# =============================================================================

def send_justification_reply(
    recipient_email: str,
    coder_name: str,
    justification_id: str,
    decision_action: str,
    original_subject: str,
    original_message_id: Optional[str] = None,
    affected_date: str = "",
    excuse_type: str = "Inasistencia médica",
    hse_notes: str = "",
    reviewer_name: str = "Paola Admin (HSE)",
    provider: str = "SMTP",
    attachments: Optional[List[Dict[str, Any]]] = None,
    sender_email: Optional[str] = None
) -> Dict[str, Any]:
    """
    Función principal de despacho de respuesta HSE conservando el hilo de correo.
    """
    from_addr = sender_email or os.getenv("SMTP_FROM", "hse@riwi.io")
    subject = format_reply_subject(original_subject)
    template = generate_hse_email_template(
        decision_action=decision_action,
        coder_name=coder_name,
        justification_id=justification_id,
        affected_date=affected_date or "No especificada",
        excuse_type=excuse_type,
        hse_notes=hse_notes or "Revisión conforme a lineamientos.",
        reviewer_name=reviewer_name
    )

    mime_msg = build_mime_message(
        sender_email=from_addr,
        recipient_email=recipient_email,
        subject=subject,
        body_text=template["text"],
        body_html=template["html"],
        in_reply_to=original_message_id,
        references=original_message_id,
        attachments=attachments
    )

    if provider.upper() == "SMTP":
        sender = SMTPSender.from_env()
        return sender.send(mime_msg)
    elif provider.upper() == "GRAPH":
        import outlook_connector
        graph_client = outlook_connector.OutlookGraphClient.from_env()
        if not graph_client:
            raise ValueError("No se pudieron cargar credenciales de Azure Graph para enviar correo.")
        sender = GraphMailSender(graph_client)
        return sender.send(
            to_email=recipient_email,
            subject=subject,
            body_html=template["html"],
            in_reply_to=original_message_id,
            references=original_message_id,
            attachments=attachments
        )
    elif provider.upper() == "GMAIL":
        import gmail_connector
        gmail_client = gmail_connector.GmailAPIClient.from_env()
        if not gmail_client:
            raise ValueError("No se pudieron cargar credenciales de Gmail API para enviar correo.")
        sender = GmailSendSender(gmail_client)
        return sender.send(mime_msg)
    else:
        raise ValueError(f"Proveedor desconocido: {provider}. Use 'SMTP', 'GRAPH' o 'GMAIL'.")


# =============================================================================
# SUITE DE PRUEBAS OFFLINE DETERMINISTA (CONN-04)
# =============================================================================

def run_offline_test() -> int:
    """Ejecuta una suite determinista de prueba para validación de formato y preservación de hilo."""
    print("=" * 70)
    print("  SUITE DE PRUEBA OFFLINE: DESPACHADOR DE CORREOS Y TRAZABILIDAD   ")
    print("=" * 70)

    # 1. Validación de prefijo de asunto 'Re: '
    subj1 = format_reply_subject("Incapacidad médica 25 de Septiembre")
    subj2 = format_reply_subject("Re: Incapacidad médica 25 de Septiembre")
    print(f"  [1/4] Normalización de asunto de respuesta:")
    print(f"        '{subj1}'")
    assert subj1 == "Re: Incapacidad médica 25 de Septiembre"
    assert subj2 == "Re: Incapacidad médica 25 de Septiembre"

    # 2. Construcción de mensaje MIME con cabeceras de hilo
    original_msg_id = "<msg_orig_123456@riwi.io>"
    mime = build_mime_message(
        sender_email="hse@riwi.io",
        recipient_email="coder@riwi.io",
        subject="Incapacidad médica",
        body_text="Texto de prueba",
        body_html="<p>Texto HTML</p>",
        in_reply_to=original_msg_id,
        references=original_msg_id
    )

    print(f"\n  [2/4] Verificación de cabeceras RFC 2822 de hilo:")
    print(f"        In-Reply-To: {mime['In-Reply-To']}")
    print(f"        References:  {mime['References']}")
    assert mime["In-Reply-To"] == original_msg_id
    assert mime["References"] == original_msg_id
    assert mime["Subject"] == "Re: Incapacidad médica"
    assert mime["To"] == "coder@riwi.io"

    # 3. Validación de Plantillas HSE para los 3 casos
    for action in ["APPROVED", "DISAPPROVED", "REQUEST_CORRECTION"]:
        tmpl = generate_hse_email_template(
            decision_action=action,
            coder_name="Carlos Méndez",
            justification_id="JUST-2026-001",
            affected_date="2026-09-28",
            excuse_type="Calamidad doméstica",
            hse_notes="Aprobado por el equipo HSE."
        )
        assert "Carlos Méndez" in tmpl["text"]
        assert "JUST-2026-001" in tmpl["html"]
        assert ("APROBADA" in tmpl["text"] or "RECHAZADA" in tmpl["text"] or "SOPORTE" in tmpl["text"])
    print(f"\n  [3/4] Plantillas HSE generadas correctamente (APPROVED, DISAPPROVED, REQUEST_CORRECTION).")

    # 4. Verificación de adjuntos MIME en base64
    mock_pdf_bytes = b"%PDF-1.4 Acta de resolucion HSE"
    mock_pdf_b64 = base64.b64encode(mock_pdf_bytes).decode("ascii")
    mime_with_att = build_mime_message(
        sender_email="hse@riwi.io",
        recipient_email="coder@riwi.io",
        subject="Resolución",
        body_text="Texto",
        attachments=[{"filename": "acta_hse.pdf", "data_base64": mock_pdf_b64}]
    )
    payload_parts = list(mime_with_att.get_payload())
    assert len(payload_parts) == 2, f"Se esperaban 2 partes (cuerpo + adjunto), se obtuvieron {len(payload_parts)}"
    print(f"\n  [4/4] Adjuntos MIME integrados y codificados en Base64 con éxito.")

    print("\n" + "=" * 70)
    print("  ¡TODAS LAS PRUEBAS OFFLINE DEL DESPACHADOR PASARON AL 100%!     ")
    print("=" * 70)
    return 0


# =============================================================================
# CLI PRINCIPAL
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Despachador de correos HSE multi-proveedor (SMTP / Graph / Gmail)"
    )
    parser.add_argument("--test", action="store_true", help="Ejecuta la suite de pruebas unitarias offline")
    parser.add_argument("--to", help="Correo destinatario del coder")
    parser.add_argument("--coder-name", default="Coder", help="Nombre del coder")
    parser.add_argument("--id", default="JUST-TEST", help="ID de la justificación")
    parser.add_argument("--action", choices=["APPROVED", "DISAPPROVED", "REQUEST_CORRECTION"], default="APPROVED", help="Decisión HSE")
    parser.add_argument("--subject", default="Justificación de inasistencia", help="Asunto original")
    parser.add_argument("--reply-to-id", help="Message-ID original para conservar el hilo")
    parser.add_argument("--notes", default="Revisión realizada por HSE.", help="Notas del evaluador")
    parser.add_argument("--provider", choices=["SMTP", "GRAPH", "GMAIL"], default="SMTP", help="Proveedor de envío")

    args = parser.parse_args()

    if args.test:
        return run_offline_test()

    if not args.to:
        logger.error("Debe especificar --to (correo del destinatario).")
        logger.info("Para verificar el funcionamiento sin enviar correos reales, ejecute: python mail_sender.py --test")
        return 1

    res = send_justification_reply(
        recipient_email=args.to,
        coder_name=args.coder_name,
        justification_id=args.id,
        decision_action=args.action,
        original_subject=args.subject,
        original_message_id=args.reply_to_id,
        hse_notes=args.notes,
        provider=args.provider
    )
    logger.info(f"Resultado del envío: {res}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
