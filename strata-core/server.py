import asyncio
import json
import os
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

from engine.pdf_reader import PDFEngineReader
from engine.search_index import SearchEngine
from engine.ai_extractor import AIExtractor, DEFAULT_MODEL

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


def _process_input_to_doc_data(file_path: Optional[str], text_content: Optional[str]) -> Dict[str, Any]:
    """Convierte un archivo (PDF/imagen) o texto plano en la estructura unificada de Strata."""
    if file_path:
        ext = os.path.splitext(file_path)[1].lower()
        if ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp"]:
            # PyMuPDF puede convertir imágenes a PDF en memoria al instante
            img_doc = fitz.open(file_path)
            pdf_bytes = img_doc.convert_to_pdf()
            img_doc.close()
            
            temp_pdf_path = file_path + ".converted.pdf"
            with open(temp_pdf_path, "wb") as f:
                f.write(pdf_bytes)
            
            doc_data = reader.process_pdf(temp_pdf_path, run_ocr_on_images=True)
            try:
                os.remove(temp_pdf_path)
            except OSError:
                pass
            return doc_data
        else:
            return reader.process_pdf(file_path, run_ocr_on_images=True)
            
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
        combined_text = ""
        if email_subject:
            combined_text += f"ASUNTO DEL CORREO: {email_subject}\n"
        if email_body:
            combined_text += f"CUERPO DEL CORREO:\n{email_body}\n\n"
            
        doc_data = _process_input_to_doc_data(temp_file_path, combined_text if not temp_file_path else None)
        
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
        
        # Validación y saneamiento del veredicto para cumplir con evaluation_schema.json
        valido = bool(ai_verdict.get("valido", False))
        tipo_novedad = ai_verdict.get("tipo_novedad") or "no_identificado"
        valid_types = ["inasistencia_medica", "calamidad", "tramite_oficial", "falla_tecnica", "tardanza", "salida_temprana", "no_identificado"]
        if tipo_novedad not in valid_types:
            tipo_novedad = "no_identificado"
            
        fecha_afectada = str(ai_verdict.get("fecha_afectada") or "No identificada")
        motivo_decision = str(ai_verdict.get("motivo_decision") or "Evaluación completada.")
        
        try:
            confianza_score = float(ai_verdict.get("confianza_score", 0.8))
            confianza_score = max(0.0, min(1.0, confianza_score))
        except (ValueError, TypeError):
            confianza_score = 0.80
            
        requiere_revision_manual = bool(ai_verdict.get("requiere_revision_manual", False))
        
        detalles_adjunto = ai_verdict.get("detalles_adjunto") or {}
        if not isinstance(detalles_adjunto, dict):
            detalles_adjunto = {}
            
        detalles_adjunto["paginas_consultadas"] = pages_used
        if error_msg:
            detalles_adjunto["warning_modelo"] = error_msg
            
        t_elapsed = time.perf_counter() - t_start
        
        return {
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
        error_payload = {
                "valido": False,
                "tipo_novedad": "no_identificado",
                "fecha_afectada": "No identificada",
                "motivo_decision": f"Error interno en Strata Core al procesar documento: {str(e)}",
                "confianza_score": 0.0,
                "requiere_revision_manual": True,
                "error": str(e),
                "tiempo_procesamiento_segundos": round(t_elapsed, 2)
        }
        # Si hay request HTTP real, devolver JSONResponse con status 500;
        # si se invocó directamente (test runner), devolver dict plano.
        if request is not None:
            return JSONResponse(status_code=500, content=error_payload)
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
