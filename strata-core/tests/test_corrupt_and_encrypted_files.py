#!/usr/bin/env python3
"""
test_corrupt_and_encrypted_files.py
Prueba unitaria de Sub-tarea 1: Resiliencia ante archivos corruptos, cifrados o incompatibles.
Verifica que Strata Core NUNCA lance un error HTTP 500 y responda siempre un JSON estructurado
100% compliant con evaluation_schema.json y requiere_revision_manual = True.
"""

import sys
import os
import asyncio
import json
import tempfile
import jsonschema
import pytest
from unittest.mock import MagicMock
import pymupdf as fitz

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import server
SCHEMA_PATH = os.path.join(BASE_DIR, "schemas", "evaluation_schema.json")


class MockUploadFile:
    def __init__(self, filename: str, content: bytes):
        self.filename = filename
        self._temp = tempfile.NamedTemporaryFile(delete=False)
        self._temp.write(content)
        self._temp.seek(0)
        self.file = self._temp

    def cleanup(self):
        try:
            self._temp.close()
            if os.path.exists(self._temp.name):
                os.remove(self._temp.name)
        except OSError:
            pass


@pytest.mark.asyncio
async def test_corrupt_file_handling():
    print("\n" + "=" * 70)
    print("🧪 TEST SUB-TAREA 1: MANEJO DE ARCHIVOS CORRUPTOS, PROTEGIDOS E INCOMPATIBLES")
    print("=" * 70)

    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = json.load(f)

    # 1. Caso A: Archivo binario totalmente corrupto con extensión .pdf
    corrupt_content = b"\x00\xff\xfe\x12NOT_A_REAL_PDF_DATA_GARBAGE\x00\x00"
    mock_corrupt = MockUploadFile("danado.pdf", corrupt_content)

    try:
        # Mock de request HTTP real para verificar que no devuelva status 500
        mock_http_request = MagicMock()
        mock_http_request.headers = {"content-type": "multipart/form-data"}
        mock_http_request.form = asyncio.iscoroutinefunction(mock_http_request.form)

        res_obj = await server.evaluate_excuse(
            request=None,
            file=mock_corrupt,
            email_subject="Mi excusa médica",
            email_body="Adjunto soporte médico"
        )

        # Validación de contrato
        jsonschema.validate(instance=res_obj, schema=schema)
        print("  [OK] Caso 1 (PDF Corrupto): JSON cumple 100% el schema.")
        assert res_obj["valido"] is False, "El veredicto debe ser false para archivo corrupto"
        assert res_obj["requiere_revision_manual"] is True, "Debe requerir revisión manual"
        assert res_obj["confianza_score"] == 0.0, "Confianza debe ser 0.0"
        assert "dañado" in res_obj["motivo_decision"].lower() or "corrupto" in res_obj["motivo_decision"].lower()
        print(f"  • Motivo: {res_obj['motivo_decision']}")

    finally:
        mock_corrupt.cleanup()

    # 2. Caso B: Archivo con extensión no soportada (.exe o .docx)
    mock_unsupported = MockUploadFile("soporte.exe", b"MZ\x90\x00executable")
    try:
        res_obj2 = await server.evaluate_excuse(
            request=None,
            file=mock_unsupported,
            email_subject="Excusa ejecutoria",
            email_body="Adjunto archivo"
        )
        jsonschema.validate(instance=res_obj2, schema=schema)
        print("  [OK] Caso 2 (Formato no soportado): JSON cumple 100% el schema.")
        assert res_obj2["valido"] is False
        assert res_obj2["requiere_revision_manual"] is True
        assert "no admitido" in res_obj2["motivo_decision"].lower() or "no compatible" in res_obj2["motivo_decision"].lower()
        print(f"  • Motivo: {res_obj2['motivo_decision']}")
    finally:
        mock_unsupported.cleanup()

    # 3. Caso C: PDF Cifrado / Protegido con Contraseña
    # Generamos un PDF encriptado con contraseña usando PyMuPDF
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Datos medicos confidenciales protegidos")
    encrypt_perm = fitz.PDF_PERM_ACCESSIBILITY
    encrypted_bytes = doc.tobytes(
        encryption=fitz.PDF_ENCRYPT_AES_256,
        user_pw="clave_secreta_eps",
        owner_pw="clave_propietario",
        permissions=encrypt_perm
    )
    doc.close()

    mock_encrypted = MockUploadFile("incapacidad_protegida.pdf", encrypted_bytes)
    try:
        res_obj3 = await server.evaluate_excuse(
            request=None,
            file=mock_encrypted,
            email_subject="Incapacidad protegida por EPS",
            email_body="Adjunto incapacidad con contraseña de SURA"
        )
        jsonschema.validate(instance=res_obj3, schema=schema)
        print("  [OK] Caso 3 (PDF Protegido con clave): JSON cumple 100% el schema.")
        assert res_obj3["valido"] is False
        assert res_obj3["requiere_revision_manual"] is True
        assert "protegido" in res_obj3["motivo_decision"].lower() or "contraseña" in res_obj3["motivo_decision"].lower()
        print(f"  • Motivo: {res_obj3['motivo_decision']}")
    finally:
        mock_encrypted.cleanup()

    # 4. Caso D: Petición HTTP real vía FastAPI TestClient verificando status_code = 200 (NUNCA 500)
    from fastapi.testclient import TestClient
    client = TestClient(server.app)

    response = client.post(
        "/api/evaluate-excuse",
        files={"file": ("archivo_roto.pdf", b"\x00\x01\x02\x03corrupt_bytes", "application/pdf")},
        data={"email_subject": "Soporte roto", "email_body": "Envío documento"}
    )
    assert response.status_code == 200, f"Debe responder 200 OK en lugar de 500, obtenido: {response.status_code}"
    body = response.json()
    jsonschema.validate(instance=body, schema=schema)
    assert body["valido"] is False
    assert body["requiere_revision_manual"] is True
    assert "dañado" in body["motivo_decision"].lower() or "corrupto" in body["motivo_decision"].lower()
    print(f"  [OK] Caso 4 (Petición HTTP real multipart con archivo corrupto): Retorna HTTP {response.status_code} (NUNCA 500).")

    print("\n✅ SUB-TAREA 1 VALIDADA AL 100%: Tolerancia total a fallos y eliminación de HTTP 500.")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_corrupt_file_handling())
