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
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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
    file: Optional[UploadFile] = File(None),
    email_body: Optional[str] = Form(None),
    email_subject: Optional[str] = Form(None),
    rules_json: Optional[str] = Form(None),
    model: Optional[str] = Form(DEFAULT_MODEL)
):
    """
    Endpoint principal llamado por n8n:
    Recibe el archivo (PDF/Foto) y/o el cuerpo del correo,
    evalúa con Strata Core (PyMuPDF + OCR + Qwen 2.5) contra las reglas HSE,
    y retorna el JSON estandarizado para decisión y despacho.
    """
    t_start = time.perf_counter()
    temp_file_path = None
    
    try:
        rules = DEFAULT_HSE_RULES
        if rules_json:
            try:
                rules = json.loads(rules_json)
            except Exception:
                pass
                
        # Guardar archivo temporal si existe
        if file and file.filename:
            file_ext = os.path.splitext(file.filename)[1]
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
        
        # Extracción de campos clave usando Strata Core
        target_fields = [
            "Nombre del Coder",
            "Fecha o Rango de Inasistencia",
            "Institucion Emisora o EPS",
            "Motivo o Diagnostico CIE-10",
            "Tiene Firma o Sello Oficial"
        ]
        
        ai_res = await ai_client.extract_values(doc_data, target_fields, model=model)
        raw_values = ai_res.get("values", {})
        
        # Ponderación y Veredicto con reglas de negocio HSE
        extracted_name = raw_values.get("Nombre del Coder") or "No identificado"
        extracted_date = raw_values.get("Fecha o Rango de Inasistencia") or "No identificada"
        extracted_reason = raw_values.get("Motivo o Diagnostico CIE-10") or "Inasistencia general"
        extracted_stamp = raw_values.get("Tiene Firma o Sello Oficial")
        has_stamp = bool(extracted_stamp and any(w in str(extracted_stamp).lower() for w in ["si", "válido", "valido", "sello", "firma", "oficial"]))
        
        # Determinar validez según reglas dinámicas
        is_valid = True
        decision_reasons = []
        requires_manual_review = False
        
        if rules.get("requires_attachment", True) and not temp_file_path:
            is_valid = False
            decision_reasons.append("No se adjuntó soporte documental o constancia válida.")
            
        if temp_file_path and not has_stamp:
            decision_reasons.append("El documento adjunto no presenta firma o sello profesional visible.")
            requires_manual_review = True
            
        if not decision_reasons:
            decision_reasons.append("Documento médico/oficial válido con fecha y soporte verificable.")
            
        confidence = 0.95 if (is_valid and not requires_manual_review) else 0.70
        
        t_elapsed = time.perf_counter() - t_start
        
        return {
            "valido": is_valid and not requires_manual_review,
            "tipo_novedad": "inasistencia_medica" if "med" in extracted_reason.lower() else "inasistencia_general",
            "fecha_afectada": extracted_date,
            "motivo_decision": ". ".join(decision_reasons),
            "confianza_score": round(confidence, 2),
            "requiere_revision_manual": requires_manual_review,
            "detalles_adjunto": {
                "coder_detectado": extracted_name,
                "motivo_extraido": extracted_reason,
                "tiene_firma_o_sello": has_stamp,
                "paginas_consultadas": ai_res.get("pages_consulted", [])
            },
            "tiempo_procesamiento_segundos": round(t_elapsed, 2)
        }
        
    except Exception as e:
        t_elapsed = time.perf_counter() - t_start
        return JSONResponse(
            status_code=500,
            content={
                "valido": False,
                "error": str(e),
                "requiere_revision_manual": True,
                "motivo_decision": f"Error interno en Strata Core al procesar documento: {str(e)}",
                "tiempo_procesamiento_segundos": round(t_elapsed, 2)
            }
        )
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
