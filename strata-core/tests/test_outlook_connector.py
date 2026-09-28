import os
import sys
import email
import base64
import hashlib
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import outlook_connector

def test_extract_sender_info():
    email_addr, name = outlook_connector.extract_sender_info('"Santiago Morales" <santiago.morales@riwi.io>')
    assert email_addr == "santiago.morales@riwi.io"
    assert name == "Santiago Morales"

    # Caso sin corchetes
    email_addr_plain, name_plain = outlook_connector.extract_sender_info("laura.gomez@riwi.io")
    assert email_addr_plain == "laura.gomez@riwi.io"

def test_decode_mime_header_rfc2047():
    encoded = "=?UTF-8?Q?Justificaci=C3=B3n_inasistencia_m=C3=A9dica?="
    decoded = outlook_connector.decode_mime_header(encoded)
    assert decoded == "Justificación inasistencia médica"

def test_extract_attachments_and_sha256():
    sample_content = b"%PDF-1.4 Incapacidad Medica SURA EPS"
    b64_content = base64.b64encode(sample_content).decode("ascii")
    expected_hash = hashlib.sha256(sample_content).hexdigest()

    raw_mime = f"""Content-Type: multipart/mixed; boundary="BOUNDARY123"

--BOUNDARY123
Content-Type: text/plain

Mensaje de prueba.

--BOUNDARY123
Content-Type: application/pdf
Content-Disposition: attachment; filename="incapacidad.pdf"
Content-Transfer-Encoding: base64

{b64_content}
--BOUNDARY123--
"""
    msg = email.message_from_string(raw_mime)
    attachments = outlook_connector.extract_attachments(msg)
    assert len(attachments) == 1
    assert attachments[0]["filename"] == "incapacidad.pdf"
    assert attachments[0]["mime_type"] == "application/pdf"
    assert attachments[0]["sha256"] == expected_hash
    assert attachments[0]["data_base64"] == b64_content

def test_offline_suite_runs():
    assert outlook_connector.run_offline_test() == 0

def test_graph_client_from_env(monkeypatch):
    # Test when vars are missing
    monkeypatch.delenv("OUTLOOK_TENANT_ID", raising=False)
    monkeypatch.delenv("AZURE_TENANT_ID", raising=False)
    assert outlook_connector.OutlookGraphClient.from_env() is None

    # Test when Azure vars are provided
    monkeypatch.setenv("AZURE_TENANT_ID", "tenant-123")
    monkeypatch.setenv("AZURE_CLIENT_ID", "client-456")
    monkeypatch.setenv("AZURE_CLIENT_SECRET", "secret-789")
    monkeypatch.setenv("OUTLOOK_MAILBOX", "hse@riwi.io")
    client = outlook_connector.OutlookGraphClient.from_env()
    assert client is not None
    assert client.tenant_id == "tenant-123"
    assert client.client_id == "client-456"
    assert client.client_secret == "secret-789"
    assert client.user_email == "hse@riwi.io"
