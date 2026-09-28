#!/usr/bin/env python3
"""
send_10_justifications.py
Envía exactamente 10 justificaciones realistas al webhook de n8n:
- 4 Posiblemente Válidas (Aprobadas)
- 3 Posiblemente Inválidas (Rechazadas)
- 3 Requieren Revisión Manual (Calamidad sin soporte, fórmula médica, corte técnico)
"""

import os
import sys
import time
import json
import base64
from datetime import datetime, date, timedelta, timezone
import urllib.request
import urllib.error
import psycopg2

def create_mock_pdf_base64(title: str, coder_name: str, doc_id: str, dates_text: str) -> str:
    pdf_content = f"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >> endobj
4 0 obj << /Length 200 >>
stream
BT
/F1 14 Tf
50 720 Td ({title}) Tj
/F1 11 Tf
50 680 Td (Paciente: {coder_name}) Tj
50 660 Td (Documento: {doc_id}) Tj
50 640 Td (Periodo: {dates_text}) Tj
50 620 Td (Certificado de Incapacidad Medico Legal - Entidad Promotora de Salud) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000214 00000 n 
trailer << /Size 5 /Root 1 0 R >>
startxref
465
%%EOF
"""
    return base64.b64encode(pdf_content.encode("latin-1")).decode("ascii")

def get_db_coders():
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        dbname="hse_email_automation",
        user="hse_admin",
        password=os.getenv("POSTGRES_PASSWORD", "hse_segura_123")
    )
    cur = conn.cursor()
    cur.execute("SELECT id, full_name, email, cedula, route FROM coders WHERE is_active = true ORDER BY id LIMIT 10;")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def build_10_cases(coders):
    today = date.today()
    cases = []

    # =========================================================================
    # GRUPO 1: POSIBLEMENTE VÁLIDOS (APROBADOS) - 4 CASOS
    # =========================================================================
    # Caso 1: Incapacidad SURA EPS
    c = coders[0]
    dt1 = today.strftime("%d/%m/%Y")
    dt2 = (today + timedelta(days=2)).strftime("%d/%m/%Y")
    cases.append({
        "target_category": "POSIBLEMENTE_VALIDO",
        "sender_name": c[1],
        "sender_email": c[2],
        "email_subject": f"Justificación médica - 2 días de incapacidad - {c[1]}",
        "email_body": f"""Cordial saludo Equipo de Bienestar HSE RIWI,

Me dirijo a ustedes para justificar mi inasistencia a la jornada formativa de la ruta {c[4]}.
Presenté complicaciones de salud diagnosticadas por SURA EPS (Rinofaringitis aguda, CIE-10: J00).

Detalles de la atención:
- Coder: {c[1]}
- Documento: {c[3]}
- Días de incapacidad: 2 días (desde {dt1} hasta {dt2})
- Médico tratante: Dra. Camila Restrepo (RM 45892-Medellín)
- Recomendación: Reposo e hidratación por cuadro viral agudo.

Adjunto certificado de incapacidad EPS emitido oficialmente en PDF.

Atentamente,
{c[1]}
Coder RIWI - {c[4]}""",
        "attachments": [{
            "filename": f"incapacidad_{c[3]}_sura.pdf",
            "mime_type": "application/pdf",
            "data_base64": create_mock_pdf_base64("CERTIFICADO MEDICO SURA EPS", c[1], c[3], f"{dt1} a {dt2}")
        }]
    })

    # Caso 2: Incapacidad Sanitas EPS
    c = coders[1]
    dt1 = today.strftime("%d/%m/%Y")
    dt2 = (today + timedelta(days=3)).strftime("%d/%m/%Y")
    cases.append({
        "target_category": "POSIBLEMENTE_VALIDO",
        "sender_name": c[1],
        "sender_email": c[2],
        "email_subject": f"Incapacidad médica EPS Sanitas 3 días - {c[1]}",
        "email_body": f"""Buenas tardes Equipo HSE,

Por medio de la presente radico mi incapacidad médica expedida por EPS Sanitas debido a gastroenteritis aguda (CIE-10: K29.7).
- Nombre: {c[1]}
- Cédula: {c[3]}
- Periodo: {dt1} al {dt2}
- Diagnóstico: Infección gastrointestinal con indicación de reposo en casa.

Adjunto soporte oficial emitido por la clínica Sanitas.

Muchas gracias,
{c[1]}""",
        "attachments": [{
            "filename": f"incapacidad_{c[3]}_sanitas.pdf",
            "mime_type": "application/pdf",
            "data_base64": create_mock_pdf_base64("CERTIFICADO EPS SANITAS", c[1], c[3], f"{dt1} a {dt2}")
        }]
    })

    # Caso 3: Incapacidad Nueva EPS
    c = coders[2]
    dt1 = today.strftime("%d/%m/%Y")
    dt2 = (today + timedelta(days=2)).strftime("%d/%m/%Y")
    cases.append({
        "target_category": "POSIBLEMENTE_VALIDO",
        "sender_name": c[1],
        "sender_email": c[2],
        "email_subject": f"Radicación de incapacidad médica Nueva EPS - {c[1]}",
        "email_body": f"""Hola Paola y equipo de HSE,

Adjunto constancia de incapacidad médica expedida por Nueva EPS por cuadro de lumbago severo (CIE-10: M54.5).
Fechas cubiertas: {dt1} a {dt2}.
Coder: {c[1]} (CC {c[3]}).

El documento oficial con firma y registro médico se encuentra anexo en PDF.

Saludos cordiales,
{c[1]}""",
        "attachments": [{
            "filename": f"incapacidad_{c[3]}_nueva_eps.pdf",
            "mime_type": "application/pdf",
            "data_base64": create_mock_pdf_base64("CERTIFICADO NUEVA EPS", c[1], c[3], f"{dt1} a {dt2}")
        }]
    })

    # Caso 4: Constancia de Asistencia a Cita Médica
    c = coders[3]
    dt1 = today.strftime("%d/%m/%Y")
    cases.append({
        "target_category": "POSIBLEMENTE_VALIDO",
        "sender_name": c[1],
        "sender_email": c[2],
        "email_subject": f"Constancia de Asistencia a Cita Médica Odontológica - {c[1]}",
        "email_body": f"""Buenos días Paola y equipo HSE,

El día de hoy {dt1} asistí a una cita médica prioritaria y procedimiento odontológico en Salud Total EPS en horario matutino.
Atendido por: Dra. Diana Patricia Osorio (RM 31405).
Coder: {c[1]} (CC {c[3]}).

Adjunto el comprobante de asistencia emitido por la entidad de salud. Ya me encuentro al día con el material formativo.

Muchas gracias,
{c[1]}""",
        "attachments": [{
            "filename": f"constancia_cita_{c[3]}.pdf",
            "mime_type": "application/pdf",
            "data_base64": create_mock_pdf_base64("CONSTANCIA DE CITA MEDICA SALUD TOTAL", c[1], c[3], dt1)
        }]
    })

    # =========================================================================
    # GRUPO 2: POSIBLEMENTE INVÁLIDOS (RECHAZADOS) - 3 CASOS
    # =========================================================================
    # Caso 5: Radicación extemporánea (semana pasada)
    c = coders[4]
    dt_old = (today - timedelta(days=7)).strftime("%d/%m/%Y")
    cases.append({
        "target_category": "POSIBLEMENTE_INVALIDO",
        "sender_name": c[1],
        "sender_email": c[2],
        "email_subject": f"Certificado con fecha de la semana pasada - {c[1]}",
        "email_body": f"""Equipo HSE,
Buenos días, adjunto la incapacidad que tuve la semana pasada el día {dt_old} que se me olvidó enviar a tiempo.
Es una incapacidad vencida que no alcancé a radicar oportunamente.
Coder: {c[1]} (CC {c[3]}).

Quedo atento si aún es posible validarla.
Saludos.""",
        "attachments": [{
            "filename": f"incapacidad_vencida_{c[3]}.pdf",
            "mime_type": "application/pdf",
            "data_base64": create_mock_pdf_base64("CERTIFICADO EXTEMPORANEO", c[1], c[3], dt_old)
        }]
    })

    # Caso 6: Justificación extemporánea fuera del plazo de 48h
    c = coders[5]
    dt_old = (today - timedelta(days=6)).strftime("%d/%m/%Y")
    cases.append({
        "target_category": "POSIBLEMENTE_INVALIDO",
        "sender_name": c[1],
        "sender_email": c[2],
        "email_subject": f"Incapacidad extemporánea radicada fuera de tiempo - {c[1]}",
        "email_body": f"""Cordial saludo Equipo de Bienestar HSE,

Envío soporte médico vencido correspondiente al día {dt_old} de la semana pasada.
No pude enviarlo en el plazo estipulado de 48 horas reglamentarias.
Coder: {c[1]} - CC {c[3]}.

Agradezco su revisión aunque esté extemporáneo.
{c[1]}""",
        "attachments": [{
            "filename": f"soporte_extemporaneo_{c[3]}.pdf",
            "mime_type": "application/pdf",
            "data_base64": create_mock_pdf_base64("SOPORTE FUERA DE PLAZO", c[1], c[3], dt_old)
        }]
    })

    # Caso 7: Incapacidad antigua sin justificación
    c = coders[6]
    dt_old = (today - timedelta(days=8)).strftime("%d/%m/%Y")
    cases.append({
        "target_category": "POSIBLEMENTE_INVALIDO",
        "sender_name": c[1],
        "sender_email": c[2],
        "email_subject": f"Radicación extemporánea justificación médica vencida - {c[1]}",
        "email_body": f"""Buenas tardes,
Reporto justificación de inasistencia de la semana pasada ({dt_old}).
El certificado médico ya está vencido pero requiero que conste en mi expediente de formación.
Documento: {c[3]} | Coder: {c[1]}.

Atentamente,
{c[1]}""",
        "attachments": []
    })

    # =========================================================================
    # GRUPO 3: REVISIÓN MANUAL - 3 CASOS
    # =========================================================================
    # Caso 8: Calamidad doméstica sin soporte adjunto
    c = coders[7]
    cases.append({
        "target_category": "REVISION_MANUAL",
        "sender_name": c[1],
        "sender_email": c[2],
        "email_subject": f"Novedad por Calamidad Doméstica Urgente - {c[1]}",
        "email_body": f"""Buenas tardes Equipo HSE y Paola,

Presento reporte por una grave calamidad doméstica familiar ocurrida en horas de la mañana (inundación de vivienda por rotura de tubería principal y daño en enseres).
Por atender la emergencia no pude conectarme a la sesión formativa.
Coder: {c[1]} | Cédula: {c[3]} | Ruta: {c[4]}.

No cuento con documento probatorio formal en este momento. Solicito orientación de la Team Leader.

Atentamente,
{c[1]}""",
        "attachments": []
    })

    # Caso 9: Fórmula médica de farmacia (no es incapacidad EPS con días de reposo)
    c = coders[8]
    cases.append({
        "target_category": "REVISION_MANUAL",
        "sender_name": c[1],
        "sender_email": c[2],
        "email_subject": f"Formula médica y recibo de farmacia - {c[1]}",
        "email_body": f"""Equipo HSE,
Estuve enfermo esta mañana y fui al médico particular. No me dieron formato de incapacidad EPS, pero adjunto la fórmula y orden médica de la farmacia con los medicamentos recetados.
Coder: {c[1]} (CC {c[3]}).

Agradezco si con la fórmula y prescripción médica me pueden justificar la ausencia.
Saludos,
{c[1]}""",
        "attachments": [{
            "filename": f"formula_farmacia_{c[3]}.pdf",
            "mime_type": "application/pdf",
            "data_base64": create_mock_pdf_base64("FORMULA MEDICA - FARMACIA", c[1], c[3], today.strftime("%d/%m/%Y"))
        }]
    })

    # Caso 10: Falla técnica / corte de fluido eléctrico y fibra óptica
    c = coders[9]
    cases.append({
        "target_category": "REVISION_MANUAL",
        "sender_name": c[1],
        "sender_email": c[2],
        "email_subject": f"Reporte de Novedad Técnica por Corte de Fluido y Conectividad - {c[1]}",
        "email_body": f"""Hola equipo de HSE y Formación,

Informo que en mi sector residencial se presentó un corte no programado de energía eléctrica y caída general de la fibra óptica de internet desde las 8:00 AM.
Radicado preliminar con la empresa proveedora de energía.
Fecha del evento: {today.strftime("%d/%m/%Y")}.
Nombre: {c[1]} | Documento: {c[3]} | Ruta: {c[4]}.

Derivo a revisión para validación de la contingencia técnica.

Saludos,
{c[1]}""",
        "attachments": []
    })

    return cases

def send_cases(cases, target_url="http://localhost:5678/webhook/riwi-email-incoming"):
    print("=" * 70)
    print("  DESPACHANDO 10 JUSTIFICACIONES BALANCEADAS AL SISTEMA HSE RIWI   ")
    print("=" * 70)
    
    results = []
    for idx, item in enumerate(cases, 1):
        payload = {
            "source_provider": "OUTLOOK" if idx % 2 == 0 else "GMAIL",
            "message_id": f"<justif_batch10_{idx}_{int(time.time())}_{item['sender_name'].split()[0].lower()}@riwi.io>",
            "conversation_id": f"conv_batch10_{idx}_{int(time.time())}",
            "sender_email": item["sender_email"],
            "sender_name": item["sender_name"],
            "email_subject": item["email_subject"],
            "email_body": item["email_body"],
            "received_at": datetime.now(timezone.utc).isoformat(),
            "attachments": item["attachments"],
            "has_attachments": len(item["attachments"]) > 0
        }

        req_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            target_url,
            data=req_bytes,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        t_start = time.time()
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                elapsed = time.time() - t_start
                print(f"  [✓] #{idx:02d} [{item['target_category']}] -> {item['sender_name']} | {elapsed:.2f}s | HTTP {resp.status}")
                results.append({"idx": idx, "success": True, "category": item["target_category"]})
        except Exception as e:
            elapsed = time.time() - t_start
            print(f"  [✗] #{idx:02d} [{item['target_category']}] -> {item['sender_name']} | Error: {e}")
            results.append({"idx": idx, "success": False, "category": item["target_category"], "error": str(e)})

        # Intervalo controlado para permitir procesamiento ordenado
        time.sleep(1.0)

    print("\n" + "-" * 70)
    print(f"  Envío finalizado: {sum(1 for r in results if r['success'])}/{len(results)} correos procesados por n8n.")
    print("-" * 70)

if __name__ == "__main__":
    coders = get_db_coders()
    cases = build_10_cases(coders)
    send_cases(cases)
