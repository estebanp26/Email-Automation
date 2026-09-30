import os
import sys
import email
import json
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


class MockHTTPResponse:
    def __init__(self, status: int, data: bytes):
        self.status = status
        self._data = data

    def read(self):
        return self._data

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


def test_forward_to_inbound_api_success_202(monkeypatch):
    """Verifica que el conector reciba correctamente HTTP 202 Accepted de la API nativa."""
    fake_body = json.dumps({
        "status": "ACCEPTED",
        "message": "Event queued for identification and validation",
        "message_id": "msg-outlook-001",
        "transaction_id": "tx-12345",
        "state": "PENDING_IDENTIFICATION"
    }).encode("utf-8")

    def mock_urlopen(req, timeout=30):
        assert req.headers.get("Authorization") == "Bearer secret-token-123"
        assert req.headers.get("X-api-key") == "secret-token-123"
        return MockHTTPResponse(202, fake_body)

    monkeypatch.setattr(outlook_connector.urllib.request, "urlopen", mock_urlopen)

    payload = {"source_provider": "OUTLOOK", "message_id": "msg-outlook-001"}
    res = outlook_connector.forward_to_inbound_api(
        payload=payload,
        api_key="secret-token-123"
    )
    assert res["status"] == "SUCCESS"
    assert res["code"] == 202
    assert res["response"]["transaction_id"] == "tx-12345"
    assert res["response"]["state"] == "PENDING_IDENTIFICATION"
    assert res["retries"] == 0


def test_forward_to_inbound_api_idempotency_200(monkeypatch):
    """Verifica el manejo transparente de idempotencia (HTTP 200 OK) sin arrojar error."""
    fake_body = json.dumps({
        "status": "OK",
        "message": "Event already processed",
        "message_id": "msg-duplicate-001"
    }).encode("utf-8")

    def mock_urlopen(req, timeout=30):
        return MockHTTPResponse(200, fake_body)

    monkeypatch.setattr(outlook_connector.urllib.request, "urlopen", mock_urlopen)

    payload = {"source_provider": "OUTLOOK", "message_id": "msg-duplicate-001"}
    res = outlook_connector.forward_to_inbound_api(payload=payload)
    assert res["status"] == "SUCCESS"
    assert res["code"] == 200
    assert res["response"]["message"] == "Event already processed"


def test_forward_to_inbound_api_backoff_on_503(monkeypatch):
    """
    Criterio de Aceptación:
    Ambos conectores ejecutan reintentos con backoff exponencial si la API backend
    está temporalmente no disponible (código 503/504).
    """
    import urllib.error
    call_count = 0

    fake_success_body = json.dumps({
        "status": "ACCEPTED",
        "transaction_id": "tx-retry-recovered",
        "state": "PENDING_IDENTIFICATION"
    }).encode("utf-8")

    def mock_urlopen_with_retries(req, timeout=30):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise urllib.error.HTTPError(req.full_url, 503, "Service Unavailable", {}, None)
        elif call_count == 2:
            raise urllib.error.HTTPError(req.full_url, 504, "Gateway Timeout", {}, None)
        return MockHTTPResponse(202, fake_success_body)

    monkeypatch.setattr(outlook_connector.urllib.request, "urlopen", mock_urlopen_with_retries)
    # Reducir base_delay para prueba ultrarrápida
    payload = {"source_provider": "OUTLOOK", "message_id": "msg-retry-test"}
    res = outlook_connector.forward_to_inbound_api(
        payload=payload,
        max_retries=3,
        base_delay=0.01
    )

    assert call_count == 3
    assert res["status"] == "SUCCESS"
    assert res["code"] == 202
    assert res["retries"] == 2


def test_forward_to_inbound_api_hmac_signature(monkeypatch):
    """Verifica la generación de la firma HMAC-SHA256 en X-Signature-SHA256."""
    captured_headers = {}

    def mock_urlopen(req, timeout=30):
        nonlocal captured_headers
        captured_headers = {k: v for k, v in req.headers.items()}
        return MockHTTPResponse(202, b'{"status": "ACCEPTED"}')

    monkeypatch.setattr(outlook_connector.urllib.request, "urlopen", mock_urlopen)

    payload = {"source_provider": "OUTLOOK", "test": "data"}
    outlook_connector.forward_to_inbound_api(
        payload=payload,
        hmac_secret="secret-key-xyz"
    )

    assert "X-signature-sha256" in captured_headers
    raw_payload = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    import hmac
    expected_sig = hmac.new(b"secret-key-xyz", raw_payload, hashlib.sha256).hexdigest()
    assert captured_headers["X-signature-sha256"] == expected_sig


def test_attachment_binary_integrity_and_zero_corruption():
    """
    Criterio de Aceptación:
    Validación de que los adjuntos se codifiquen y transmitan sin corrupción de bytes.
    Prueba flujos binarios arbitrarios incluyendo bytes nulos y secuencias de escape.
    """
    # Archivo binario con bytes altos y nulos simulando PDF corruptible
    raw_pdf_bytes = bytes([0x25, 0x50, 0x44, 0x46, 0x2D, 0x31, 0x2E, 0x34] + list(range(256)) * 4)
    raw_b64 = base64.b64encode(raw_pdf_bytes).decode("ascii")

    raw_mime = f"""Content-Type: multipart/mixed; boundary="BND1"

--BND1
Content-Type: application/pdf
Content-Disposition: attachment; filename="documento_integridad.pdf"
Content-Transfer-Encoding: base64

{raw_b64}
--BND1--
"""
    msg = email.message_from_string(raw_mime)
    attachments = outlook_connector.extract_attachments(msg)

    assert len(attachments) == 1
    att = attachments[0]
    decoded = base64.b64decode(att["data_base64"])

    assert decoded == raw_pdf_bytes, "¡FALLO DE INTEGRIDAD: bytes no coinciden!"
    assert hashlib.sha256(decoded).hexdigest() == att["sha256"]
    assert att["sha256_hash"] == att["sha256"]
    assert att["size_bytes"] == len(raw_pdf_bytes)
