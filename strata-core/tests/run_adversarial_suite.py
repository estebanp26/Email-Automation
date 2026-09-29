#!/usr/bin/env python3
"""
run_adversarial_suite.py
Suite de pruebas no triviales y casos frontera para evaluar la robustez
del clasificador Strata Core AI con Ollama activo (qwen2.5:1.5b).
Evalúa casos ambiguos de:
- Calamidad coloquial vs Síntomas de enfermedad sin soporte EPS
- Fórmula de farmacia EPS vs Incapacidad formal con reposo
- Cita médica programada con preaviso vs radicada post-facto
- Salida temprana vs inasistencia
- Calamidad por fuerza mayor en texto plano (plazo 72h)
- Salud mental / alta sensibilidad
- Incapacidad EPS formal válida
- Falla técnica sin ticket de soporte
"""

import os
import sys
import json
import asyncio
import tempfile
import jsonschema
import pymupdf as fitz
from pathlib import Path

# Setup paths
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import server

SCHEMA_PATH = BASE_DIR / "schemas" / "evaluation_schema.json"

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

def create_pdf(text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes

CASES = [
    {
        "id": 1,
        "name": "Calamidad coloquial con fiebre/vómito (sin soporte EPS)",
        "subject": "Calamidad doméstica hoy",
        "body": "Equipo, tuve una calamidad tremenda en la noche me dio una fiebre de 39 y vómito incontrolable, sigo en cama sin poder levantarme.",
        "pdf_text": None,
        "expected_tipo": "enfermedad_sin_soporte",
        "expected_cat": "REVISION_MANUAL",
        "expected_valido": False,
        "expected_manual": True
    },
    {
        "id": 2,
        "name": "Fórmula médica de farmacia con membrete EPS SURA (sin reposo)",
        "subject": "Soporte de medicamentos SURA",
        "body": "Adjunto el papel que me entregaron en la consulta de SURA para justificar mi falta.",
        "pdf_text": "EPS SURA Formulario de Medicamentos: Acetaminofén 500mg, Amoxicilina 500mg. Tomar cada 8 horas.",
        "expected_tipo": "enfermedad_sin_soporte",
        "expected_cat": "REVISION_MANUAL",
        "expected_valido": False,
        "expected_manual": True
    },
    {
        "id": 3,
        "name": "Cita médica programada radicada a destiempo (post-facto)",
        "subject": "Excusa médica por cita de control",
        "body": "Profe, ayer en la tarde asistí a mi cita con el especialista que tenía agendada desde el mes pasado, se me olvidó avisarles antes pero aquí estuve en la consulta.",
        "pdf_text": "Constancia de Asistencia a Cita Médica con Especialista. Fecha de atención: ayer.",
        "expected_tipo": "inasistencia_medica",
        "expected_cat": "POSIBLEMENTE_INVALIDO",
        "expected_valido": False,
        "expected_manual": False
    },
    {
        "id": 4,
        "name": "Salida temprana con cita odontológica previa",
        "subject": "Permiso de jornada",
        "body": "Buenas tardes, llegué a las 8am normalmente pero me toca salir antes hoy a las 3pm por cita odontológica.",
        "pdf_text": "Constancia clínica cita control dental odontológico.",
        "expected_tipo": "salida_temprana",
        "expected_cat": "POSIBLEMENTE_VALIDO",
        "expected_valido": True,
        "expected_manual": False
    },
    {
        "id": 5,
        "name": "Calamidad doméstica de fuerza mayor en texto plano (inundación)",
        "subject": "Emergencia grave en vivienda",
        "body": "Equipo HSE, lamentablemente hubo una inundación grave en mi casa por la lluvia torrencial y se dañaron los enseres, estoy con bomberos sacando el agua.",
        "pdf_text": None,
        "expected_tipo": "calamidad",
        "expected_cat": "REVISION_MANUAL",
        "expected_valido": False,
        "expected_manual": True
    },
    {
        "id": 6,
        "name": "Salud mental / crisis de ansiedad (Protocolo alta sensibilidad)",
        "subject": "No puedo asistir hoy",
        "body": "Hola Paola, estoy pasando por un cuadro de depresión y crisis de ansiedad muy fuerte desde anoche, no me siento en condiciones de prender la cámara ni concentrarme.",
        "pdf_text": None,
        "expected_tipo": "calamidad",
        "expected_cat": "REVISION_MANUAL",
        "expected_valido": False,
        "expected_manual": True
    },
    {
        "id": 7,
        "name": "Incapacidad formal EPS Sanitas con días de reposo legítima",
        "subject": "Incapacidad médica EPS Sanitas",
        "body": "Buenos días, adjunto certificado de incapacidad médica de EPS Sanitas por 2 días de reposo debido a gastroenteritis aguda.",
        "pdf_text": "EPS SANITAS Certificado de incapacidad médica reposo 2 dias diagnostico CIE-10 A09 gastroenteritis firma y sello medico",
        "expected_tipo": "inasistencia_medica",
        "expected_cat": "POSIBLEMENTE_VALIDO",
        "expected_valido": True,
        "expected_manual": False
    },
    {
        "id": 8,
        "name": "Falla técnica sin ticket de soporte adjunto",
        "subject": "Problemas con el internet",
        "body": "No tengo internet desde esta mañana porque se cayó la red en mi barrio.",
        "pdf_text": None,
        "expected_tipo": "falla_tecnica",
        "expected_cat": "REVISION_MANUAL",
        "expected_valido": False,
        "expected_manual": True
    }
]

async def run_suite():
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = json.load(f)

    print("================================================================================")
    print("  STRATA CORE AI - SUITE DE PRUEBAS ADVERSARIALES Y FRONTERA (OLLAMA ENGINE)")
    print("================================================================================\n")

    passed_count = 0
    total_count = len(CASES)
    results_table = []

    for c in CASES:
        mock_file = None
        if c["pdf_text"]:
            pdf_bytes = create_pdf(c["pdf_text"])
            mock_file = MockUploadFile(f"soporte_caso_{c['id']}.pdf", pdf_bytes)

        try:
            res = await server.evaluate_excuse(
                request=None,
                file=mock_file,
                email_subject=c["subject"],
                email_body=c["body"]
            )
            
            # 1. Validar esquema JSON estricto
            jsonschema.validate(instance=res, schema=schema)

            # 2. Validar reglas de clasificación
            actual_tipo = res.get("tipo_novedad")
            actual_cat = res.get("categoria_sugerida")
            actual_valido = res.get("valido")
            actual_manual = res.get("requiere_revision_manual")
            elapsed = res.get("tiempo_procesamiento_segundos", 0.0)

            tipo_ok = (actual_tipo == c["expected_tipo"])
            cat_ok = (actual_cat == c["expected_cat"])
            val_ok = (actual_valido == c["expected_valido"])
            man_ok = (actual_manual == c["expected_manual"])

            all_ok = tipo_ok and cat_ok and val_ok and man_ok
            if all_ok:
                passed_count += 1
                status_str = "PASS"
            else:
                status_str = "FAIL"

            results_table.append({
                "id": c["id"],
                "name": c["name"],
                "expected_tipo": c["expected_tipo"],
                "actual_tipo": actual_tipo,
                "expected_cat": c["expected_cat"],
                "actual_cat": actual_cat,
                "latency": elapsed,
                "status": status_str,
                "motivo": res.get("motivo_decision")
            })

            print(f"[{status_str}] Caso {c['id']}: {c['name']}")
            print(f"      Tipo novedad:        {actual_tipo} (esperado: {c['expected_tipo']})")
            print(f"      Categoría sugerida:  {actual_cat} (esperado: {c['expected_cat']})")
            print(f"      Válido:              {actual_valido} | Revisión manual: {actual_manual}")
            print(f"      Latencia:            {elapsed}s")
            print(f"      Motivo decisión:     {res.get('motivo_decision')[:90]}...")
            print("-" * 80)

        finally:
            if mock_file:
                mock_file.cleanup()

    print("\n================================================================================")
    print(f"  RESUMEN DE RESULTADOS: {passed_count}/{total_count} PASARON ({(passed_count/total_count)*100:.1f}%)")
    print("================================================================================")

    if passed_count < total_count:
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(run_suite())
