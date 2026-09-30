import base64
from locust import HttpUser, task, between

class HseLoadTestUser(HttpUser):
    # Pausa entre peticiones de un mismo usuario (si se ejecuta por tiempo prolongado)
    wait_time = between(1, 2)

    @task
    def enviar_justificacion_concurrente(self):
        # Simulamos un PDF ligero en Base64
        pdf_falso = b"%PDF-1.4\nFalso contenido PDF para estresar el sistema de colas..."
        pdf_b64 = base64.b64encode(pdf_falso).decode('utf-8')

        payload = {
            "source_provider": "SIMULATION",
            "sender_email": "estres_test@campuslands.net",
            "subject": "Excusa Médica - Prueba de Carga",
            "body": "Enviando ráfaga concurrente para saturar Strata Core. CC: 1010101010",
            "attachments": [
                {
                    "filename": "evidencia_estres.pdf",
                    "mime_type": "application/pdf",
                    "data_base64": pdf_b64
                }
            ]
        }

        # Lanzamos el POST y evaluamos si el servidor sobrevive
        with self.client.post("/api/v1/emails/ingest", json=payload, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Caída del servidor: Status {response.status_code} - {response.text[:50]}")