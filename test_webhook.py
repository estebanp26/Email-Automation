import requests
import time

# Reemplaza con la URL de prueba de tu nodo en n8n
WEBHOOK_URL = "https://xclipsym.app.n8n.cloud/webhook-test/riwi-email-incoming"

CASOS_DIRECTOS = [
    {
        "sender": "carlos.mendoza@campuslands.net",
        "subject": "Ausencia por calamidad familiar - Carlos Mendoza",
        "body": "Hola, tuve una calamidad urgente y no pude asistir a la cohorte. Soy Carlos Mendoza CC: 1010101010",
        "has_attachments": False
    },
    {
        "sender": "laura.gomez@campuslands.net",
        "subject": "Problemas de transporte - Laura Gómez",
        "body": "No pude ir porque tuve un problema pagando y pedí un descuento en mi servicio.",
        "has_attachments": True
    }
]

def inyectar_webhook():
    print("Inyectando casos directamente al webhook de n8n...")
    for caso in CASOS_DIRECTOS:
        try:
            response = requests.post(WEBHOOK_URL, json=caso)
            print(f"✅ Enviado al webhook: {caso['subject']} | Status: {response.status_code}")
        except Exception as e:
            print(f"❌ Error de conexión con n8n: {e}")
        time.sleep(2)

if __name__ == "__main__":
    inyectar_webhook()