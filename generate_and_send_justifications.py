#!/usr/bin/env python3
"""
generate_and_send_justifications.py
=============================================================================
GENERADOR Y DESPACHADOR DE 200 CORREOS DE JUSTIFICACIÓN DE INASISTENCIA HSE
=============================================================================
Genera 200 correos electrónicos hiperrealistas de justificación de faltas y
contingencias formativas de Coders de RIWI.

Estrategia de Envío:
- Fase 1: Ráfaga de Concurrencia (Burst) -> 50 correos enviados simultáneamente
          para probar saturación, seguridad, concurrencia y resiliencia.
- Fase 2: Envío Escalonado (Intervals) -> 150 correos enviados con intervalos
          y pausas programadas simulando tráfico realista continuo.
=============================================================================
"""

import os
import sys
import time
import json
import base64
import random
import hashlib
import argparse
from datetime import datetime, date, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Tuple
import urllib.request
import urllib.error

# Soporte UTF-8 para consolas
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent

def load_env_file():
    env_path = BASE_DIR / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ[k.strip()] = v.strip().strip('"').strip("'")

load_env_file()

# =============================================================================
# CATÁLOGO DE EPS, DIAGNÓSTICOS CIE-10 Y TIPOS DE NOVEDAD
# =============================================================================

EPS_LIST = [
    "SURA EPS", "EPS Sanitas", "Nueva EPS", "Salud Total EPS",
    "Compensar EPS", "Famisanar", "Coosalud EPS", "Mutual Ser"
]

CIE10_DIAGNOSES = [
    ("J00", "Rinofaringitis aguda (resfriado común)", "Reposo e hidratación por cuadro viral agudo."),
    ("J06.9", "Infección aguda de las vías respiratorias superiores", "Reposo en casa y aislamiento por sintomatología respiratoria."),
    ("K29.7", "Gastritis no especificada / Gastroenteritis aguda", "Reposo digestivo, hidratación oral y analgesia."),
    ("M54.5", "Lumbago no especificado / Contractura muscular", "Reposo físico, analgesia y terapia postural."),
    ("B34.9", "Infección viral no especificada / Cuadro febril", "Reposo en casa por 48 horas bajo vigilancia clínica."),
    ("H10.9", "Conjuntivitis no especificada", "Aislamiento relativo y reposo visual, evitar pantallas."),
    ("K52.9", "Gastroenteritis y colitis tóxica no infecciosa", "Incapacidad médica por deshidratación y reposo oral."),
    ("N39.0", "Infección de vías urinarias no especificada", "Tratamiento antibiótico ambulatorio y reposo.")
]

DOCTORS = [
    ("Dra. Camila Restrepo", "RM 45892-Medellín"),
    ("Dr. Carlos Mario Valencia", "RM 67120-Barranquilla"),
    ("Dra. Diana Patricia Osorio", "RM 31405-Bogotá"),
    ("Dr. Andrés Felipe Londoño", "RM 52391-Bucaramanga"),
    ("Dra. Laura Vanessa Gutiérrez", "RM 78451-Cali")
]

DOMESTIC_CALAMITIES = [
    ("Calamidad doméstica por inundación en vivienda", "Buenos días equipo HSE, presento falla por inundación en mi domicilio debido a las fuertes lluvias de anoche. Tuve afectación de enseres y fluido eléctrico."),
    ("Acompañamiento a familiar en urgencias hospitalarias", "Buenas tardes, me dirijo a ustedes para justificar mi inasistencia debido al ingreso por urgencias de mi madre a la clínica general."),
    ("Fallecimiento de abuelo materno y diligencias fúnebres", "Cordial saludo equipo de Bienestar, me encuentro en la ciudad de origen por el sensible fallecimiento de mi abuelo."),
    ("Accidente doméstico y atención de primera necesidad", "Buenos días, tuve un incidente doméstico menor con una quemadura en mano derecha que requirió curación en centro de salud.")
]

TECHNICAL_FAILURES = [
    ("Falla masiva de energía en el sector residencial", "Hola equipo, presento reporte por corte del servicio eléctrico en mi barrio por mantenimiento no programado de Air-e / Afinia."),
    ("Corte de fibra óptica / Conectividad a internet", "Estimados, informo que el proveedor Claro reporta daño en la fibra óptica principal del sector. Radicado de falla: #TK-89472."),
    ("Daño en adaptador de corriente del equipo de cómputo", "Buenas tardes, presento daño súbito en el cargador de mi laptop durante la mañana, ya gestioné el reemplazo para reincorporarme mañana.")
]

SPECIAL_CASES_REVISION = [
    ("Formula médica sin formato de incapacidad", "Adjunto la orden médica que me entregaron en la farmacia para justificar que fui al médico.", "FORMULA"),
    ("Solicitud de permiso por trámite de cédula / pasaporte", "Tengo cita en la Registraduría Nacional en horas de la mañana para renovar mi documento.", "LEGAL"),
    ("Certificado con fecha de la semana pasada", "Buenos días, adjunto la incapacidad que tuve el martes pasado que no alcancé a enviar a tiempo.", "VENCIDA")
]


# =============================================================================
# GENERADOR DETERMINISTA DE ARCHIVOS PDF MOCK EN BASE64
# =============================================================================

def create_mock_pdf_base64(title: str, coder_name: str, doc_id: str, dates_text: str) -> str:
    """Genera una estructura de bytes PDF válida (%PDF-1.4) con metadatos reales."""
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
    raw_bytes = pdf_content.encode("latin-1")
    return base64.b64encode(raw_bytes).decode("ascii")


# =============================================================================
# CARGA DE CODERS (POSTGRESQL O CATÁLOGO LOCAL)
# =============================================================================

def load_coders_from_db_or_fallback(limit: int = 200) -> List[Dict[str, str]]:
    """Intenta cargar coders de la base de datos PostgreSQL; si falla, usa catálogo sintético."""
    coders = []
    try:
        import psycopg2
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", 5432)),
            dbname=os.getenv("POSTGRES_DB", "hse_email_automation"),
            user=os.getenv("POSTGRES_USER", "hse_admin"),
            password=os.getenv("POSTGRES_PASSWORD", "cambia_esta_contrasena_en_produccion"),
            connect_timeout=3
        )
        cur = conn.cursor()
        cur.execute("SELECT full_name, email, cedula, route FROM coders WHERE is_active = true ORDER BY id LIMIT %s;", (limit,))
        rows = cur.fetchall()
        for r in rows:
            coders.append({
                "name": r[0],
                "email": r[1],
                "cedula": r[2],
                "route": r[3]
            })
        cur.close()
        conn.close()
        if len(coders) >= 20:
            print(f"  [✓] Se cargaron {len(coders)} Coders reales directamente desde PostgreSQL.")
            return coders
    except Exception as e:
        print(f"  [i] Aviso conexión DB ({e}); usando catálogo de coders integrado.")

    # Generador de respaldo de 200 coders
    first_names = ["Santiago", "Mariana", "Andres", "Laura", "Carlos", "Valentina", "David", "Sofia", "Mateo", "Camila", "Daniel", "Natalia", "Felipe", "Isabella", "Alejandro", "Paula", "Sebastian", "Gabriela", "Julian", "Daniela"]
    last_names = ["Morales", "Gomez", "Rios", "Torres", "Valencia", "Ospina", "Rodriguez", "Castro", "Martinez", "Perez", "Vargas", "Suarez", "Ortiz", "Navarro", "Arrieta", "Mendoza", "Restrepo", "Londoño", "Gutierrez", "Silva"]
    routes = ["Node.js Backend", "Java Spring Boot", "TypeScript Fullstack", ".NET / C# Backend", "Analítica de Datos & BI"]

    count = 0
    for fn in first_names:
        for ln in last_names:
            count += 1
            name = f"{fn} {ln}"
            email_addr = f"{fn.lower()}.{ln.lower()}{count}@riwi.io"
            ced = f"100{count:06d}"
            coders.append({"name": name, "email": email_addr, "cedula": ced, "route": random.choice(routes)})
            if len(coders) >= limit:
                break
        if len(coders) >= limit:
            break
    return coders


# =============================================================================
# FABRICADOR DE LOS 200 CORREOS DE JUSTIFICACIÓN
# =============================================================================

def build_200_justification_emails(target_count: int = 200) -> List[Dict[str, Any]]:
    """Construye 200 casos detallados de correos estructurados."""
    coders = load_coders_from_db_or_fallback(target_count)
    emails = []

    today = date.today()

    for i in range(target_count):
        coder = coders[i % len(coders)]
        coder_name = coder["name"]
        coder_email = coder["email"]
        coder_cedula = coder["cedula"]
        coder_route = coder.get("route", "Desarrollo de Software")

        case_type_roll = random.random()
        provider = "OUTLOOK" if i % 2 == 0 else "GMAIL"
        message_id = f"<justif_{provider.lower()}_{i+1}_{int(time.time())}_{coder_cedula}@riwi.io>"
        offset_days = random.randint(0, 3)
        incident_date = today - timedelta(days=offset_days)
        incident_date_str = incident_date.strftime("%d/%m/%Y")

        attachments = []

        # Caso 1: Incapacidad Médica Válida (60% de los casos)
        if case_type_roll < 0.60:
            eps = random.choice(EPS_LIST)
            cie, diag_name, rec = random.choice(CIE10_DIAGNOSES)
            doctor, reg = random.choice(DOCTORS)
            days = random.choice([1, 2, 3, 4, 5])
            end_date = incident_date + timedelta(days=days - 1)

            subject = f"Justificación médica - {days} día(s) de incapacidad - {coder_name}"
            body = f"""Cordial saludo Equipo de Bienestar HSE RIWI,

Me dirijo a ustedes para justificar mi inasistencia a la jornada formativa de la ruta {coder_route}.
Presenté complicaciones de salud diagnosticadas por {eps} ({diag_name}, CIE-10: {cie}).

Detalles de la atención:
- Coder: {coder_name}
- Documento: {coder_cedula}
- Días de incapacidad: {days} día(s) (desde {incident_date_str} hasta {end_date.strftime('%d/%m/%Y')})
- Médico tratante: {doctor} ({reg})
- Recomendación: {rec}

Adjunto constancia médica oficial en formato PDF para su validación en el sistema.

Quedo atento a su confirmación.
Atentamente,
{coder_name}
Coder RIWI - {coder_route}"""

            pdf_b64 = create_mock_pdf_base64(
                title=f"CERTIFICADO DE INCAPACIDAD - {eps}",
                coder_name=coder_name,
                doc_id=coder_cedula,
                dates_text=f"{incident_date_str} a {end_date.strftime('%d/%m/%Y')} ({days} dias)"
            )
            attachments.append({
                "filename": f"incapacidad_{coder_cedula}_{eps.replace(' ', '_').lower()}.pdf",
                "mime_type": "application/pdf",
                "size_bytes": 1450,
                "data_base64": pdf_b64
            })
            category_tag = "MEDICA_VALIDA"

        # Caso 2: Calamidad Doméstica (18% de los casos)
        elif case_type_roll < 0.78:
            calamity_title, calamity_desc = random.choice(DOMESTIC_CALAMITIES)
            subject = f"Novedad por Calamidad Doméstica - {coder_name}"
            body = f"""Buenas tardes Equipo HSE,

{calamity_desc}

Por esta razón no me fue posible conectarme a la sesión del día {incident_date_str}.
Mi cédula es {coder_cedula}, pertenezco a la ruta {coder_route}.

Agradezco su comprensión y apoyo ante esta contingencia.

Atentamente,
{coder_name}"""

            if random.random() < 0.5:
                # Adjunta comprobante
                pdf_b64 = create_mock_pdf_base64(
                    title="CONSTANCIA DE INCIDENTE / SOPORTE",
                    coder_name=coder_name,
                    doc_id=coder_cedula,
                    dates_text=incident_date_str
                )
                attachments.append({
                    "filename": f"soporte_calamidad_{coder_cedula}.pdf",
                    "mime_type": "application/pdf",
                    "size_bytes": 1320,
                    "data_base64": pdf_b64
                })
            category_tag = "CALAMIDAD_DOMESTICA"

        # Caso 3: Cita Médica / Examen Clínico (10% de los casos)
        elif case_type_roll < 0.88:
            doctor, reg = random.choice(DOCTORS)
            eps = random.choice(EPS_LIST)
            subject = f"Constancia de Asistencia a Cita Médica - {coder_name}"
            body = f"""Buenos días Paola y equipo HSE,

El día {incident_date_str} asistí a una cita médica prioritaria y toma de exámenes de laboratorio en {eps} en horario de la mañana.
Atendido por: {doctor}.
Coder: {coder_name} (CC {coder_cedula}).

Adjunto el comprobante de asistencia emitido por la entidad. Ya me encuentro al día con las grabaciones de la sesión.

Muchas gracias,
{coder_name}"""
            pdf_b64 = create_mock_pdf_base64(
                title=f"COMPROBANTE DE ATENCION MEDICA - {eps}",
                coder_name=coder_name,
                doc_id=coder_cedula,
                dates_text=incident_date_str
            )
            attachments.append({
                "filename": f"comprobante_cita_{coder_cedula}.pdf",
                "mime_type": "application/pdf",
                "size_bytes": 1280,
                "data_base64": pdf_b64
            })
            category_tag = "CITA_MEDICA"

        # Caso 4: Falla Técnica / Eléctrica (7% de los casos)
        elif case_type_roll < 0.95:
            fault_title, fault_desc = random.choice(TECHNICAL_FAILURES)
            subject = f"Reporte de Novedad Técnica - {coder_name}"
            body = f"""Hola equipo de HSE y Formación,

{fault_desc}
Fecha del evento: {incident_date_str}.
Nombre: {coder_name} | Documento: {coder_cedula}.

Me pongo al día de inmediato con los entregables del módulo.

Saludos,
{coder_name}"""
            category_tag = "FALLA_TECNICA"

        # Caso 5: Casos con soporte incompleto o extemporáneo (5% de los casos)
        else:
            spec_subj, spec_body, spec_type = random.choice(SPECIAL_CASES_REVISION)
            subject = f"{spec_subj} - {coder_name}"
            body = f"""Equipo HSE,
{spec_body}
Fecha: {incident_date_str}
Coder: {coder_name} (CC {coder_cedula})."""
            category_tag = f"REVISION_{spec_type}"

        # Ensamblar payload conforme al contrato universal de n8n / Strata Core
        payload = {
            "source_provider": provider,
            "message_id": message_id,
            "sender_email": coder_email,
            "sender_name": coder_name,
            "email_subject": subject,
            "email_body": body,
            "received_at": datetime.now(timezone.utc).isoformat(),
            "attachments": attachments,
            "has_attachments": len(attachments) > 0,
            "_meta_category": category_tag,
            "_meta_index": i + 1
        }
        emails.append(payload)

    return emails


# =============================================================================
# DESPACHADOR HTTP RESILIENTE
# =============================================================================

def send_single_email(
    item: Dict[str, Any],
    target_url: str,
    timeout: int = 15
) -> Dict[str, Any]:
    """Envía un correo mediante petición HTTP POST al endpoint indicado."""
    idx = item.get("_meta_index", 0)
    tag = item.get("_meta_category", "GENERAL")
    coder = item.get("sender_name", "Coder")

    # Limpiar campos internos antes de enviar
    payload_to_send = {k: v for k, v in item.items() if not k.startswith("_meta_")}
    req_bytes = json.dumps(payload_to_send).encode("utf-8")

    req = urllib.request.Request(
        target_url,
        data=req_bytes,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    start_t = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            elapsed = time.time() - start_t
            return {
                "index": idx,
                "coder": coder,
                "category": tag,
                "status_code": resp.status,
                "success": True,
                "elapsed": elapsed,
                "error": None
            }
    except urllib.error.HTTPError as e:
        elapsed = time.time() - start_t
        return {
            "index": idx,
            "coder": coder,
            "category": tag,
            "status_code": e.code,
            "success": False,
            "elapsed": elapsed,
            "error": f"HTTP {e.code}: {e.reason}"
        }
    except Exception as e:
        elapsed = time.time() - start_t
        return {
            "index": idx,
            "coder": coder,
            "category": tag,
            "status_code": None,
            "success": False,
            "elapsed": elapsed,
            "error": str(e)
        }


# =============================================================================
# ORQUESTADOR PRINCIPAL: RÁFAGA (50) + ESCALONADO (150)
# =============================================================================

def execute_stress_and_staggered_injection(
    total: int = 200,
    burst_count: int = 50,
    interval_base: float = 0.5,
    jitter: float = 0.3,
    target_url: str = "http://localhost:5678/webhook/riwi-email-incoming",
    dry_run: bool = False
):
    print("=" * 75)
    print("  RIWI HSE — DESPACHADOR DE INYECCIÓN DE CORREOS DE JUSTIFICACIÓN   ")
    print("=" * 75)
    print(f" • Total de correos a generar:    {total}")
    print(f" • Fase 1 (Ráfaga Simultánea):    {burst_count} correos en paralelo")
    print(f" • Fase 2 (Envío con Intervalos): {total - burst_count} correos escalonados")
    print(f" • Intervalo base entre envíos:   {interval_base}s (± {jitter}s jitter)")
    print(f" • Endpoint destino:              {target_url}")
    print(f" • Modo simulación (Dry-Run):     {'ACTIVO' if dry_run else 'DESACTIVADO (Envío Real)'}")
    print("-" * 75)

    print("\n[Paso 1/3] Generando 200 justificaciones con datos reales...")
    all_emails = build_200_justification_emails(total)
    burst_batch = all_emails[:burst_count]
    staggered_batch = all_emails[burst_count:]
    print(f"  [✓] {len(all_emails)} justificaciones preparadas.")

    if dry_run:
        print("\n[Dry-Run] Verificando estructura de los primeros 5 correos:")
        for sample in all_emails[:5]:
            print(f"  • #{sample['_meta_index']:03d} [{sample['_meta_category']}] De: {sample['sender_name']} <{sample['sender_email']}> | Asunto: {sample['email_subject'][:45]}... | Adjuntos: {len(sample['attachments'])}")
        print("\n[✓] Generación completada con éxito en modo Dry-Run. Fin de prueba.")
        return

    # =========================================================================
    # FASE 1: RÁFAGA DE 50 CORREOS SIMULTÁNEOS
    # =========================================================================
    print(f"\n[Paso 2/3] FASE 1: ENVIANDO RÁFAGA DE {burst_count} CORREOS SIMULTÁNEOS...")
    print(f"  ⚡ Disparando 50 hilos paralelos para probar saturación y resiliencia...")

    burst_results = []
    t_start_burst = time.time()

    with ThreadPoolExecutor(max_workers=burst_count) as executor:
        futures = {executor.submit(send_single_email, mail, target_url): mail for mail in burst_batch}
        for future in as_completed(futures):
            res = future.result()
            burst_results.append(res)
            status_icon = "✓" if res["success"] else "✗"
            print(f"    [{status_icon}] Ráfaga #{res['index']:02d} | {res['coder'][:22]:<22} | {res['elapsed']:.2f}s | HTTP {res['status_code']}")

    t_burst_total = time.time() - t_start_burst
    burst_success = sum(1 for r in burst_results if r["success"])
    print(f"\n  [✓] Fin de Fase 1 (Ráfaga):")
    print(f"      • Exitosos: {burst_success}/{burst_count} ({(burst_success/burst_count)*100:.1f}%)")
    print(f"      • Tiempo total ráfaga: {t_burst_total:.2f}s | Throughput: {burst_count/t_burst_total:.1f} req/s")

    # =========================================================================
    # FASE 2: ENVÍO ESCALONADO DE LOS 150 CORREOS RESTANTES CON INTERVALOS
    # =========================================================================
    staggered_count = len(staggered_batch)
    print(f"\n[Paso 3/3] FASE 2: ENVIANDO {staggered_count} CORREOS CON INTERVALOS PROGRAMADOS...")
    staggered_results = []
    t_start_staggered = time.time()

    for idx, mail in enumerate(staggered_batch, 1):
        global_index = burst_count + idx
        res = send_single_email(mail, target_url)
        staggered_results.append(res)

        status_icon = "✓" if res["success"] else "✗"
        print(f"  [{status_icon}] [{global_index:03d}/{total:03d}] {mail['sender_name'][:24]:<24} | {mail['_meta_category']:<18} | {res['elapsed']:.2f}s | HTTP {res['status_code']}")

        # Aplicar intervalo con variación jitter (salvo en el último correo)
        if idx < staggered_count:
            sleep_time = max(0.1, interval_base + random.uniform(-jitter, jitter))
            time.sleep(sleep_time)

    t_staggered_total = time.time() - t_start_staggered
    staggered_success = sum(1 for r in staggered_results if r["success"])

    # =========================================================================
    # RESUMEN EJECUTIVO Y ESTADÍSTICAS
    # =========================================================================
    total_success = burst_success + staggered_success
    total_time = t_burst_total + t_staggered_total

    print("\n" + "=" * 75)
    print("                    REPORTE FINAL DE LA PRUEBA                      ")
    print("=" * 75)
    print(f" • Total Correos Despachados:     {total}")
    print(f" • Éxito Global:                  {total_success}/{total} ({(total_success/total)*100:.1f}%)")
    print(f" • Tiempo Total de Ejecución:     {total_time:.2f}s")
    print("-" * 75)
    print(f" • Fase 1 (Ráfaga de 50):         {burst_success}/50 exitosos en {t_burst_total:.2f}s ({burst_count/t_burst_total:.1f} req/s)")
    print(f" • Fase 2 (150 con intervalos):   {staggered_success}/150 exitosos en {t_staggered_total:.2f}s")
    print("=" * 75)


def main():
    parser = argparse.ArgumentParser(
        description="Generador y despachador de 200 justificaciones para el Sistema HSE RIWI"
    )
    parser.add_argument("--total", type=int, default=200, help="Total de correos a generar (default: 200)")
    parser.add_argument("--burst", type=int, default=50, help="Cantidad enviada en ráfaga simultánea inicial (default: 50)")
    parser.add_argument("--interval", type=float, default=0.4, help="Intervalo base en segundos para fase 2 (default: 0.4s)")
    parser.add_argument("--jitter", type=float, default=0.2, help="Variación aleatoria del intervalo (default: 0.2s)")
    parser.add_argument("--url", default="http://localhost:5678/webhook/riwi-email-incoming", help="URL del webhook destino")
    parser.add_argument("--dry-run", action="store_true", help="Genera los correos y muestra muestra estadística sin enviarlos")

    args = parser.parse_args()
    execute_stress_and_staggered_injection(
        total=args.total,
        burst_count=args.burst,
        interval_base=args.interval,
        jitter=args.jitter,
        target_url=args.url,
        dry_run=args.dry_run
    )


if __name__ == "__main__":
    main()
