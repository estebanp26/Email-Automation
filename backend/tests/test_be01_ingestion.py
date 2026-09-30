import pytest
import base64
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.ingestion import EmailNormalizationService, email_normalizer
from backend.app.schemas.email import RawEmailInput, RawAttachmentInput

client = TestClient(app)


def test_clean_sender_rfc_format():
    email, name = EmailNormalizationService.clean_sender("carlos.perez@riwi.io", "Carlos Pérez")
    assert email == "carlos.perez@riwi.io"
    assert name == "Carlos Pérez"

    # Encapsulated format
    email2, name2 = EmailNormalizationService.clean_sender('"Laura Gómez" <laura.gomez@riwi.io>')
    assert email2 == "laura.gomez@riwi.io"
    assert name2 == "Laura Gómez"

    # Only email, infer name
    email3, name3 = EmailNormalizationService.clean_sender("andres.felipe.mendoza@riwi.io")
    assert email3 == "andres.felipe.mendoza@riwi.io"
    assert name3 == "Andres Felipe Mendoza"


def test_clean_subject_strips_reply_and_forward_prefixes():
    raw, clean = EmailNormalizationService.clean_subject("Re: Fwd: RV: [Riwi] Justificante de inasistencia")
    assert clean == "Justificante de inasistencia"


def test_clean_html_and_strip_quoted_threads():
    html_body = """
    <html>
        <body>
            <p>Buenos d&iacute;as Team Leader,</p>
            <p>El d&iacute;a de ayer no pude asistir por <strong>incapacidad m&eacute;dica</strong> de la EPS.</p>
            <br>
            <p>Adjunto documento soporte. C&eacute;dula: 1045892341.</p>
            <hr>
            <div>
                De: Coordinación Riwi <coord@riwi.io><br>
                Enviado el: lunes 21 de septiembre de 2026<br>
                Para: Coder <coder@riwi.io><br>
                Asunto: Notificaciones académicas<br>
                <p>Texto viejo del hilo anterior que debe eliminarse...</p>
            </div>
        </body>
    </html>
    """
    cleaned = EmailNormalizationService.clean_html_and_text(html_body)
    assert "Buenos días Team Leader" in cleaned
    assert "incapacidad médica" in cleaned
    assert "1045892341" in cleaned
    assert "Texto viejo del hilo anterior" not in cleaned
    assert "<p>" not in cleaned


def test_formacion_cc_validation():
    # Caso 1: Sí contiene copia a formacion
    ccs, has_cc = EmailNormalizationService.check_formacion_cc(
        recipient="tl@riwi.io",
        cc_emails=["formacion.barranquilla@riwi.io", "otra.area@riwi.io"]
    )
    assert has_cc is True
    assert "formacion.barranquilla@riwi.io" in ccs

    # Caso 2: No contiene copia obligatoria
    ccs2, has_cc2 = EmailNormalizationService.check_formacion_cc(
        recipient="tl@riwi.io",
        cc_emails=["amigo@gmail.com"]
    )
    assert has_cc2 is False


def test_normalize_valid_attachment():
    sample_content = b"%PDF-1.4 sample pdf content for test"
    b64_content = base64.b64encode(sample_content).decode("utf-8")

    raw_att = RawAttachmentInput(
        filename="incapacidad_eps.pdf",
        mime_type="application/pdf",
        data_base64=b64_content
    )

    norm_att = EmailNormalizationService.normalize_attachment(raw_att)
    assert norm_att.filename == "incapacidad_eps.pdf"
    assert norm_att.mime_type == "application/pdf"
    assert norm_att.size_bytes == len(sample_content)
    assert norm_att.is_valid_evidence is True
    assert norm_att.sha256_hash != ""


def test_normalize_invalid_attachment_extension():
    sample_content = b"malicious binary content"
    b64_content = base64.b64encode(sample_content).decode("utf-8")

    raw_att = RawAttachmentInput(
        filename="script_virus.exe",
        data_base64=b64_content
    )

    norm_att = EmailNormalizationService.normalize_attachment(raw_att)
    assert norm_att.is_valid_evidence is False
    assert "Extensión no permitida" in norm_att.validation_error


def test_preliminary_extraction_pptx_motives_and_sensitivity():
    # Incapacidad médica
    text_med = "No pude asistir el 2026-09-28 por incapacidad médica de la EPS Sura. Cédula 1045892341 Clan Turing mañana."
    res_med = EmailNormalizationService.extract_preliminary_data(text_med, "Excusa Médica")
    assert res_med.suspected_motive == "incapacidad_medica"
    assert res_med.detected_cedula == "1045892341"
    assert res_med.detected_clan == "Clan Turing"
    assert "2026-09-28" in res_med.detected_dates
    assert res_med.is_sensitive is False

    # Situación emocional crítica (Sensible - Slide 5 PPTX)
    text_sens = "Estimado TL, estoy sufriendo una crisis de pánico y depresión severa. CC 1029384756."
    res_sens = EmailNormalizationService.extract_preliminary_data(text_sens, "Situación Urgente")
    assert res_sens.suspected_motive == "situacion_emocional_critica"
    assert res_sens.is_sensitive is True


def test_api_health_endpoint():
    response = client.get("/api/v1/emails/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "OUTLOOK" in data["supported_providers"]


def test_api_ingest_endpoint_full_flow():
    payload = {
        "source_provider": "OUTLOOK",
        "message_id": "test-msg-123",
        "sender_email": "carlos.perez@riwi.io",
        "sender_name": "Carlos Pérez",
        "recipient_email": "tl.desarrollo@riwi.io",
        "cc_emails": ["formacion.barranquilla@riwi.io"],
        "subject": "Re: Justificación por Cita Médica - 1045892341",
        "body": "Buenas tardes, adjunto cita médica para el día 2026-09-29. Soy del Clan Gosling.",
        "attachments": [
            {
                "filename": "comprobante_cita.pdf",
                "mime_type": "application/pdf",
                "data_base64": base64.b64encode(b"%PDF-1.4 Dummy PDF content for test").decode("utf-8")
            }
        ]
    }

    response = client.post("/api/v1/emails/ingest", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["normalized_email"]["sender_email"] == "carlos.perez@riwi.io"
    assert data["normalized_email"]["has_formacion_cc"] is True
    assert data["normalized_email"]["preliminary_extraction"]["detected_cedula"] == "1045892341"
    assert data["normalized_email"]["preliminary_extraction"]["suspected_motive"] == "cita_medica"
    assert len(data["normalized_email"]["attachments"]) == 1


def test_api_simulate_endpoint():
    response = client.post("/api/v1/emails/simulate?scenario=incapacidad_sura")
    assert response.status_code == 200
    data = response.json()
    assert data["normalized_email"]["sender_email"] == "carlos.perez@riwi.io"
    assert data["normalized_email"]["preliminary_extraction"]["suspected_motive"] == "incapacidad_medica"
