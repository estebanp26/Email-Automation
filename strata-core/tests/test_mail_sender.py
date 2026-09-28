import os
import sys
import base64
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import mail_sender

def test_format_reply_subject():
    assert mail_sender.format_reply_subject("Asunto") == "Re: Asunto"
    assert mail_sender.format_reply_subject("Re: Asunto") == "Re: Asunto"
    assert mail_sender.format_reply_subject("RE: Asunto") == "RE: Asunto"
    assert mail_sender.format_reply_subject("") == "Re: Justificación de Inasistencia"

def test_build_mime_message_headers():
    msg = mail_sender.build_mime_message(
        sender_email="hse@riwi.io",
        recipient_email="coder@riwi.io",
        subject="Incapacidad 2 días",
        body_text="Cuerpo en texto plano",
        body_html="<p>Cuerpo en HTML</p>",
        in_reply_to="<parent_msg_id_123@riwi.io>",
        references="<parent_msg_id_123@riwi.io>"
    )
    assert msg["From"] == "hse@riwi.io"
    assert msg["To"] == "coder@riwi.io"
    assert msg["Subject"] == "Re: Incapacidad 2 días"
    assert msg["In-Reply-To"] == "<parent_msg_id_123@riwi.io>"
    assert msg["References"] == "<parent_msg_id_123@riwi.io>"

def test_build_mime_message_with_attachment():
    raw_pdf = b"%PDF-1.4 Mock Acta Resolucion"
    b64_pdf = base64.b64encode(raw_pdf).decode("ascii")

    msg = mail_sender.build_mime_message(
        sender_email="hse@riwi.io",
        recipient_email="coder@riwi.io",
        subject="Acta",
        body_text="Adjunto resolución",
        attachments=[{
            "filename": "acta.pdf",
            "data_base64": b64_pdf
        }]
    )
    # Debe ser multipart con 2 subpartes: cuerpo alternativo y adjunto
    parts = list(msg.get_payload())
    assert len(parts) == 2
    assert parts[1].get_filename() == "acta.pdf"

def test_generate_hse_email_template():
    for action in ["APPROVED", "DISAPPROVED", "REQUEST_CORRECTION"]:
        tmpl = mail_sender.generate_hse_email_template(
            decision_action=action,
            coder_name="Carlos Méndez",
            justification_id="JUST-001",
            affected_date="2026-09-28",
            excuse_type="Calamidad doméstica",
            hse_notes="Observación de prueba",
            reviewer_name="Paola Admin"
        )
        assert "Carlos Méndez" in tmpl["text"]
        assert "JUST-001" in tmpl["html"]
        assert "Paola Admin" in tmpl["html"]

def test_smtp_sender_from_env(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.office365.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USER", "hse_test@riwi.io")
    monkeypatch.setenv("SMTP_PASSWORD", "secret123")
    sender = mail_sender.SMTPSender.from_env()
    assert sender.host == "smtp.office365.com"
    assert sender.port == 587
    assert sender.username == "hse_test@riwi.io"
    assert sender.password == "secret123"

def test_offline_suite_runs():
    assert mail_sender.run_offline_test() == 0
