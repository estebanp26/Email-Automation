"""
Suite de Pruebas Automatizadas de Auditoría de Seguridad: Carga de Archivos y Sanitización (QA-01).

Valida y verifica la mitigación de los 4 vectores de ataque reportados:
1. PoC 1: Content-Type Spoofing (Inspección estricta de Magic Bytes / Bloqueo de MZ, ELF, scripts).
2. PoC 2: Salto de Directorio (Path Traversal en filename: ../, ..\\, null bytes).
3. PoC 3: Detección y filtrado de Malware (Firma estándar antivirus EICAR y scripts).
4. PoC 4: Mitigación de DoS por exceso de memoria (Content-Length middleware > 20MB y adjuntos > 15MB).
5. Casos de control positivo: Verificación de evidencias legítimas (PDF, PNG, JPEG, WEBP).
"""

import base64
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def _build_email_payload(filename: str, mime_type: str, data_bytes: bytes, sender: str = "carlos.perez@riwi.io") -> dict:
    """Helper para construir payloads canónicos para POST /api/v1/emails/ingest."""
    return {
        "source_provider": "OUTLOOK",
        "message_id": f"sec-test-{hash(filename)}",
        "sender_email": sender,
        "sender_name": "Carlos Pérez",
        "recipient_email": "tl.hse@riwi.io",
        "cc_emails": ["formacion.barranquilla@riwi.io"],
        "subject": "Soporte de Inasistencia - Auditoría de Seguridad QA-01",
        "body": "Buenas tardes Team Leader, adjunto soporte médico correspondiente a mi inasistencia. CC 1045892341 Clan Turing.",
        "attachments": [
            {
                "filename": filename,
                "mime_type": mime_type,
                "data_base64": base64.b64encode(data_bytes).decode("utf-8"),
                "size_bytes": len(data_bytes)
            }
        ]
    }


# ==============================================================================
# 1. PoC 1: Content-Type Spoofing & Bloqueo de Ejecutables
# ==============================================================================

def test_poc1_reject_windows_pe_executable_renamed_as_pdf():
    """PoC 1: Un ejecutable de Windows (cabecera MZ) renombrado como 'malware.pdf' debe ser rechazado con 400."""
    pe_header = bytes([77, 90, 144, 0, 3, 0, 0, 0, 4, 0, 0, 0, 255, 255]) + b"SimulatedWindowsBinaryHeader"
    payload = _build_email_payload("malware.pdf", "application/pdf", pe_header)

    response = client.post("/api/v1/emails/ingest", json=payload)
    assert response.status_code == 400
    assert "Falsificación de Archivo" in response.json()["detail"] or "ejecutable" in response.json()["detail"].lower()


def test_poc1_reject_linux_elf_executable_renamed_as_png():
    """PoC 1b: Un binario ejecutable Linux (cabecera ELF) renombrado como 'evidencia.png' debe ser rechazado con 400."""
    elf_header = bytes([127, 69, 76, 70, 2, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0]) + b"SimulatedELF"
    payload = _build_email_payload("evidencia.png", "image/png", elf_header)

    response = client.post("/api/v1/emails/ingest", json=payload)
    assert response.status_code == 400
    assert "Falsificación de Archivo" in response.json()["detail"] or "ejecutable" in response.json()["detail"].lower()


def test_poc1_reject_shell_script_renamed_as_pdf():
    """PoC 1c: Un script ejecutable de shell (shebang #!) renombrado como 'soporte.pdf' debe ser rechazado con 400."""
    script_content = b"#!" + b"/bin/bash\necho Malicious\n"
    payload = _build_email_payload("soporte.pdf", "application/pdf", script_content)

    response = client.post("/api/v1/emails/ingest", json=payload)
    assert response.status_code == 400
    assert any(term in response.json()["detail"].lower() for term in ["shell", "script", "falsificación", "malware", "ejecutable"])


def test_poc1_reject_pdf_with_corrupted_or_fake_magic_bytes():
    """PoC 1d: Un archivo con extensión .pdf pero con texto plano o bytes que no inician con %PDF- debe ser rechazado con 400."""
    fake_pdf = b"Esto no es un archivo PDF legitimo, es solo texto plano intentando enganar al sistema."
    payload = _build_email_payload("incapacidad_falsa.pdf", "application/pdf", fake_pdf)

    response = client.post("/api/v1/emails/ingest", json=payload)
    assert response.status_code == 400
    assert "Falsificación de tipo MIME" in response.json()["detail"]


# ==============================================================================
# 2. PoC 2: Salto de Directorio (Path Traversal)
# ==============================================================================

def test_poc2_reject_unix_path_traversal():
    """PoC 2: Un nombre de archivo con secuencias de salto '../' debe ser rechazado con 400."""
    valid_pdf_bytes = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"
    payload = _build_email_payload("../../../etc/passwd", "application/pdf", valid_pdf_bytes)

    response = client.post("/api/v1/emails/ingest", json=payload)
    assert response.status_code == 400
    assert "Path Traversal" in response.json()["detail"]


def test_poc2_reject_windows_path_traversal():
    """PoC 2b: Un nombre de archivo con secuencias de salto Windows '..\\..\\' debe ser rechazado con 400."""
    valid_pdf_bytes = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"
    payload = _build_email_payload(r"..\..\..\windows\system32\cmd.exe", "application/pdf", valid_pdf_bytes)

    response = client.post("/api/v1/emails/ingest", json=payload)
    assert response.status_code == 400
    assert "Path Traversal" in response.json()["detail"]


def test_poc2_reject_null_byte_injection():
    """PoC 2c: Inyección de Null Bytes (\\x00) en el nombre del archivo debe ser rechazada con 400."""
    valid_pdf_bytes = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"
    payload = _build_email_payload("incapacidad.pdf\x00.exe", "application/pdf", valid_pdf_bytes)

    response = client.post("/api/v1/emails/ingest", json=payload)
    assert response.status_code == 400
    assert "Path Traversal" in response.json()["detail"] or "seguridad" in response.json()["detail"].lower()


# ==============================================================================
# 3. PoC 3: Detección y Filtrado de Malware (EICAR & Webshells)
# ==============================================================================

def test_poc3_reject_eicar_antivirus_test_signature():
    """PoC 3: Inyección de la firma estándar de prueba antivirus EICAR en Base64 debe ser rechazada con 400."""
    eicar_bytes = b"X5O!P%@AP[4" + bytes([92]) + b"PZX54(P^)7CC)7}$" + b"EICAR-STANDARD-" + b"ANTIVIRUS-TEST-FILE" + b"!$H+H*"
    payload = _build_email_payload("prueba_eicar.pdf", "application/pdf", eicar_bytes)

    response = client.post("/api/v1/emails/ingest", json=payload)
    assert response.status_code == 400
    assert "Malware Detectado" in response.json()["detail"] or "EICAR" in response.json()["detail"]


def test_poc3_reject_embedded_php_webshell():
    """PoC 3b: Inyección de script webshell PHP embebido debe ser rechazada con 400."""
    webshell_bytes = b"%PDF-1.4\n<" + b"?php sys" + b"tem('whoami'); ?" + b">\n%%EOF"
    payload = _build_email_payload("webshell_incapacidad.pdf", "application/pdf", webshell_bytes)

    response = client.post("/api/v1/emails/ingest", json=payload)
    assert response.status_code == 400
    assert "Malware Detectado" in response.json()["detail"] or "malicioso" in response.json()["detail"].lower()


# ==============================================================================
# 4. PoC 4: Denegación de Servicio (DoS por Exceso de Memoria)
# ==============================================================================

def test_poc4_reject_oversized_attachment_exceeding_15mb():
    """PoC 4: Un adjunto que exceda el límite de 15MB debe ser rechazado con 413 Payload Too Large."""
    large_size = 16 * 1024 * 1024
    large_pdf_header = b"%PDF-1.4\n" + (b"A" * (large_size - 15)) + b"\n%%EOF"
    payload = _build_email_payload("archivo_masivo.pdf", "application/pdf", large_pdf_header)

    response = client.post("/api/v1/emails/ingest", json=payload)
    assert response.status_code == 413
    assert "Límite de Tamaño Excedido" in response.json()["detail"] or "Payload Too Large" in response.json()["detail"]


def test_poc4_middleware_blocks_content_length_exceeding_20mb():
    """PoC 4b: Petición HTTP con cabecera Content-Length > 20MB debe ser cortada inmediatamente por el middleware con 413."""
    headers = {"Content-Length": str(25 * 1024 * 1024)}  # 25 MB
    response = client.post(
        "/api/v1/emails/ingest",
        json={"source_provider": "OUTLOOK", "sender_email": "a@riwi.io", "subject": "Test", "body": "Test"},
        headers=headers
    )
    assert response.status_code == 413
    assert "Payload Too Large" in response.json()["detail"]


# ==============================================================================
# 5. Casos de Control Positivo: Evidencias Legítimas y Multipart
# ==============================================================================

def test_positive_control_valid_pdf():
    """Control Positivo: PDF legítimo con %PDF-1.4 debe procesarse exitosamente (200 OK)."""
    valid_pdf = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"
    payload = _build_email_payload("incapacidad_sura.pdf", "application/pdf", valid_pdf)

    response = client.post("/api/v1/emails/ingest", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["normalized_email"]["attachments"][0]["is_valid_evidence"] is True
    assert data["normalized_email"]["attachments"][0]["mime_type"] == "application/pdf"


def test_positive_control_valid_png():
    """Control Positivo: Imagen PNG legítima debe procesarse exitosamente (200 OK)."""
    valid_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
    payload = _build_email_payload("receta_medica.png", "image/png", valid_png)

    response = client.post("/api/v1/emails/ingest", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["normalized_email"]["attachments"][0]["mime_type"] == "image/png"


def test_positive_control_valid_jpeg():
    """Control Positivo: Imagen JPEG legítima con cabecera \\xff\\xd8\\xff debe procesarse exitosamente (200 OK)."""
    valid_jpeg = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb"
    payload = _build_email_payload("foto_incapacidad.jpg", "image/jpeg", valid_jpeg)

    response = client.post("/api/v1/emails/ingest", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["normalized_email"]["attachments"][0]["mime_type"] == "image/jpeg"


def test_positive_control_valid_webp():
    """Control Positivo: Imagen WEBP legítima (RIFF....WEBP) debe procesarse exitosamente (200 OK)."""
    valid_webp = b"RIFF\x1a\x00\x00\x00WEBPVP8 \x0e\x00\x00\x00/0\x00\x00\x00\x00\x00\x00\x00\x00"
    payload = _build_email_payload("soporte_clinico.webp", "image/webp", valid_webp)

    response = client.post("/api/v1/emails/ingest", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["normalized_email"]["attachments"][0]["mime_type"] == "image/webp"


def test_multi_attachment_fails_fast_if_any_is_malicious():
    """Si una petición contiene múltiples adjuntos y uno solo es malicioso, toda la transacción se interrumpe con 400."""
    valid_pdf = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"
    malicious_mz = bytes([77, 90, 144, 0, 3, 0, 0, 0])

    payload = {
        "source_provider": "OUTLOOK",
        "message_id": "sec-multi-test",
        "sender_email": "carlos.perez@riwi.io",
        "sender_name": "Carlos Pérez",
        "recipient_email": "tl.hse@riwi.io",
        "cc_emails": ["formacion.barranquilla@riwi.io"],
        "subject": "Justificación con dos adjuntos",
        "body": "Buenas tardes, adjunto incapacidad y otro archivo. CC 1045892341.",
        "attachments": [
            {
                "filename": "incapacidad_sura.pdf",
                "mime_type": "application/pdf",
                "data_base64": base64.b64encode(valid_pdf).decode("utf-8")
            },
            {
                "filename": "virus_camuflado.pdf",
                "mime_type": "application/pdf",
                "data_base64": base64.b64encode(malicious_mz).decode("utf-8")
            }
        ]
    }

    response = client.post("/api/v1/emails/ingest", json=payload)
    assert response.status_code == 400
    assert "Falsificación de Archivo" in response.json()["detail"] or "ejecutable" in response.json()["detail"].lower()
