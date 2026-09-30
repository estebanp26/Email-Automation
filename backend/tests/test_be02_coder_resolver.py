import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.coder_resolver import coder_resolver
from backend.app.services.ingestion import email_normalizer
from backend.app.schemas.coder import CoderIdentificationQuery
from backend.app.schemas.email import RawEmailInput

client = TestClient(app)


def test_master_coders_loaded():
    """Verifica que el índice maestro contenga los 297 coders reales de Riwi."""
    assert len(coder_resolver._coders_list) >= 297


def test_identify_by_exact_email():
    query = CoderIdentificationQuery(email="jose.acevedo@riwi.io")
    result = coder_resolver.identify_coder(query)

    assert result.identification_status == "IDENTIFIED"
    assert result.matched_by == "EMAIL"
    assert result.confidence == 1.0
    assert result.coder is not None
    assert result.coder.full_name == "Jose Luis Acevedo Vargas"
    assert result.coder.cedula == "1000000001"


def test_identify_by_exact_cedula():
    # Buscar por cédula sin enviar correo
    query = CoderIdentificationQuery(cedula="1000000002")
    result = coder_resolver.identify_coder(query)

    assert result.identification_status == "IDENTIFIED"
    assert result.matched_by == "CEDULA"
    assert result.confidence == 1.0
    assert result.coder is not None
    assert result.coder.full_name == "Andrea Mariette Ahumada Borja"
    assert result.coder.email == "andrea.ahumada@riwi.io"


def test_identify_by_fuzzy_name():
    # Buscar con variación de nombre o sin tildes
    query = CoderIdentificationQuery(name="Jose Luis Acevedo")
    result = coder_resolver.identify_coder(query)

    assert result.identification_status == "IDENTIFIED"
    assert result.matched_by == "FUZZY_NAME"
    assert result.confidence >= 0.82
    assert result.coder.cedula == "1000000001"


def test_fallback_coder_not_found():
    query = CoderIdentificationQuery(
        email="desconocido.externo@hotmail.com",
        cedula="9999999999",
        name="Persona Ficticia Desconocida"
    )
    result = coder_resolver.identify_coder(query)

    assert result.identification_status == "CODER_NOT_FOUND"
    assert result.matched_by == "NONE"
    assert result.confidence == 0.0
    assert result.coder is None


def test_resolve_from_normalized_email():
    raw_email = RawEmailInput(
        source_provider="OUTLOOK",
        sender_email="andrea.zarate@riwi.io",
        sender_name="Andrea Zárate",
        subject="Justificación de inasistencia",
        body="Buenas tardes, soy Andrea Zárate con CC 1000000297 del Clan Analítica."
    )
    norm = email_normalizer.normalize(raw_email)
    result = coder_resolver.resolve_from_normalized_email(norm)

    assert result.identification_status == "IDENTIFIED"
    assert result.coder.cedula == "1000000297"
    assert result.coder.full_name == "Andrea Valentina Zárate Rubio"


def test_api_resolve_endpoint():
    payload = {"email": "cristian.albor@riwi.io"}
    response = client.post("/api/v1/coders/resolve", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["identification_status"] == "IDENTIFIED"
    assert data["matched_by"] == "EMAIL"
    assert data["coder"]["cedula"] == "1000000004"


def test_api_count_endpoint():
    response = client.get("/api/v1/coders/count")
    assert response.status_code == 200
    data = response.json()
    assert data["total_coders"] >= 297
    assert data["status"] == "ready"


def test_api_search_endpoint():
    response = client.get("/api/v1/coders/search?q=Acevedo")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert "Acevedo" in data[0]["full_name"]
