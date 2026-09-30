import requests
import base64

# Endpoint de ingestión según la arquitectura (usaremos el router de emails)
BASE_URL = "http://localhost:8000/api/v1/emails/ingest"

def test_file_upload_vulnerabilities():
    print("Iniciando Auditoría de Seguridad QA-01: File Uploads & Sanitization...\n")

    # Función para empaquetar el ataque en el modelo RawEmailInput esperado
    def build_payload(filename, fake_mime, real_content_bytes):
        return {
            "source_provider": "SIMULATION",
            "sender_email": "attacker@campuslands.net",
            "subject": "Justificación Médica Urgente",
            "body": "Adjunto evidencia para revisión. CC: 1010101010",
            "attachments": [
                {
                    "filename": filename,
                    "mime_type": fake_mime,
                    "data_base64": base64.b64encode(real_content_bytes).decode('utf-8')
                }
            ]
        }

    ataques = [
        {
            "nombre": "1. Falsificación de MIME Type (Ejecutable disfrazado de PDF)",
            "payload": build_payload("malware.pdf", "application/pdf", b"MZ\x90\x00\x03\x00\x00\x00_hacked"),
            "descripcion": "Verifica si el backend inspecciona Magic Bytes o confía en la extensión '.pdf'."
        },
        {
            "nombre": "2. Path Traversal (Salto de directorio)",
            "payload": build_payload("../../../etc/passwd", "application/pdf", b"%PDF-1.4 archivo real"),
            "descripcion": "Intenta sobrescribir archivos del sistema retrocediendo carpetas en el nombre."
        },
        {
            "nombre": "3. EICAR Test File (Firma de malware estándar en Base64)",
            "payload": build_payload("eicar.pdf", "application/pdf", b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"),
            "descripcion": "Firma estándar inofensiva. Todo sistema de seguridad debe rechazarla con 400/422."
        },
        {
            "nombre": "4. Exceso de Memoria (Bypass de Tamaño)",
            # Simulamos un Base64 enorme para probar si corta la conexión o intenta decodificar en memoria
            "payload": build_payload("crash_test.pdf", "application/pdf", b"%PDF-1.4 " + b"A" * (20 * 1024 * 1024)),
            "descripcion": "Archivo de 20MB para probar si revienta el límite (MAX_ATTACHMENT_SIZE_BYTES)."
        }
    ]

    for ataque in ataques:
        print(f"Probando: {ataque['nombre']}")
        try:
            response = requests.post(BASE_URL, json=ataque['payload'])
            
            # Criterio QA-01: El ataque debe ser RECHAZADO (400, 422 o 413)
            if response.status_code in [400, 422, 413]:
                print(f"✅ BLOQUEADO EXITOSAMENTE (Status {response.status_code})")
            else:
                print(f"❌ VULNERABILIDAD DETECTADA! (Status {response.status_code})")
                print(f"Detalle: El backend aceptó el archivo malicioso.")
        except Exception as e:
            print(f"⚠️ Error de conexión: {e}")
        print("-" * 60)

if __name__ == "__main__":
    test_file_upload_vulnerabilities()