import os
import sys
import base64
import json
import hashlib
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import gmail_connector

def test_decode_base64url():
    # Test valid URL safe base64 with missing padding
    original = b"Hola Mundo desde PubSub HSE"
    b64url = base64.urlsafe_b64encode(original).decode("ascii").rstrip("=")
    decoded = gmail_connector.decode_base64url(b64url)
    assert decoded == original

    # Test empty string
    assert gmail_connector.decode_base64url("") == b""

def test_parse_sender_string():
    email_addr, name = gmail_connector.parse_sender_string('"Laura Gómez" <laura.gomez@riwi.io>')
    assert email_addr == "laura.gomez@riwi.io"
    assert name == "Laura Gómez"

    email_addr2, name2 = gmail_connector.parse_sender_string("camilo.torres@riwi.io")
    assert email_addr2 == "camilo.torres@riwi.io"

def test_parse_pubsub_push_payload():
    payload_data = {"emailAddress": "hse@riwi.io", "historyId": "554433"}
    data_b64 = base64.b64encode(json.dumps(payload_data).encode("utf-8")).decode("ascii")

    req_body = {
        "message": {
            "data": data_b64,
            "messageId": "msg_pubsub_99",
            "publishTime": "2026-09-28T12:00:00Z"
        },
        "subscription": "projects/riwi-hse/subscriptions/sub-1"
    }

    parsed = gmail_connector.parse_pubsub_push_payload(req_body)
    assert parsed["email_address"] == "hse@riwi.io"
    assert parsed["history_id"] == "554433"
    assert parsed["pubsub_message_id"] == "msg_pubsub_99"

def test_extract_attachments_from_gmail():
    content = b"%PDF-1.4 Mock Attachment For Testing"
    b64url = base64.urlsafe_b64encode(content).decode("ascii").rstrip("=")
    expected_hash = hashlib.sha256(content).hexdigest()
    expected_b64 = base64.b64encode(content).decode("ascii")

    payload = {
        "parts": [
            {
                "partId": "0",
                "mimeType": "text/plain",
                "body": {"data": base64.urlsafe_b64encode(b"Texto de prueba").decode("ascii")}
            },
            {
                "partId": "1",
                "mimeType": "application/pdf",
                "filename": "constancia_medica.pdf",
                "body": {
                    "data": b64url
                }
            }
        ]
    }

    attachments = gmail_connector.extract_attachments_from_gmail_payload("msg123", payload)
    assert len(attachments) == 1
    assert attachments[0]["filename"] == "constancia_medica.pdf"
    assert attachments[0]["mime_type"] == "application/pdf"
    assert attachments[0]["sha256"] == expected_hash
    assert attachments[0]["data_base64"] == expected_b64

def test_gmail_client_from_env(monkeypatch):
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("GMAIL_CLIENT_ID", raising=False)
    assert gmail_connector.GmailAPIClient.from_env() is None

    monkeypatch.setenv("GOOGLE_CLIENT_ID", "google-cid")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "google-sec")
    monkeypatch.setenv("GOOGLE_REFRESH_TOKEN", "google-ref")
    client = gmail_connector.GmailAPIClient.from_env()
    assert client is not None
    assert client.client_id == "google-cid"
    assert client.client_secret == "google-sec"
    assert client.refresh_token == "google-ref"

def test_offline_suite_runs():
    assert gmail_connector.run_offline_test() == 0


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


def test_gmail_forward_to_inbound_api_success_202(monkeypatch):
    """Verifica que el conector de Gmail reciba HTTP 202 Accepted de la API nativa."""
    fake_body = json.dumps({
        "status": "ACCEPTED",
        "message": "Event queued for identification and validation",
        "message_id": "msg-gmail-001",
        "transaction_id": "tx-gmail-12345",
        "state": "PENDING_IDENTIFICATION"
    }).encode("utf-8")

    def mock_urlopen(req, timeout=30):
        assert req.headers.get("Authorization") == "Bearer gmail-secret-key"
        assert req.headers.get("X-api-key") == "gmail-secret-key"
        return MockHTTPResponse(202, fake_body)

    monkeypatch.setattr(gmail_connector.urllib.request, "urlopen", mock_urlopen)

    payload = {"source_provider": "GMAIL", "message_id": "msg-gmail-001"}
    res = gmail_connector.forward_to_inbound_api(
        payload=payload,
        api_key="gmail-secret-key"
    )
    assert res["status"] == "SUCCESS"
    assert res["code"] == 202
    assert res["response"]["transaction_id"] == "tx-gmail-12345"
    assert res["response"]["state"] == "PENDING_IDENTIFICATION"
    assert res["retries"] == 0


def test_gmail_forward_to_inbound_api_idempotency_200(monkeypatch):
    """Verifica el manejo de idempotencia (HTTP 200 OK) sin error en el conector de Gmail."""
    fake_body = json.dumps({
        "status": "OK",
        "message": "Event already processed",
        "message_id": "msg-duplicate-gmail"
    }).encode("utf-8")

    def mock_urlopen(req, timeout=30):
        return MockHTTPResponse(200, fake_body)

    monkeypatch.setattr(gmail_connector.urllib.request, "urlopen", mock_urlopen)

    payload = {"source_provider": "GMAIL", "message_id": "msg-duplicate-gmail"}
    res = gmail_connector.forward_to_inbound_api(payload=payload)
    assert res["status"] == "SUCCESS"
    assert res["code"] == 200
    assert res["response"]["message"] == "Event already processed"


def test_gmail_forward_to_inbound_api_backoff_on_503(monkeypatch):
    """
    Criterio de Aceptación:
    Reintentos automáticos con backoff exponencial ante códigos 503/504 en Gmail connector.
    """
    import urllib.error
    call_count = 0

    fake_success_body = json.dumps({
        "status": "ACCEPTED",
        "transaction_id": "tx-gmail-recovered",
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

    monkeypatch.setattr(gmail_connector.urllib.request, "urlopen", mock_urlopen_with_retries)

    payload = {"source_provider": "GMAIL", "message_id": "msg-gmail-retry"}
    res = gmail_connector.forward_to_inbound_api(
        payload=payload,
        max_retries=3,
        base_delay=0.01
    )

    assert call_count == 3
    assert res["status"] == "SUCCESS"
    assert res["code"] == 202
    assert res["retries"] == 2


def test_gmail_forward_to_inbound_api_hmac_signature(monkeypatch):
    """Verifica la firma HMAC-SHA256 en X-Signature-SHA256 para Gmail connector."""
    captured_headers = {}

    def mock_urlopen(req, timeout=30):
        nonlocal captured_headers
        captured_headers = {k: v for k, v in req.headers.items()}
        return MockHTTPResponse(202, b'{"status": "ACCEPTED"}')

    monkeypatch.setattr(gmail_connector.urllib.request, "urlopen", mock_urlopen)

    payload = {"source_provider": "GMAIL", "message_id": "msg-gmail-hmac"}
    gmail_connector.forward_to_inbound_api(
        payload=payload,
        hmac_secret="gmail-hmac-secret"
    )

    assert "X-signature-sha256" in captured_headers
    raw_payload = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    import hmac
    expected_sig = hmac.new(b"gmail-hmac-secret", raw_payload, hashlib.sha256).hexdigest()
    assert captured_headers["X-signature-sha256"] == expected_sig


def test_gmail_attachment_binary_integrity_and_zero_corruption():
    """
    Criterio de Aceptación:
    Validación de que los adjuntos se codifiquen y transmitan sin corrupción de bytes.
    Verifica conversión estricta de base64url a bytes crudos y preservación de hashes.
    """
    # Stream binario complejo
    raw_bytes = bytes([0xFF, 0xD8, 0xFF, 0xE0] + list(range(256)) * 3 + [0x00, 0x01, 0xFE])
    b64url = base64.urlsafe_b64encode(raw_bytes).decode("ascii").rstrip("=")
    expected_hash = hashlib.sha256(raw_bytes).hexdigest()
    expected_std_b64 = base64.b64encode(raw_bytes).decode("ascii")

    mock_payload = {
        "parts": [
            {
                "partId": "0",
                "filename": "evidencia_medica.jpg",
                "mimeType": "image/jpeg",
                "body": {"data": b64url}
            }
        ]
    }

    attachments = gmail_connector.extract_attachments_from_gmail_payload("msg-test", mock_payload)
    assert len(attachments) == 1
    att = attachments[0]

    assert att["filename"] == "evidencia_medica.jpg"
    assert att["mime_type"] == "image/jpeg"
    assert att["sha256"] == expected_hash
    assert att["sha256_hash"] == expected_hash
    assert att["data_base64"] == expected_std_b64

    # Verificar decodificación exacta
    recovered_bytes = base64.b64decode(att["data_base64"])
    assert recovered_bytes == raw_bytes, "¡CORRUPCIÓN DE BYTES EN ADJUNTO DE GMAIL!"

