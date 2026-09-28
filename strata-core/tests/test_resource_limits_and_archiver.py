#!/usr/bin/env python3
"""
test_resource_limits_and_archiver.py
Prueba unitaria de Sub-tarea 3:
1. Control de uso de RAM para servidores de 8 GB (límite de páginas en PDFs extensos).
2. Módulo de archivado y compactación de evidencias en ZIPs con integridad CRC32.
"""

import sys
import os
import tempfile
import pymupdf as fitz
import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from engine.pdf_reader import PDFEngineReader
from engine.archiver import EvidenceArchiver


def test_pdf_page_limits():
    print("\n" + "=" * 70)
    print("🧪 TEST SUB-TAREA 3.1: CONTROL DE RAM Y LÍMITE DE PÁGINAS (8 GB RAM)")
    print("=" * 70)

    # 1. Crear PDF sintético de 10 páginas
    doc = fitz.open()
    for i in range(1, 11):
        page = doc.new_page()
        page.insert_text((50, 100), f"Página {i} de informe médico extenso de 10 páginas.")
    
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        temp_pdf = f.name
    doc.save(temp_pdf)
    doc.close()

    try:
        reader = PDFEngineReader()
        
        # Procesar con límite de 3 páginas (default de producción)
        result = reader.process_pdf(temp_pdf, run_ocr_on_images=False, max_pages=3)
        
        assert result["total_pages"] == 10, "El total de páginas detectadas debe ser 10"
        assert result["pages_processed"] == 3, "Solo debe haber procesado las primeras 3 páginas"
        assert len(result["pages"]) == 3, "La estructura de páginas en memoria debe tener longitud 3"
        print(f"  [OK] PDF de {result['total_pages']} páginas limitado a {result['pages_processed']} en memoria.")
        print(f"  • Páginas en memoria: {[p['page'] for p in result['pages']]}")
    finally:
        if os.path.exists(temp_pdf):
            os.remove(temp_pdf)


def test_evidence_archiver_and_cleanup():
    print("\n" + "=" * 70)
    print("🧪 TEST SUB-TAREA 3.2: ARCHIVADO Y LIBERACIÓN DE DISCO EN FORMATO ZIP")
    print("=" * 70)

    # 1. Crear lote de 5 archivos temporales simulando justificantes antiguos
    temp_dir = tempfile.mkdtemp()
    sample_files = []
    original_contents = {}

    for i in range(1, 6):
        fname = f"justificante_antiguo_caso_{i:03d}.txt"
        fpath = os.path.join(temp_dir, fname)
        content = f"Contenido del justificante {i} con firma médica y EPS SURA."
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(content)
        sample_files.append(fpath)
        original_contents[fname] = content

    zip_dest = os.path.join(temp_dir, "archivo_evidencias_2026_09.zip")

    try:
        # 2. Archivar y solicitar borrado de fuentes
        archive_res = EvidenceArchiver.archive_files(
            files=sample_files,
            zip_output_path=zip_dest,
            delete_sources=True
        )

        assert archive_res["success"] is True, "El archivado debió ser exitoso"
        assert archive_res["archived_count"] == 5, "Debió archivar 5 archivos"
        assert archive_res["deleted_count"] == 5, "Debió eliminar las 5 fuentes para liberar disco"
        print(f"  [OK] 5 archivos archivados exitosamente en: {archive_res['zip_path']}")
        print(f"  • Bytes originales: {archive_res['original_bytes']} B | Comprimidos: {archive_res['compressed_bytes']} B")
        print(f"  • Ahorro de espacio: {archive_res['saved_bytes']} B ({archive_res['compression_ratio_pct']}%)")

        # 3. Verificar que los archivos sueltos ya no existen (disco liberado)
        for fpath in sample_files:
            assert not os.path.exists(fpath), f"El archivo original {fpath} debió ser eliminado"
        print("  [OK] Verificado: Todos los archivos fuente fueron eliminados del disco.")

        # 4. Verificar listado sin descomprimir
        listed = EvidenceArchiver.list_archived_files(zip_dest)
        assert len(listed) == 5, "El índice debe contener los 5 archivos"
        print(f"  [OK] Índice manifest.json leído correctamente con {len(listed)} registros.")

        # 5. Extraer un archivo bajo demanda y verificar integridad
        extract_dir = os.path.join(temp_dir, "recuperados")
        recovered_path = EvidenceArchiver.extract_file_from_archive(
            zip_path=zip_dest,
            filename_inside="justificante_antiguo_caso_003.txt",
            target_dir=extract_dir
        )
        assert recovered_path is not None and os.path.exists(recovered_path)
        with open(recovered_path, "r", encoding="utf-8") as f:
            recovered_content = f.read()
        assert recovered_content == original_contents["justificante_antiguo_caso_003.txt"]
        print("  [OK] Extracción bajo demanda validada: El contenido recuperado es 100% idéntico.")

    finally:
        # Limpieza
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

    print("\n✅ SUB-TAREA 3 VALIDADA AL 100%: Control de RAM (3 págs) y archivado ZIP operativo.")
    print("=" * 70)


if __name__ == "__main__":
    test_pdf_page_limits()
    test_evidence_archiver_and_cleanup()
