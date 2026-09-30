#!/usr/bin/env python3
"""
test_conn04_connectors_native_api.py
=============================================================================
SUITE OFICIAL DE PRUEBAS DE INTEGRACIÓN: CONN-04
=============================================================================
Valida los Criterios de Aceptación de CONN-04:
1. Desacoplamiento total de n8n: Conectores apuntan por defecto a POST /api/v1/inbound-email.
2. Autenticación interna por clave de API (Bearer / X-API-Key) y firma HMAC-SHA256.
3. Resiliencia y Exponential Backoff ante errores 503 / 504 / fallos de red.
4. Cero corrupción de bytes en codificación, transmisión y cálculo de SHA-256 de adjuntos.
5. Manejo correcto de idempotencia (HTTP 200 OK) y nuevos eventos (HTTP 202 Accepted).
=============================================================================
"""

import os
import sys
import json
import base64
import hashlib
import hmac
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import urllib.error

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import outlook_connector
import gmail_connector


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


# =============================================================================
# 1. CRITERIO 1: RETIRO DEFINITIVO DE N8N Y DESTINO NATIVO PREDETERMINADO
# =============================================================================

def test_n8n_functions_and_parameters_removed():
    """Verifica que los conectores ya no contengan funciones de despacho a n8n ni dependencias activas."""
    assert not hasattr(outlook_connector, "forward_to_n8n_webhook"), "forward_to_n8n_webhook no debe existir en outlook_connector"
    assert not hasattr(gmail_connector, "forward_to_n8n_webhook"), "forward_to_n8n_webhook no debe existir en gmail_connector"


def test_default_api_url_points_to_native_inbound_endpoint():
    """Verifica que el endpoint predeterminado en ambos conectores sea POST /api/v1/inbound-email."""
    # Outlook
    import inspect
    sig_outlook = inspect.signature(outlook_connector.forward_to_inbound_api)
    default_outlook_url = sig_outlook.parameters["api_url"].default
    assert "/api/v1/inbound-email" in default_outlook_url

    # Gmail
    sig_gmail = inspect.signature(gmail_connector.forward_to_inbound_api)
    default_gmail_url = sig_gmail.parameters["api_url"].default
    assert "/api/v1/inbound-email" in default_gmail_url


# =============================================================================
# 2. CRITERIO 2: AUTENTICACIÓN POR CLAVE DE API INTERNA (BEARER / HMAC)
# =============================================================================

def test_outlook_connector_injects_bearer_and_hmac_headers(monkeypatch):
    """Verifica que outlook_connector incluya Authorization Bearer, X-API-Key y firma HMAC."""
    captured_headers = {}

    def mock_urlopen(req, timeout=30):
        nonlocal captured_headers
        captured_headers = {k: v for k, v in req.headers.items()}
        return MockHTTPResponse(202, b'{"status": "ACCEPTED", "transaction_id": "tx-1"}')

    monkeypatch.setattr(outlook_connector.urllib.request, "urlopen", mock_urlopen)

    payload = {
        "source_provider": "OUTLOOK",
        "message_id": "msg-auth-test-01",
        "sender_email": "coder@riwi.io"
    }

    res = outlook_connector.forward_to_inbound_api(
        payload=payload,
        api_key="my-super-secret-api-key",
        hmac_secret="my-hmac-signing-secret"
    )

    assert res["status"] == "SUCCESS"
    assert res["code"] == 202
    assert captured_headers.get("Authorization") == "Bearer my-super-secret-api-key"
    assert captured_headers.get("X-api-key") == "my-super-secret-api-key"

    # Verificar cálculo HMAC-SHA256
    raw_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    expected_hmac = hmac.new(b"my-hmac-signing-secret", raw_bytes, hashlib.sha256).hexdigest()
    assert captured_headers.get("X-signature-sha256") == expected_hmac


def test_gmail_connector_injects_bearer_and_hmac_headers(monkeypatch):
    """Verifica que gmail_connector incluya Authorization Bearer, X-API-Key y firma HMAC."""
    captured_headers = {}

    def mock_urlopen(req, timeout=30):
        nonlocal captured_headers
        captured_headers = {k: v for k, v in req.headers.items()}
        return MockHTTPResponse(202, b'{"status": "ACCEPTED", "transaction_id": "tx-gmail-1"}')

    monkeypatch.setattr(gmail_connector.urllib.request, "urlopen", mock_urlopen)

    payload = {
        "source_provider": "GMAIL",
        "message_id": "msg-gmail-auth-test",
        "sender_email": "mariana.ospina@riwi.io"
    }

    res = gmail_connector.forward_to_inbound_api(
        payload=payload,
        api_key="gmail-token-bearer",
        hmac_secret="gmail-hmac-key"
    )

    assert res["status"] == "SUCCESS"
    assert res["code"] == 202
    assert captured_headers.get("Authorization") == "Bearer gmail-token-bearer"
    assert captured_headers.get("X-api-key") == "gmail-token-bearer"

    raw_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    expected_hmac = hmac.new(b"gmail-hmac-key", raw_bytes, hashlib.sha256).hexdigest()
    assert captured_headers.get("X-signature-sha256") == expected_hmac


# =============================================================================
# 3. CRITERIO 3: RESILIENCIA CON BACKOFF EXPONENCIAL ANTE 503 / 504 / RED
# =============================================================================

def test_outlook_connector_retries_on_503_and_504_with_backoff(monkeypatch):
    """
    Criterio de Aceptación:
    Ambos conectores ejecutan reintentos con backoff exponencial si la API backend
    está temporalmente no disponible (código 503/504).
    """
    call_attempts = 0

    def mock_urlopen(req, timeout=30):
        nonlocal call_attempts
        call_attempts += 1
        if call_attempts == 1:
            raise urllib.error.HTTPError(req.full_url, 503, "Service Unavailable", {}, None)
        elif call_attempts == 2:
            raise urllib.error.HTTPError(req.full_url, 504, "Gateway Timeout", {}, None)
        return MockHTTPResponse(202, b'{"status": "ACCEPTED", "transaction_id": "tx-backoff-success"}')

    monkeypatch.setattr(outlook_connector.urllib.request, "urlopen", mock_urlopen)

    res = outlook_connector.forward_to_inbound_api(
        payload={"source_provider": "OUTLOOK", "test": "backoff"},
        max_retries=3,
        base_delay=0.01  # Aceleración de test
    )

    assert call_attempts == 3
    assert res["status"] == "SUCCESS"
    assert res["code"] == 202
    assert res["retries"] == 2


def test_gmail_connector_retries_on_503_and_504_with_backoff(monkeypatch):
    """Verifica backoff exponencial en gmail_connector ante 503 y 504."""
    call_attempts = 0

    def mock_urlopen(req, timeout=30):
        nonlocal call_attempts
        call_attempts += 1
        if call_attempts == 1:
            raise urllib.error.HTTPError(req.full_url, 503, "Service Unavailable", {}, None)
        elif call_attempts == 2:
            raise urllib.error.HTTPError(req.full_url, 504, "Gateway Timeout", {}, None)
        return MockHTTPResponse(202, b'{"status": "ACCEPTED", "transaction_id": "tx-gmail-backoff"}')

    monkeypatch.setattr(gmail_connector.urllib.request, "urlopen", mock_urlopen)

    res = gmail_connector.forward_to_inbound_api(
        payload={"source_provider": "GMAIL", "test": "backoff"},
        max_retries=3,
        base_delay=0.01
    )

    assert call_attempts == 3
    assert res["status"] == "SUCCESS"
    assert res["code"] == 202
    assert res["retries"] == 2


def test_connectors_fail_fast_on_client_errors_without_retry(monkeypatch):
    """Verifica que ante errores 400, 401 o 422 NO se reintente innecesariamente."""
    outlook_calls = 0
    gmail_calls = 0

    def mock_outlook_err(req, timeout=30):
        nonlocal outlook_calls
        outlook_calls += 1
        raise urllib.error.HTTPError(req.full_url, 422, "Unprocessable Entity", {}, None)

    def mock_gmail_err(req, timeout=30):
        nonlocal gmail_calls
        gmail_calls += 1
        raise urllib.error.HTTPError(req.full_url, 401, "Unauthorized", {}, None)

    monkeypatch.setattr(outlook_connector.urllib.request, "urlopen", mock_outlook_err)
    res_outlook = outlook_connector.forward_to_inbound_api(
        payload={"test": "bad"},
        max_retries=3,
        base_delay=0.01
    )
    assert outlook_calls == 1, "No debe reintentar errores 422"
    assert res_outlook["status"] == "HTTP_ERROR"
    assert res_outlook["code"] == 422

    monkeypatch.setattr(gmail_connector.urllib.request, "urlopen", mock_gmail_err)
    res_gmail = gmail_connector.forward_to_inbound_api(
        payload={"test": "unauth"},
        max_retries=3,
        base_delay=0.01
    )
    assert gmail_calls == 1, "No debe reintentar errores 401"
    assert res_gmail["status"] == "HTTP_ERROR"
    assert res_gmail["code"] == 401


# =============================================================================
# 4. CRITERIO 4: VALIDACIÓN DE CERO CORRUPCIÓN DE BYTES EN ADJUNTOS
# =============================================================================

def test_zero_byte_corruption_pdf_binary_stream():
    """
    Criterio de Aceptación:
    Validación de que los adjuntos se codifiquen y transmitan sin corrupción de bytes.
    Prueba un PDF simulado con tablas de xref, streams binarios y bytes nulos.
    """
    raw_pdf = (
        b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"stream\n" + bytes(range(256)) * 8 + b"\nendstream\n%%EOF"
    )
    b64_encoded = base64.b64encode(raw_pdf).decode("ascii")
    expected_sha256 = hashlib.sha256(raw_pdf).hexdigest()

    # Outlook extraction simulation
    raw_mime = f"""Content-Type: multipart/mixed; boundary="TEST_BOUND"

--TEST_BOUND
Content-Type: application/pdf; name="certificado_medico.pdf"
Content-Disposition: attachment; filename="certificado_medico.pdf"
Content-Transfer-Encoding: base64

{b64_encoded}
--TEST_BOUND--
"""
    import email
    msg = email.message_from_string(raw_mime)
    attachments = outlook_connector.extract_attachments(msg)

    assert len(attachments) == 1
    att = attachments[0]
    recovered_bytes = base64.b64decode(att["data_base64"])

    assert recovered_bytes == raw_pdf, "¡Fallo crítico: bytes recuperados difieren del original!"
    assert hashlib.sha256(recovered_bytes).hexdigest() == expected_sha256
    assert att["size_bytes"] == len(raw_pdf)


def test_zero_byte_corruption_image_binary_stream():
    """Verifica que imágenes PNG y JPG no sufran corrupción ni truncamiento de cabeceras."""
    # PNG con magic bytes \x89PNG\r\n\x1a\n y chunks de datos
    raw_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + bytes(range(128)) + b"\x00\x00\x00\x00IEND\xaeB`\x82"
    expected_sha256 = hashlib.sha256(raw_png).hexdigest()

    # Gmail base64url simulation
    b64url = base64.urlsafe_b64encode(raw_png).decode("ascii").rstrip("=")
    mock_payload = {
        "parts": [{
            "filename": "evidencia_camara.png",
            "mimeType": "image/png",
            "body": {"data": b64url}
        }]
    }

    attachments = gmail_connector.extract_attachments_from_gmail_payload("msg-img-1", mock_payload)
    assert len(attachments) == 1
    att = attachments[0]

    recovered_bytes = base64.b64decode(att["data_base64"])
    assert recovered_bytes == raw_png, "¡Fallo crítico: bytes de imagen PNG sufrieron corrupción!"
    assert hashlib.sha256(recovered_bytes).hexdigest() == expected_sha256
    assert att["sha256"] == expected_sha256
    assert att["size_bytes"] == len(raw_png)


# =============================================================================
# 5. IDEMPOTENCIA Y NORMALIZACIÓN DE PAYLOADS
# =============================================================================

def test_idempotent_response_handling_200(monkeypatch):
    """Verifica que el código HTTP 200 OK con mensaje de idempotencia sea procesado con éxito."""
    body_dup = json.dumps({
        "status": "OK",
        "message": "Event already processed",
        "message_id": "msg-duplicate-conn04"
    }).encode("utf-8")

    monkeypatch.setattr(outlook_connector.urllib.request, "urlopen", lambda req, timeout=30: MockHTTPResponse(200, body_dup))

    res = outlook_connector.forward_to_inbound_api(
        payload={"source_provider": "OUTLOOK", "message_id": "msg-duplicate-conn04"}
    )

    assert res["status"] == "SUCCESS"
    assert res["code"] == 200
    assert res["response"]["message"] == "Event already processed"
