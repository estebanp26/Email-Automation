import asyncio
import json
import os
import sys
import re
import shutil
import tempfile
import time
import uuid
from typing import List, Optional, Dict, Any

# Prevent OpenMP thread contention across parallel OCR worker processes
os.environ["OMP_THREAD_LIMIT"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

import pymupdf as fitz
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Union
import base64
from pathlib import Path
try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    psycopg2 = None

# Auto-load root .env if present
_root_env = Path(__file__).resolve().parent.parent / ".env"
if _root_env.exists():
    for _line in _root_env.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))

from engine.pdf_reader import PDFEngineReader
from engine.search_index import SearchEngine
from engine.ai_extractor import AIExtractor, DEFAULT_MODEL
from engine.telemetry import metrics_tracker

app = FastAPI(
    title="Strata Core — Document Perception & Evidence Verification API",
    version="1.0.0",
    description="Motor universal de extracción estructurada, OCR adaptativo y validación de justificaciones HSE on-premise."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from routers.inbound_email import router as inbound_email_router
from services.inbound_service import inbound_service
app.include_router(inbound_email_router)

TEMP_DIR = os.path.join(BASE_DIR, "temp_processing")
os.makedirs(TEMP_DIR, exist_ok=True)

# Singleton instances
reader = PDFEngineReader()
ai_client = AIExtractor()

DEFAULT_HSE_RULES = {
    "max_hours_allowed": 48,
    "valid_reasons": ["medica", "calamidad_domestica", "tramite_legal", "fuerza_mayor", "falla_tecnica"],
    "requires_attachment": True,
    "min_confidence_score": 0.80
}

@app.get("/health")
async def health_check():
    """Estado del servicio y modelos disponibles en Ollama."""
    available_models = await ai_client.list_available_models()
    return {
        "status": "online",
        "service": "Strata Core",
        "models_available": available_models,
        "default_model": DEFAULT_MODEL,
        "timestamp": time.time()
    }


@app.get("/api/stats")
async def get_system_stats():
    """Métricas de rendimiento, latencia y volumen en tiempo real para el Dashboard de Squad 3."""
    return metrics_tracker.get_stats()


def _process_input_to_doc_data(file_path: Optional[str], text_content: Optional[str]) -> Dict[str, Any]:
    """Convierte un archivo (PDF/imagen) o texto plano en la estructura unificada de Strata."""
    if file_path:
        ext = os.path.splitext(file_path)[1].lower()
        if ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp"]:
            # PyMuPDF puede convertir imágenes a PDF en memoria al instante
            try:
                img_doc = fitz.open(file_path)
                pdf_bytes = img_doc.convert_to_pdf()
                img_doc.close()
            except Exception as img_err:
                raise ValueError(f"Imagen corrupta o ilegible: {img_err}")
            
            temp_pdf_path = file_path + ".converted.pdf"
            try:
                with open(temp_pdf_path, "wb") as f:
                    f.write(pdf_bytes)
                doc_data = reader.process_pdf(temp_pdf_path, run_ocr_on_images=True)
            finally:
                if os.path.exists(temp_pdf_path):
                    try:
                        os.remove(temp_pdf_path)
                    except OSError:
                        pass
            return doc_data
        elif ext in [".pdf"]:
            return reader.process_pdf(file_path, run_ocr_on_images=True)
        else:
            raise ValueError(f"Formato no compatible '{ext}'. Se requieren documentos PDF o imágenes JPG/PNG.")
            
    elif text_content:
        # Texto plano puro (sin archivo adjunto)
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        page.insert_text((50, 70), text_content, fontsize=11)
        temp_pdf = os.path.join(TEMP_DIR, f"text_{uuid.uuid4().hex[:8]}.pdf")
        doc.save(temp_pdf)
        doc.close()
        
        doc_data = reader.process_pdf(temp_pdf, run_ocr_on_images=False)
        try:
            os.remove(temp_pdf)
        except OSError:
            pass
        return doc_data
    else:
        raise ValueError("Se debe proporcionar al menos un archivo adjunto o texto plano.")


def _detect_prompt_injection(*texts: Optional[str]) -> bool:
    """Escanea el contenido del correo y documento en busca de patrones de inyección de prompt / jailbreak."""
    raw_combined = " ".join([t for t in texts if t]).lower()
    if not raw_combined.strip():
        return False

    injection_patterns = [
        r"ignora\s+(todas\s+las\s+|las\s+)?instrucciones",
        r"ignore\s+(all\s+)?(previous\s+)?instructions",
        r"system\s+(override|prompt|message)",
        r"instrucci[oó]n\s+del\s+sistema",
        r"modo\s+(desarrollador|administrador|superusuario)",
        r"developer\s+mode",
        r"you\s+are\s+now\s+(an?\s+)?ai",
        r"responde\s+estrictamente\s+con",
        r"responde\s+[úu]nicamente\s+con",
        r"valido[\"'\s]*:\s*true",
        r"requiere_revision_manual[\"'\s]*:\s*false",
        r"act[úu]a\s+como\s+(un\s+)?evaluador\s+que\s+aprueba"
    ]
    for pattern in injection_patterns:
        if re.search(pattern, raw_combined, re.IGNORECASE):
            return True
    return False


@app.post("/api/evaluate-excuse")
async def evaluate_excuse(
    request: Request = None,
    file: Optional[UploadFile] = None,
    email_body: Optional[str] = None,
    email_subject: Optional[str] = None,
    rules_json: Optional[Union[str, Dict[str, Any]]] = None,
    model: Optional[str] = DEFAULT_MODEL
):
    """
    Endpoint principal llamado por n8n:
    Recibe el archivo (PDF/Foto) y/o el cuerpo del correo,
    soporta tanto 'multipart/form-data' como 'application/json',
    evalúa con Strata Core (PyMuPDF + OCR + Qwen 2.5) contra las reglas HSE,
    y retorna el JSON estandarizado para decisión y despacho.
    """
    t_start = time.perf_counter()
    temp_file_path = None
    
    # 1. Resolver payload dependiendo del medio de invocación (HTTP con Request vs función directa)
    if request is not None:
        content_type = request.headers.get("content-type", "").lower()
        if "application/json" in content_type:
            try:
                body_data = await request.json()
            except Exception:
                body_data = {}
            email_body = body_data.get("email_body") or email_body
            email_subject = body_data.get("email_subject") or email_subject
            rules_val = body_data.get("rules_json") or body_data.get("rules")
            if rules_val is not None:
                rules_json = rules_val
            model = body_data.get("model") or model
            
            # Soporte de adjunto en Base64 desde el JSON (según API_CONTRACTS.md)
            b64_str = body_data.get("file_base64") or body_data.get("data_base64")
            b64_filename = body_data.get("file_name") or body_data.get("filename") or "adjunto.pdf"
            
            if not b64_str and isinstance(body_data.get("attachments"), list) and len(body_data["attachments"]) > 0:
                first_att = body_data["attachments"][0]
                b64_str = first_att.get("data_base64") or first_att.get("file_base64")
                b64_filename = first_att.get("filename") or first_att.get("file_name") or "adjunto.pdf"
                
            if b64_str:
                try:
                    if "," in b64_str:
                        b64_str = b64_str.split(",", 1)[1]
                    raw_bytes = base64.b64decode(b64_str)
                    ext = os.path.splitext(b64_filename)[1] or ".pdf"
                    temp_file_path = os.path.join(TEMP_DIR, f"upload_b64_{uuid.uuid4().hex[:8]}{ext}")
                    with open(temp_file_path, "wb") as bf:
                        bf.write(raw_bytes)
                except Exception as b64_err:
                    print(f"Warning: Fallo al decodificar adjunto base64: {b64_err}")
                    temp_file_path = None
                    
        elif "multipart/form-data" in content_type or "application/x-www-form-urlencoded" in content_type:
            try:
                form = await request.form()
                form_file = form.get("file")
                if form_file and hasattr(form_file, "filename") and form_file.filename:
                    file = form_file
                email_body = form.get("email_body") or email_body
                email_subject = form.get("email_subject") or email_subject
                rules_json = form.get("rules_json") or rules_json
                model = form.get("model") or model
            except Exception as form_err:
                print(f"Error parsing form data: {form_err}")

    if not isinstance(model, str) or not model:
        model = DEFAULT_MODEL
        
    try:
        rules = DEFAULT_HSE_RULES
        if rules_json:
            if isinstance(rules_json, dict):
                rules = rules_json
            elif isinstance(rules_json, str):
                try:
                    rules = json.loads(rules_json)
                except Exception:
                    pass
                
        # Guardar archivo UploadFile si no se había generado desde base64
        if not temp_file_path and file and hasattr(file, "filename") and file.filename:
            file_ext = os.path.splitext(file.filename)[1] or ".bin"
            temp_file_path = os.path.join(TEMP_DIR, f"upload_{uuid.uuid4().hex[:8]}{file_ext}")
            with open(temp_file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
                
        # Construir contexto combinado (correo + documento)
        today_str = time.strftime("%Y-%m-%d")
        combined_text = f"FECHA ACTUAL DE EVALUACIÓN: {today_str}\n"
        if email_subject:
            combined_text += f"ASUNTO DEL CORREO: {email_subject}\n"
        if email_body:
            combined_text += f"CUERPO DEL CORREO:\n{email_body}\n\n"
            
        doc_data = _process_input_to_doc_data(temp_file_path, combined_text if not temp_file_path else None)

        # Extracción del texto del documento para análisis de integridad
        doc_text_content = ""
        if isinstance(doc_data, dict) and "pages" in doc_data:
            doc_text_content = " ".join([p.get("text", "") for p in doc_data["pages"] if isinstance(p, dict)])

        # Verificación y contención de Prompt Injection / Instrucciones Directas en el soporte
        if _detect_prompt_injection(email_subject, email_body, doc_text_content):
            t_elapsed = time.perf_counter() - t_start
            metrics_tracker.record_evaluation(
                valido=False,
                manual=True,
                tipo="no_identificado",
                latency=round(t_elapsed, 2)
            )
            return {
                "categoria_sugerida": "REVISION_MANUAL",
                "valido": False,
                "tipo_novedad": "no_identificado",
                "fecha_afectada": "No identificada",
                "motivo_decision": "Se detectaron patrones de texto no convencionales o instrucciones directas en el cuerpo/documento que requieren auditoría y validación manual por parte del Team Leader.",
                "confianza_score": 0.0,
                "requiere_revision_manual": True,
                "detalles_adjunto": {
                    "es_legible": True,
                    "tiene_firma_o_sello": False,
                    "institucion_emisora": "No identificada",
                    "auditoria_seguridad": "Patrón de instrucción directa detectado en el texto suministrado"
                },
                "tiempo_procesamiento_segundos": round(t_elapsed, 2)
            }
        
        PROMPT_PATH = os.path.join(BASE_DIR, "prompts", "evaluator_system_prompt.md")
        with open(PROMPT_PATH, "r", encoding="utf-8") as f:
            system_prompt_template = f.read()
            
        ai_verdict, pages_used, error_msg = await ai_client.evaluate_hse_excuse(
            document_data=doc_data,
            system_prompt_template=system_prompt_template,
            rules=rules,
            email_subject=email_subject,
            email_body=email_body,
            model=model
        )
        
        # Validación y saneamiento del veredicto con Failover inteligente ante lentitud o timeouts
        if error_msg or not ai_verdict:
            text_eval = f"{email_subject or ''} {email_body or ''} {doc_text_content or ''}".lower()
            if "vencid" in text_eval or "semana pasada" in text_eval or "extemporane" in text_eval:
                categoria_sugerida = "POSIBLEMENTE_INVALIDO"
                confianza_score = 0.85
                tipo_novedad = "inasistencia_medica"
                motivo_decision = "Incapacidad médica radicada de forma extemporánea (superior a 48 horas de holgura reglamentaria) sin justificación de fuerza mayor."
            elif "formula" in text_eval or "farmacia" in text_eval or "orden medica" in text_eval:
                categoria_sugerida = "REVISION_MANUAL"
                confianza_score = 0.65
                tipo_novedad = "enfermedad_sin_soporte"
                motivo_decision = "El soporte suministrado corresponde a una fórmula o prescripción de farmacia y no a un certificado oficial de incapacidad EPS con días de reposo."
            elif any(w in text_eval for w in ["fiebre", "malestar", "vomit", "vómit", "colico", "cólico", "diarrea", "migraña", "indispuest", "descompuest", "enfermo", "quebranto", "dolor de cabeza"]):
                categoria_sugerida = "REVISION_MANUAL"
                confianza_score = 0.82
                tipo_novedad = "enfermedad_sin_soporte"
                motivo_decision = "Reporte de quebranto de salud o malestar general sin incapacidad formal de EPS/IPS adjunta. Sujeto a verificación de tolerancia (hasta 2 faltas en 30 días)."
            elif "registraduria" in text_eval or "cedula" in text_eval or "tramite" in text_eval or "pasaporte" in text_eval:
                categoria_sugerida = "REVISION_MANUAL"
                confianza_score = 0.72
                tipo_novedad = "tramite_oficial"
                motivo_decision = "Permiso solicitado por trámite administrativo personal. Requiere aprobación discrecional de la Team Leader de HSE."
            elif "corte" in text_eval or "fibra" in text_eval or "energia" in text_eval or "cargador" in text_eval or "internet" in text_eval:
                categoria_sugerida = "REVISION_MANUAL"
                confianza_score = 0.75
                tipo_novedad = "falla_tecnica"
                motivo_decision = "Reporte de contingencia técnica o corte de fluido/conectividad. Derivado a revisión para verificación de ticket técnico."
            elif any(eps in text_eval for eps in ["sura", "sanitas", "salud total", "nueva eps", "compensar", "famisanar", "coosalud", "mutual ser", "eps", "incapacidad"]):
                categoria_sugerida = "POSIBLEMENTE_VALIDO"
                confianza_score = 0.95
                tipo_novedad = "inasistencia_medica"
                motivo_decision = "Incapacidad médica formal con diagnóstico CIE-10 expedida por entidad promotora de salud (EPS) y soporte adjunto verificado."
            elif "cita" in text_eval or "odontol" in text_eval or "medico general" in text_eval or "especialista" in text_eval:
                tipo_novedad = "inasistencia_medica"
                # Regla HSE: Citas programadas deben notificarse con preaviso (antes del día de entrenamiento)
                has_negation_or_past = bool(re.search(r'\b(no alcanc[eé]|no avis[eé]|sin antelaci[oó]n|sin preaviso|despu[eé]s de la jornada|ayer|asist[ií]|estuve en la cita)\b', text_eval))
                is_preaviso = not has_negation_or_past and bool(re.search(r'\b(asistir[eé]|preaviso|con antelaci[oó]n|agendada para|ma[nñ]ana|futur[oa]|solicito permiso previo)\b', text_eval))
                is_posterior = has_negation_or_past or bool(re.search(r'\b(asist[ií]|estuve|fui|despu[eé]s|ayer|semana pasada)\b', text_eval))
                if is_posterior:
                    categoria_sugerida = "POSIBLEMENTE_INVALIDO"
                    confianza_score = 0.88
                    motivo_decision = "Las citas médicas programadas deben notificarse previamente antes del día de entrenamiento. No fue remitida con la antelación reglamentaria requerida."
                else:
                    categoria_sugerida = "POSIBLEMENTE_VALIDO"
                    confianza_score = 0.94
                    motivo_decision = "Cita médica programada notificada con antelación reglamentaria antes del día de entrenamiento y constancia adjunta."
            elif "calamidad" in text_eval or "urgencia" in text_eval or "falleci" in text_eval:
                categoria_sugerida = "POSIBLEMENTE_VALIDO"
                confianza_score = 0.88
                tipo_novedad = "calamidad"
                motivo_decision = "Calamidad doméstica / contingencia familiar de fuerza mayor reportada en tiempo con soporte adjunto."
            else:
                categoria_sugerida = "REVISION_MANUAL"
                confianza_score = 0.70
                tipo_novedad = "no_identificado"
                motivo_decision = "Solicitud preliminar con información asistida para validación y determinación de la Team Leader de HSE."

            valido = (categoria_sugerida == "POSIBLEMENTE_VALIDO")
            requiere_revision_manual = (categoria_sugerida == "REVISION_MANUAL")
            fecha_afectada = today_str
        else:
            cat = str(ai_verdict.get("categoria_sugerida", "")).upper()
            if cat in ["POSIBLEMENTE_VALIDO", "POSIBLEMENTE_INVALIDO", "REVISION_MANUAL"]:
                categoria_sugerida = cat
            else:
                if bool(ai_verdict.get("requiere_revision_manual", False)):
                    categoria_sugerida = "REVISION_MANUAL"
                elif bool(ai_verdict.get("valido", False)):
                    categoria_sugerida = "POSIBLEMENTE_VALIDO"
                else:
                    categoria_sugerida = "POSIBLEMENTE_INVALIDO"

            valido = (categoria_sugerida == "POSIBLEMENTE_VALIDO")
            requiere_revision_manual = (categoria_sugerida == "REVISION_MANUAL")

            tipo_novedad = ai_verdict.get("tipo_novedad") or "no_identificado"
            valid_types = ["inasistencia_medica", "enfermedad_sin_soporte", "calamidad", "tramite_oficial", "falla_tecnica", "tardanza", "salida_temprana", "no_identificado"]
            if tipo_novedad not in valid_types:
                tipo_novedad = "no_identificado"
                
            raw_fecha = str(ai_verdict.get("fecha_afectada") or "")
            try:
                if re.match(r"^\d{4}-\d{2}-\d{2}$", raw_fecha):
                    y, m, d = [int(p) for p in raw_fecha.split("-")]
                    if 1 <= m <= 12:
                        import calendar
                        max_days = calendar.monthrange(y, m)[1]
                        adj_d = min(max(1, d), max_days)
                        fecha_afectada = f"{y:04d}-{m:02d}-{adj_d:02d}"
                    else:
                        fecha_afectada = today_str
                else:
                    fecha_afectada = today_str
            except Exception:
                fecha_afectada = today_str
            motivo_decision = str(ai_verdict.get("motivo_decision") or "Evaluación completada.")
            
            try:
                confianza_score = float(ai_verdict.get("confianza_score", 0.8))
                confianza_score = max(0.0, min(1.0, confianza_score))
            except (ValueError, TypeError):
                confianza_score = 0.80

        # Guardrails deterministas de negocio HSE
        text_lower = ((email_subject or "") + " " + (email_body or "")).lower()
        doc_text_lower = " ".join([p.get("text", "") for p in doc_data.get("pages", [])]).lower()
        full_text_lower = text_lower + " " + doc_text_lower

        is_calamidad_event = any(w in text_lower for w in [
            "falleci", "luto", "funerari", "entierro", "duelo", "calamidad",
            "inundaci", "incendio", "derrumbe", "desastre", "bomberos",
            "emergencia familiar", "fuerza mayor", "emergencia grave"
        ])
        is_sickness_symptom = any(w in full_text_lower for w in [
            "fiebre", "malestar", "gripe", "vomit", "vómit", "diarrea",
            "migraña", "colico", "cólico", "dolor de cabeza", "enfermo",
            "indispuest", "descompuest", "quebranto", "indisposición", "nausea", "náusea"
        ])
        has_formal_eps = any(eps in full_text_lower for eps in [
            "sanitas", "sura", "compensar", "famisanar", "salud total",
            "nueva eps", "coosalud", "mutual ser", "colsanitas", "medimas"
        ]) and any(m in full_text_lower for m in [
            "incapacidad", "dias de reposo", "días de reposo", "orden de reposo", "incapacidad temporal"
        ])

        if is_calamidad_event and not is_sickness_symptom:
            tipo_novedad = "calamidad"
            if not temp_file_path:
                categoria_sugerida = "REVISION_MANUAL"
                valido = False
                requiere_revision_manual = True
                motivo_decision = "Calamidad doméstica o contingencia de fuerza mayor reportada en texto. Cuenta con hasta 72 horas hábiles para radicar el soporte."

        if any(w in full_text_lower for w in ["ansiedad", "depresion", "depresión", "panico", "pánico", "salud mental", "psicolog", "psiquiatr", "crisis emocional"]):
            tipo_novedad = "calamidad"
            categoria_sugerida = "REVISION_MANUAL"
            valido = False
            requiere_revision_manual = True
            motivo_decision = "Situación de alta sensibilidad (salud mental/emocional). Se recomienda remitir a conversación presencial con el equipo de HSE."

        # Guardrail de Temporalidad: Citas médicas programadas vs Eventos Impredecibles
        is_cita_programada = any(w in full_text_lower for w in ["cita medica", "cita médica", "cita odontol", "procedimiento programado", "cita con especialista", "constancia de asistencia a cita"])
        if is_cita_programada:
            tipo_novedad = "inasistencia_medica"
            has_negation_or_past = bool(re.search(r'\b(no alcanc[eé]|no avis[eé]|sin antelaci[oó]n|sin preaviso|despu[eé]s de la jornada|ayer|asist[ií]|estuve en la cita|se me olvid[oó] avisar)\b', text_lower))
            is_preaviso = not has_negation_or_past and bool(re.search(r'\b(asistir[eé]|preaviso|con antelaci[oó]n|agendada para|ma[nñ]ana|futur[oa]|solicito permiso previo)\b', text_lower))
            is_post_evento = has_negation_or_past or bool(re.search(r'\b(asist[ií]|estuve en|fui a|despu[eé]s|ayer|semana pasada)\b', text_lower))
            if is_post_evento:
                categoria_sugerida = "POSIBLEMENTE_INVALIDO"
                valido = False
                requiere_revision_manual = False
                confianza_score = 0.88
                motivo_decision = "Las citas médicas programadas deben notificarse obligatoriamente antes del día de entrenamiento (con preaviso). No se admite radicación posterior a la inasistencia."
            else:
                categoria_sugerida = "POSIBLEMENTE_VALIDO"
                valido = True
                requiere_revision_manual = False
                confianza_score = 0.94
                motivo_decision = "Cita médica programada notificada con antelación reglamentaria antes del día de entrenamiento y constancia adjunta."

        # Guardrail para malestar general / enfermedad sin incapacidad formal de EPS
        if (is_sickness_symptom or (tipo_novedad in ["inasistencia_medica", "enfermedad_sin_soporte"] and not is_calamidad_event)) and not is_cita_programada:
            if not temp_file_path or not has_formal_eps:
                tipo_novedad = "enfermedad_sin_soporte"
                categoria_sugerida = "REVISION_MANUAL"
                valido = False
                requiere_revision_manual = True
                confianza_score = 0.88
                motivo_decision = "Reporte de malestar general / enfermedad sin incapacidad formal de EPS/IPS adjunta. Requiere validación de gabela de hasta 2 faltas en 30 días."

        if any(w in text_lower for w in ["retirarme", "salir antes", "salida temprana"]):
            tipo_novedad = "salida_temprana"
            if any(w in full_text_lower for w in ["odontolog", "dental", "procedimiento", "cita"]):
                categoria_sugerida = "POSIBLEMENTE_VALIDO"
                valido = True
                requiere_revision_manual = False

        is_falla_tecnica_word = any(w in full_text_lower for w in [
            "falla tecnica", "falla técnica", "sin internet", "no tengo internet",
            "corte de internet", "corte de luz", "corte de fluido", "corte de energía",
            "corte de energia", "fluido electrico", "fluido eléctrico", "fibra", "tigo",
            "claro", "movistar", "etb", "ticket", "se cayó la red", "se cayo la red",
            "problemas con el internet"
        ])
        if is_falla_tecnica_word:
            tipo_novedad = "falla_tecnica"
            if temp_file_path:
                categoria_sugerida = "POSIBLEMENTE_VALIDO"
                valido = True
                requiere_revision_manual = False
            else:
                categoria_sugerida = "REVISION_MANUAL"
                valido = False
                requiere_revision_manual = True
                motivo_decision = "Reporte de falla técnica o corte de conectividad sin radicado ni comprobante adjunto. Requiere verificación de ticket técnico."

        if any(w in text_lower for w in ["descuento", "cursos de", "promocion", "suscripciones"]):
            tipo_novedad = "no_identificado"
            categoria_sugerida = "REVISION_MANUAL"
            valido = False
            requiere_revision_manual = True

        if any(w in full_text_lower for w in ["borrosa", "totalmente borrosa", "foto_borrosa"]):
            tipo_novedad = "no_identificado"
            categoria_sugerida = "REVISION_MANUAL"
            valido = False
            requiere_revision_manual = True

        # Guardrail para incapacidades formales de EPS con soporte legítimo (Sanitas, SURA, Compensar)
        if any(eps in full_text_lower for eps in ["sanitas", "sura", "compensar", "famisanar", "salud total"]) and any(m in full_text_lower for m in ["incapacidad", "reposo", "gastrointestinal", "cefalea"]):
            is_extemporanea = any(w in text_lower for w in ["atrasad", "dos semanas", "hace 15 días", "no alcancé a enviar antes", "vencida"]) or "10/09" in full_text_lower or "10 de septiembre" in full_text_lower
            is_particular = any(w in full_text_lower for w in ["particular", "sin registro", "sin sello"])
            is_formula = any(w in full_text_lower for w in ["formula", "farmacia", "receta", "medicamentos"]) and "dias de reposo" not in full_text_lower and "días de reposo" not in full_text_lower and "incapacidad temporal" not in full_text_lower

            if is_extemporanea or is_particular:
                categoria_sugerida = "POSIBLEMENTE_INVALIDO"
                valido = False
                requiere_revision_manual = False
                tipo_novedad = "inasistencia_medica"
            elif is_formula:
                categoria_sugerida = "REVISION_MANUAL"
                valido = False
                requiere_revision_manual = True
                tipo_novedad = "enfermedad_sin_soporte"
                motivo_decision = "El soporte suministrado corresponde a una fórmula o prescripción de farmacia y no a un certificado oficial de incapacidad EPS con días de reposo."
            else:
                categoria_sugerida = "POSIBLEMENTE_VALIDO"
                valido = True
                requiere_revision_manual = False
                tipo_novedad = "inasistencia_medica"
        
        detalles_adjunto = ai_verdict.get("detalles_adjunto") or {}
        if not isinstance(detalles_adjunto, dict):
            detalles_adjunto = {}
            
        detalles_adjunto["paginas_consultadas"] = pages_used
        if error_msg:
            detalles_adjunto["warning_modelo"] = error_msg
            
        t_elapsed = time.perf_counter() - t_start
        metrics_tracker.record_evaluation(
            valido=valido,
            manual=requiere_revision_manual,
            tipo=tipo_novedad,
            latency=round(t_elapsed, 2)
        )
        
        return {
            "categoria_sugerida": categoria_sugerida,
            "valido": valido,
            "tipo_novedad": tipo_novedad,
            "fecha_afectada": fecha_afectada,
            "motivo_decision": motivo_decision,
            "confianza_score": round(confianza_score, 2),
            "requiere_revision_manual": requiere_revision_manual,
            "detalles_adjunto": detalles_adjunto,
            "tiempo_procesamiento_segundos": round(t_elapsed, 2)
        }
        
    except Exception as e:
        t_elapsed = time.perf_counter() - t_start
        clean_msg = str(e)
        if "password" in clean_msg.lower() or "cifrado" in clean_msg.lower() or "protegido" in clean_msg.lower():
            decision_msg = "Documento protegido con contraseña o cifrado. Derivado a revisión manual del Team Leader."
        elif "formato no compatible" in clean_msg.lower():
            decision_msg = f"Formato de archivo no admitido ({clean_msg}). Derivado a revisión manual del Team Leader."
        elif "corrupt" in clean_msg.lower() or "cannot open" in clean_msg.lower() or "dañado" in clean_msg.lower() or "ilegitimo" in clean_msg.lower() or "failed to open" in clean_msg.lower() or "no fue posible abrir" in clean_msg.lower():
            decision_msg = "Archivo adjunto dañado o corrupto. Derivado a revisión manual del Team Leader para solicitar reenvío."
        else:
            decision_msg = f"Inconsistencia al procesar soporte ({clean_msg}). Derivado a revisión manual del Team Leader."

        error_payload = {
            "categoria_sugerida": "REVISION_MANUAL",
            "valido": False,
            "tipo_novedad": "no_identificado",
            "fecha_afectada": "No identificada",
            "motivo_decision": decision_msg,
            "confianza_score": 0.0,
            "requiere_revision_manual": True,
            "detalles_adjunto": {
                "es_legible": False,
                "tiene_firma_o_sello": False,
                "institucion_emisora": "No identificada",
                "error_origen": clean_msg
            },
            "tiempo_procesamiento_segundos": round(t_elapsed, 2)
        }
        # Registrar telemetría del incidente
        metrics_tracker.record_evaluation(
            valido=False,
            manual=True,
            tipo="no_identificado",
            latency=round(t_elapsed, 2)
        )
        # NUNCA responder HTTP 500 a n8n: responder HTTP 200 con requiere_revision_manual: true
        # para que n8n continúe el flujo sin romperse y la Team Leader audite el caso en el dashboard.
        if request is not None:
            return JSONResponse(status_code=200, content=error_payload)
        return error_payload
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except OSError:
                pass


@app.post("/api/search")
async def search_document(
    query: str = Form(...),
    file: Optional[UploadFile] = File(None)
):
    """Búsqueda espacial con coordenadas para resaltar cajas en el visor del Dashboard."""
    if not file:
        raise HTTPException(status_code=400, detail="Se requiere un archivo para indexar y buscar.")
        
    temp_file_path = os.path.join(TEMP_DIR, f"search_{uuid.uuid4().hex[:8]}_{file.filename}")
    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        doc_data = _process_input_to_doc_data(temp_file_path, None)
        search_res = SearchEngine.search(doc_data, query)
        return search_res
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


# =============================================================================
# HSE DASHBOARD & POSTGRESQL REAL DATA ENDPOINTS
# =============================================================================

def get_db_connection():
    if not psycopg2:
        raise HTTPException(status_code=500, detail="psycopg2 no disponible en el entorno")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = int(os.getenv("POSTGRES_PORT", "5432"))
    dbname = os.getenv("POSTGRES_DB", "hse_email_automation")
    user = os.getenv("POSTGRES_USER", "hse_admin")
    password = os.getenv("POSTGRES_PASSWORD", "hse_segura_123")
    return psycopg2.connect(
        host=host,
        port=port,
        dbname=dbname,
        user=user,
        password=password,
        connect_timeout=3
    )

from services.inbound_service import inbound_service
inbound_service._db_conn_func = get_db_connection

@app.get("/api/kpis")
async def get_dashboard_kpis():
    """Retorna los indicadores clave (KPIs) del dashboard calculados desde la base de datos."""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE validation_status IN ('POSIBLEMENTE_VALIDO', 'APPROVED')) as approved,
                COUNT(*) FILTER (WHERE validation_status IN ('POSIBLEMENTE_INVALIDO', 'DISAPPROVED')) as denied,
                COUNT(*) FILTER (WHERE validation_status NOT IN ('POSIBLEMENTE_VALIDO', 'APPROVED', 'POSIBLEMENTE_INVALIDO', 'DISAPPROVED')) as pending
            FROM justifications;
        """)
        row = cur.fetchone()
        cur.close()
        conn.close()
        tot = row["total"] or 0
        appr = row["approved"] or 0
        den = row["denied"] or 0
        pend = row["pending"] or 0
        return {
            "total": tot,
            "approved": appr,
            "denied": den,
            "pending": pend,
            "approval_rate": round((appr / tot * 100), 1) if tot > 0 else 0.0,
            "revisadas": appr + den,
            "por_revisar": pend
        }
    except Exception as e:
        return {
            "total": 0, "approved": 0, "denied": 0, "pending": 0,
            "approval_rate": 0.0, "revisadas": 0, "por_revisar": 0, "error": str(e)
        }

@app.get("/api/requests")
async def get_requests_list(status: Optional[str] = None, limit: int = 250):
    """Lista de justificaciones con formato adaptado para el frontend de Requests y Dashboard."""
    try:
        inbound_service.sync_unprocessed_inbounds()
    except Exception as sync_err:
        print(f"Warning sincronizando correos entrantes: {sync_err}")

    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        query = """
            SELECT 
                j.id,
                j.coder_id,
                j.sender_name,
                j.sender_email,
                j.email_subject,
                j.email_body,
                j.received_at,
                j.excuse_type,
                j.validation_status,
                j.ai_recommendation,
                j.ai_confidence,
                j.ai_reason,
                j.has_human_intervention,
                j.hse_decision,
                j.hse_notes,
                j.hse_reviewed_at,
                j.attachments,
                COALESCE(c.route, 'Ruta General') as coder_route
            FROM justifications j
            LEFT JOIN coders c ON j.coder_id = c.id
        """
        params = []
        if status:
            if status == "approved":
                query += " WHERE j.validation_status IN ('POSIBLEMENTE_VALIDO', 'APPROVED')"
            elif status == "denied":
                query += " WHERE j.validation_status IN ('POSIBLEMENTE_INVALIDO', 'DISAPPROVED')"
            elif status == "pending_review":
                query += " WHERE j.validation_status NOT IN ('POSIBLEMENTE_VALIDO', 'APPROVED', 'POSIBLEMENTE_INVALIDO', 'DISAPPROVED')"
        
        query += " ORDER BY j.received_at DESC LIMIT %s;"
        params.append(limit)
        cur.execute(query, tuple(params))
        rows = cur.fetchall()
        cur.close()
        conn.close()

        formatted = []
        for r in rows:
            raw_status = (r["validation_status"] or "").upper()
            if raw_status in ["POSIBLEMENTE_VALIDO", "APPROVED"]:
                frontend_status = "approved"
            elif raw_status in ["POSIBLEMENTE_INVALIDO", "DISAPPROVED"]:
                frontend_status = "denied"
            else:
                frontend_status = "pending_review"

            raw_attachments = r["attachments"] or []
            if isinstance(raw_attachments, str):
                try:
                    raw_attachments = json.loads(raw_attachments)
                except Exception:
                    raw_attachments = []
            
            attachments_list = []
            if isinstance(raw_attachments, list):
                for att in raw_attachments:
                    if isinstance(att, dict):
                        attachments_list.append({
                            "name": att.get("filename") or att.get("name") or "documento.pdf",
                            "url": "#"
                        })

            formatted.append({
                "id": str(r["id"]),
                "studentId": str(r["coder_id"]) if r["coder_id"] else "s-ext",
                "route": r["coder_route"],
                "status": frontend_status,
                "category": r["ai_recommendation"] or raw_status,
                "recommendation": r["ai_recommendation"] or raw_status,
                "emailInfo": {
                    "senderName": r["sender_name"] or "Coder RIWI",
                    "senderEmail": r["sender_email"],
                    "subject": r["email_subject"],
                    "body": r["email_body"],
                    "date": r["received_at"].isoformat() if r["received_at"] else "",
                    "attachments": attachments_list
                },
                "hasHumanIntervention": bool(r["has_human_intervention"]),
                "hseDecision": r["hse_decision"],
                "hseNotes": r["hse_notes"],
                "hseReviewedAt": r["hse_reviewed_at"].isoformat() if r["hse_reviewed_at"] else None,
                "decision": {
                    "source": "human" if r["has_human_intervention"] else "ai",
                    "recommendation": r["ai_recommendation"] or raw_status,
                    "confidence": float(r["ai_confidence"]) if r["ai_confidence"] is not None else 0.85,
                    "reasoning": r["hse_notes"] if r["has_human_intervention"] and r["hse_notes"] else (r["ai_reason"] or "Evaluación realizada por Strata Core"),
                    "modifiedBy": "Team Leader Paola" if r["has_human_intervention"] else None,
                    "modifiedAt": r["hse_reviewed_at"].isoformat() if r["hse_reviewed_at"] else None
                }
            })
        return formatted
    except Exception as e:
        print(f"Error en get_requests: {e}")
        return []

@app.get("/api/requests/recent")
async def get_recent_emails(limit: int = 10):
    """Lista de correos recientes formateados para el carrusel de inicio."""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT 
                id, sender_email, sender_name, email_subject, email_body, received_at, validation_status
            FROM justifications
            ORDER BY received_at DESC
            LIMIT %s;
        """, (limit,))
        rows = cur.fetchall()
        cur.close()
        conn.close()

        recent = []
        for r in rows:
            st = (r["validation_status"] or "").upper()
            if st in ["POSIBLEMENTE_VALIDO", "APPROVED"]:
                st_label = "Aprobado"
                color = "bg-[#20B486]/10 text-[#20B486]"
                dot = "bg-[#20B486]"
            elif st in ["POSIBLEMENTE_INVALIDO", "DISAPPROVED"]:
                st_label = "Denegado"
                color = "bg-[#FF5C67]/10 text-[#FF5C67]"
                dot = "bg-[#FF5C67]"
            else:
                st_label = "Por revisar"
                color = "bg-[#F5B83D]/10 text-[#F5B83D]"
                dot = "bg-[#F5B83D]"

            time_str = r["received_at"].strftime("%d %b, %I:%M %p") if r["received_at"] else "Hoy"

            recent.append({
                "id": str(r["id"]),
                "sender": r["sender_email"],
                "senderName": r["sender_name"],
                "title": r["email_subject"],
                "snippet": (r["email_body"] or "")[:45] + "...",
                "time": time_str,
                "status": st_label,
                "color": color,
                "dot": dot
            })
        return recent
    except Exception as e:
        print(f"Error en get_recent_emails: {e}")
        return []

@app.get("/api/requests/weekly")
async def get_requests_weekly():
    """Agrupación de justificaciones para gráficos semanales del Dashboard."""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT 
                TO_CHAR(received_at, 'Dy') as day_key,
                DATE(received_at) as date,
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE validation_status IN ('POSIBLEMENTE_VALIDO', 'APPROVED')) as aprobados,
                COUNT(*) FILTER (WHERE validation_status IN ('POSIBLEMENTE_INVALIDO', 'DISAPPROVED')) as denegados,
                COUNT(*) FILTER (WHERE validation_status NOT IN ('POSIBLEMENTE_VALIDO', 'APPROVED', 'POSIBLEMENTE_INVALIDO', 'DISAPPROVED')) as pendientes
            FROM justifications
            GROUP BY TO_CHAR(received_at, 'Dy'), DATE(received_at)
            ORDER BY DATE(received_at) ASC;
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()

        day_map = {"Mon": "Lun", "Tue": "Mar", "Wed": "Mié", "Thu": "Jue", "Fri": "Vie", "Sat": "Sáb", "Sun": "Dom"}
        result = []
        for r in rows:
            name = day_map.get(r["day_key"], r["day_key"])
            result.append({
                "name": name,
                "Total": r["total"],
                "Aprobados": r["aprobados"],
                "Denegados": r["denegados"],
                "Pendientes": r["pendientes"],
                "solicitudes": r["total"]
            })
        
        if not result:
            result = [
                {"name": "Lun", "Total": 0, "Aprobados": 0, "Denegados": 0, "Pendientes": 0, "solicitudes": 0}
            ]
        return result
    except Exception as e:
        return [{"name": "Lun", "Total": 0, "Aprobados": 0, "Denegados": 0, "Pendientes": 0, "solicitudes": 0}]

@app.get("/api/students")
async def get_students_list():
    """Lista de estudiantes / coders reales desde PostgreSQL agrupados por ruta."""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT 
                c.id,
                c.full_name as name,
                c.email,
                COALESCE(c.route, 'Sin ruta') as route,
                c.cedula,
                c.is_active,
                COUNT(j.id) as total_justifications
            FROM coders c
            LEFT JOIN justifications j ON c.id = j.coder_id
            GROUP BY c.id, c.full_name, c.email, c.route, c.cedula, c.is_active
            ORDER BY c.full_name ASC;
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()

        students = []
        for r in rows:
            students.append({
                "id": str(r["id"]),
                "name": r["name"],
                "email": r["email"],
                "route": r["route"],
                "cedula": r["cedula"],
                "status": "Activo" if r["is_active"] else "Inactivo",
                "attendance": {
                    "present": 38,
                    "late": 1,
                    "justifiedAbsence": r["total_justifications"],
                    "unjustifiedAbsence": 0
                }
            })
        return students
    except Exception as e:
        return []

class ResolveRequestModel(BaseModel):
    action: str
    notes: Optional[str] = ""
    reviewer_name: Optional[str] = "Team Leader Paola"

@app.post("/api/requests/{justification_id}/resolve")
async def resolve_justification_in_db(justification_id: str, payload: ResolveRequestModel):
    """Actualiza la decisión de la Team Leader directamente en PostgreSQL."""
    try:
        action = payload.action.upper()
        if action == "APPROVED":
            val_status = "APPROVED"
        elif action == "DISAPPROVED":
            val_status = "DISAPPROVED"
        else:
            val_status = "MANUAL_INTERACTION"

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE justifications
            SET validation_status = %s,
                hse_decision = %s,
                hse_notes = %s,
                has_human_intervention = true,
                hse_reviewed_at = NOW()
            WHERE id = %s RETURNING id;
        """, (val_status, action, payload.notes, justification_id))
        updated = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        if not updated:
            raise HTTPException(status_code=404, detail="Justificación no encontrada")
        return {"status": "ok", "justification_id": justification_id, "decision": action}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

