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
