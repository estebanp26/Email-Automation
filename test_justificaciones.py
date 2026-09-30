import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import random
import time

# 1. EDITA TUS CUENTAS AQUÍ
REMITENTES = [
    {"email": "diazvergara.arley@gmail.com", "password": "swarfoqvqmuflbms", "smtp": "smtp.gmail.com", "port": 587},
    {"email": "arcedive1999@gmail.com", "password": "tqbhralakomiixoo", "smtp": "smtp.gmail.com", "port": 587}
]

DESTINATARIO = "skullhelhestrendr@gmail.com"

# 2. CASOS ADAPTADOS A LOS NOMBRES DEL ARCHIVO 002_SEED_DATA.SQL
CASOS_DE_PRUEBA = [
    {
        # Caso QA-002: Falla de calamidad sin adjunto. Forzado a revisión manual.
        "asunto": "Ausencia por calamidad familiar - Carlos Mendoza",
        "cuerpo": "Hola, tuve una calamidad urgente y no pude asistir a la cohorte. Soy Carlos Mendoza.",
        "adjuntos": []
    },
    {
        # Caso QA-004: Múltiples adjuntos. n8n ignorará el segundo adjunto.
        "asunto": "Justificación médica y exámenes de Mariana Torres",
        "cuerpo": "Adjunto receta médica y el certificado de la clínica de Tigo UNE. Atentamente, Mariana Torres.",
        "adjuntos": ["receta_medica_mtorres.pdf", "certificado_incapacidad_mtorres.pdf"]
    },
    {
        # Caso QA-005 y QA-007: Conflicto de Regex con celulares y fallo por Tildes.
        # En la BD está como "Diego Ramírez". Aquí mandamos "Diego Ramirez" (sin tilde) y un celular.
        "asunto": "Falta del día de hoy - Diego Ramirez",
        "cuerpo": "Estuve muy enfermo. Atentamente,\nDiego Ramirez.\nTel: 3001234567",
        "adjuntos": ["soporte_medico_diego.pdf"]
    },
    {
        # Caso QA-006: Falso Positivo de Spam por la palabra "descuento".
        "asunto": "Problemas de transporte - Laura Gómez",
        "cuerpo": "No pude ir porque tuve un problema pagando y pedí un descuento en mi servicio. Soy Laura Gómez.",
        "adjuntos": ["soporte_transporte_laura.pdf"]
    },
    {
        # Happy Path: Caso ideal, limpio y directo.
        "asunto": "Justificación de inasistencia por cita médica",
        "cuerpo": "Buenos días, adjunto mi excusa correspondiente a mi cita en Dentisalud. Atentamente, Andrés Felipe Castro.",
        "adjuntos": ["excusa_odontologica_andres.pdf"]
    }
]

def enviar_correo(remitente, caso):
    msg = MIMEMultipart()
    msg['From'] = remitente['email']
    msg['To'] = DESTINATARIO
    msg['Subject'] = caso['asunto']
    msg.attach(MIMEText(caso['cuerpo'], 'plain'))

    # Generador de PDFs falsos en memoria para simular los adjuntos
    for nombre_adjunto in caso['adjuntos']:
        pdf_falso = MIMEApplication(b"%PDF-1.4 Falso contenido de prueba", _subtype="pdf")
        pdf_falso.add_header('Content-Disposition', 'attachment', filename=nombre_adjunto)
        msg.attach(pdf_falso)

    try:
        server = smtplib.SMTP(remitente['smtp'], remitente['port'])
        server.starttls()
        server.login(remitente['email'], remitente['password'])
        server.send_message(msg)
        server.quit()
        print(f"✅ Enviado: {caso['asunto']} | Desde: {remitente['email']}")
    except Exception as e:
        print(f"❌ Error al enviar '{caso['asunto']}': {e}")

if __name__ == "__main__":
    print("Despachando casos de prueba basados en datos semilla (002_seed_data.sql)...")
    for caso in CASOS_DE_PRUEBA:
        remitente = random.choice(REMITENTES)
        enviar_correo(remitente, caso)
        time.sleep(3)
    print("Pruebas finalizadas. Monitorea n8n y el Dashboard.")