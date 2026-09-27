#!/usr/bin/env python3
"""
generate_test_cases.py
Genera un banco de 10 casos de prueba realistas para validar el evaluador HSE de Strata Core:
- Archivos PDF (digitales y escaneados)
- Imágenes PNG/JPG (fotos de celular con ruido)
- Casos de solo texto y casos límite
"""

import os, json, io, time
import pymupdf as fitz
from PIL import Image, ImageDraw, ImageFilter

SAMPLES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_samples")
os.makedirs(SAMPLES_DIR, exist_ok=True)

# 1. Caso 1: Incapacidad EPS Sanitas válida con sello y fecha actual (PDF)
def gen_case_1():
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    text = """CERTIFICADO MEDICO DE INCAPACIDAD
ENTIDAD PROMOTORA DE SALUD: EPS SANITAS
Fecha de Atencion: 25/09/2026
Paciente: Carlos Mario Restrepo - CC: 1.042.890.123
Diagnostico Medico: Gastroenteritis aguda (Codigo CIE-10: A09)
Periodo de Incapacidad: 1 dia (25 de septiembre de 2026)
Tipo de Contingencia: Enfermedad General
Medico Tratante: Dra. Marcela Gomez
Registro Profesional: RM-89412-COL
Firma y Sello Oficial EPS Sanitas: VALIDO Y VERIFICADO"""
    page.insert_text((50, 80), text, fontsize=11)
    path = os.path.join(SAMPLES_DIR, "case_01_sanitas_valida.pdf")
    doc.save(path)
    doc.close()
    return path

# 2. Caso 2: Escaneo de Incapacidad SURA EPS con sello (Imagen PNG)
def gen_case_2():
    img = Image.new("RGB", (800, 1000), color=(248, 248, 245))
    draw = ImageDraw.Draw(img)
    text = """CERTIFICADO DE INCAPACIDAD TEMPORAL
SURA EPS - SEDE PRINCIPAL MEDELLIN
Fecha de Expedicion: 25/09/2026
Paciente: Laura Camila Mejia - CC: 1.033.456.789
Diagnostico: Cefalea tensional severa (CIE-10: G44.2)
Dias Otorgados: 2 dias (Desde 25/09/2026 hasta 26/09/2026)
Medico: Dr. Fernando Ruiz Botero
Registro Medico: RM-45210-ANT
Sello de Autorizacion y Firma: SURA AUTORIZADO"""
    draw.text((40, 60), text, fill=(25, 25, 25))
    path = os.path.join(SAMPLES_DIR, "case_02_sura_escaner.png")
    img.save(path, format="PNG")
    return path

# 3. Caso 3: Incapacidad con fecha vencida de hace 15 días (PDF)
def gen_case_3():
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    text = """CERTIFICADO DE INCAPACIDAD MEDICA
COMPENSAR EPS
Fecha de Atencion: 10/09/2026
Paciente: Andres Felipe Gomez - CC: 1.018.990.231
Diagnostico: Amigdalitis aguda (CIE-10: J03.9)
Dias de Incapacidad: 1 dia (10 de septiembre de 2026)
Medico: Dr. Camilo Pardo - RM-33102
Firma y Sello: COMPENSAR SEDE CALLE 26"""
    page.insert_text((50, 80), text, fontsize=11)
    path = os.path.join(SAMPLES_DIR, "case_03_fecha_vencida.pdf")
    doc.save(path)
    doc.close()
    return path

# 4. Caso 4: Certificado médico informal SIN firma ni sello profesional (PDF)
def gen_case_4():
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    text = """CONSTANCIA DE ASISTENCIA A CONSULTA
CENTRO MEDICO PARTICULAR
Fecha: 25/09/2026
El paciente Mateo Herrera asistio a evaluacion de dolor abdominal.
Se sugiere reposo en casa por el dia de hoy.
(Sin sello profesional ni registro medico visible)"""
    page.insert_text((50, 80), text, fontsize=11)
    path = os.path.join(SAMPLES_DIR, "case_04_sin_firma_ni_sello.pdf")
    doc.save(path)
    doc.close()
    return path

# 5. Caso 5: Calamidad doméstica en texto plano (Sin adjunto)
def gen_case_5():
    # No genera archivo binario, solo metadata para correo
    return None

# 6. Caso 6: Captura de pantalla de falla técnica / reporte de internet (Imagen PNG)
def gen_case_6():
    img = Image.new("RGB", (750, 500), color=(30, 35, 45))
    draw = ImageDraw.Draw(img)
    text = """TIGO - REPORTE DE INCIDENCIA TECNICA
Numero de Ticket: INC-9948210
Estado del Servicio: INTERRUPCION GENERAL EN LA ZONA
Fecha del Reporte: 25/09/2026 08:15 AM
Cliente: Sofia Ramirez Morales
Velocidad de Enlace: 0.0 Mbps (Sin senal de fibra optica)
Tiempo estimado de resolucion: 4 a 6 horas."""
    draw.text((30, 40), text, fill=(230, 235, 240))
    path = os.path.join(SAMPLES_DIR, "case_06_falla_internet.png")
    img.save(path, format="PNG")
    return path

# 7. Caso 7: Fórmula médica de farmacia (NO es incapacidad laboral/académica) (PDF)
def gen_case_7():
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    text = """PRESCRIPCION MEDICA / FORMULA DE MEDICAMENTOS
NUEVA EPS
Fecha: 25/09/2026
Paciente: Esteban Padilla
Medicamentos:
1. Ibuprofeno 400mg - Tomar 1 tableta cada 8 horas por 3 dias.
2. Acetaminofen 500mg - Tomar 1 tableta cada 6 horas si hay fiebre.
NOTA: Esto es una formula para retiro en farmacia, no certifica incapacidad laboral."""
    page.insert_text((50, 80), text, fontsize=11)
    path = os.path.join(SAMPLES_DIR, "case_07_formula_no_incapacidad.pdf")
    doc.save(path)
    doc.close()
    return path

# 8. Caso 8: Salida temprana justificada con cita odontológica programada (PDF)
def gen_case_8():
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    text = """RECORDATORIO Y CONSTANCIA DE CITA ODONTOLOGICA
CLINICA ODONTOLOGICA DENTAL SALUD
Fecha: 25/09/2026
Hora de Cita: 11:30 AM
Paciente: Valentina Rios - CC: 1.020.345.890
Procedimiento: Cirugia de cordales inferior izquierda.
Odontologo: Dr. Julian Martinez - Odontologia Especializada
Sello y Firma: CLINICA DENTAL SALUD VERIFICADO"""
    page.insert_text((50, 80), text, fontsize=11)
    path = os.path.join(SAMPLES_DIR, "case_08_salida_temprana_cita.pdf")
    doc.save(path)
    doc.close()
    return path

# 9. Caso 9: Fotografía muy borrosa / con ruido extremo (Imagen PNG con blur)
def gen_case_9():
    img = Image.new("RGB", (600, 700), color=(180, 175, 165))
    draw = ImageDraw.Draw(img)
    draw.text((30, 40), "Certif... med... Dr... Reposo...", fill=(100, 95, 85))
    # Aplicar desenfoque severo para simular foto de celular movida e ilegible
    img = img.filter(ImageFilter.GaussianBlur(radius=6.0))
    path = os.path.join(SAMPLES_DIR, "case_09_foto_borrosa_ilegible.png")
    img.save(path, format="PNG")
    return path

# 10. Caso 10: Correo Spam / Publicidad irrelevante
def gen_case_10():
    return None

def main():
    print("[*] Generando archivos para los 10 casos de prueba...")
    gen_case_1()
    gen_case_2()
    gen_case_3()
    gen_case_4()
    gen_case_5()
    gen_case_6()
    gen_case_7()
    gen_case_8()
    gen_case_9()
    gen_case_10()

    manifest = [
        {
            "case_id": 1,
            "title": "Incapacidad médica EPS Sanitas válida con sello y fecha actual",
            "file": "case_01_sanitas_valida.pdf",
            "email_subject": "Justificante inasistencia médica - Carlos Restrepo",
            "email_body": "Adjunto incapacidad médica de EPS Sanitas por el día de hoy por cuadro gastrointestinal.",
            "expected_valido": True,
            "expected_tipo": "inasistencia_medica",
            "expected_manual_review": False
        },
        {
            "case_id": 2,
            "title": "Escaneo de Incapacidad SURA EPS con sello profesional",
            "file": "case_02_sura_escaner.png",
            "email_subject": "Incapacidad médica por 2 días - Laura Mejía",
            "email_body": "Buenos días, adjunto la foto del certificado médico de SURA por cefalea severa.",
            "expected_valido": True,
            "expected_tipo": "inasistencia_medica",
            "expected_manual_review": False
        },
        {
            "case_id": 3,
            "title": "Incapacidad médica extemporánea (fecha vencida hace 15 días)",
            "file": "case_03_fecha_vencida.pdf",
            "email_subject": "Excusa de falta atrasada - Andrés Gómez",
            "email_body": "Profe adjunto la incapacidad médica de hace dos semanas que no alcancé a enviar antes.",
            "expected_valido": False,
            "expected_tipo": "inasistencia_medica",
            "expected_manual_review": True
        },
        {
            "case_id": 4,
            "title": "Constancia médica informal sin firma ni sello profesional",
            "file": "case_04_sin_firma_ni_sello.pdf",
            "email_subject": "Justificación médica - Mateo Herrera",
            "email_body": "Fui al médico particular y me dieron esta constancia de reposo.",
            "expected_valido": False,
            "expected_tipo": "inasistencia_medica",
            "expected_manual_review": True
        },
        {
            "case_id": 5,
            "title": "Calamidad doméstica en texto plano (sin adjunto)",
            "file": None,
            "email_subject": "Inasistencia por calamidad doméstica grave - Isabella Mendoza",
            "email_body": "Equipo HSE, lamentablemente en la madrugada falleció mi abuela y me encuentro realizando los trámites funerarios. No podré conectarme hoy.",
            "expected_valido": False,
            "expected_tipo": "calamidad",
            "expected_manual_review": True
        },
        {
            "case_id": 6,
            "title": "Reporte de falla técnica de proveedor de internet",
            "file": "case_06_falla_internet.png",
            "email_subject": "Sin internet en el sector - Sofía Ramírez",
            "email_body": "Se cayó la fibra óptica de Tigo en mi barrio. Adjunto captura del ticket oficial de falla.",
            "expected_valido": True,
            "expected_tipo": "falla_tecnica",
            "expected_manual_review": False
        },
        {
            "case_id": 7,
            "title": "Fórmula médica de farmacia (no es incapacidad)",
            "file": "case_07_formula_no_incapacidad.pdf",
            "email_subject": "Soporte de medicamentos - Esteban Padilla",
            "email_body": "Adjunto el papel que me dio el médico en urgencias con los medicamentos.",
            "expected_valido": False,
            "expected_tipo": "inasistencia_medica",
            "expected_manual_review": True
        },
        {
            "case_id": 8,
            "title": "Salida temprana con cita odontológica programada",
            "file": "case_08_salida_temprana_cita.pdf",
            "email_subject": "Permiso para retirarme 1 hora antes - Valentina Ríos",
            "email_body": "Tengo procedimiento quirúrgico dental a las 11:30 AM. Adjunto la constancia de la clínica.",
            "expected_valido": True,
            "expected_tipo": "salida_temprana",
            "expected_manual_review": False
        },
        {
            "case_id": 9,
            "title": "Fotografía totalmente borrosa e ilegible",
            "file": "case_09_foto_borrosa_ilegible.png",
            "email_subject": "Justificante médico - Daniel Vargas",
            "email_body": "Adjunto foto de la excusa que me dieron en el puesto de salud.",
            "expected_valido": False,
            "expected_tipo": "no_identificado",
            "expected_manual_review": True
        },
        {
            "case_id": 10,
            "title": "Correo de Spam / Asunto no relacionado con asistencia",
            "file": None,
            "email_subject": "Descuentos en cursos de React y certificación cloud",
            "email_body": "Aprovecha el 50% de descuento en suscripciones anuales ingresando a nuestra plataforma web.",
            "expected_valido": False,
            "expected_tipo": "no_identificado",
            "expected_manual_review": True
        }
    ]

    manifest_path = os.path.join(SAMPLES_DIR, "cases_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"[OK] Manifiesto guardado con los 10 casos en:\n    {manifest_path}")

if __name__ == "__main__":
    main()
