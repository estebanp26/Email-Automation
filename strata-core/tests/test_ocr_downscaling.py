#!/usr/bin/env python3
"""
test_ocr_downscaling.py
Prueba unitaria de Sub-tarea 1: Downscaling inteligente y preprocesamiento OCR.
Genera una imagen sintética de alta resolución (4000x3000 px, 12 MP)
con texto médico, la procesa con ocr_engine, y valida tiempo y precisión.
"""

import sys
import os
import time
import io

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from PIL import Image, ImageDraw, ImageFont
from engine.ocr_engine import preprocess_image_antitodo, ocr_single_image_worker

def test_downscale_and_ocr():
    print("=" * 70)
    print("🧪 TEST SUB-TAREA 1: DOWNSCALING Y OCR EN IMAGEN DE 12 MP (4000x3000)")
    print("=" * 70)

    # 1. Crear imagen sintética gigante (4000 x 3000)
    w, h = 4000, 3000
    print(f"[*] Creando imagen sintética de prueba: {w}x{h} px...")
    img = Image.new("RGB", (w, h), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Dibujar texto médico legible con tamaño proporcional a 4000x3000
    try:
        font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 72)
        font_regular = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 54)
    except Exception:
        font = ImageFont.load_default()
        font_regular = font

    draw.text((300, 400), "CERTIFICADO DE INCAPACIDAD MEDICA", fill=(0, 0, 0), font=font)
    draw.text((300, 600), "EPS SANITAS S.A. - REGISTRO MEDICO RM-99412", fill=(0, 0, 0), font=font_regular)
    draw.text((300, 800), "DIAGNOSTICO: INFECCION RESPIRATORIA AGUDA", fill=(0, 0, 0), font=font_regular)
    draw.text((300, 1000), "DIAS DE INCAPACIDAD: 3 DIAS", fill=(0, 0, 0), font=font_regular)
    draw.text((300, 1200), "DOCTOR: DR. SEBASTIAN ROPAIN - MEDICO GENERAL", fill=(0, 0, 0), font=font_regular)

    # 2. Probar preprocesamiento y downscale
    t0 = time.perf_counter()
    processed, sx, sy = preprocess_image_antitodo(img)
    t_preproc = time.perf_counter() - t0

    pw, ph = processed.size
    print(f"[*] Preprocesamiento completado en {t_preproc*1000:.1f} ms")
    print(f" • Dimensiones originales: {w}x{h}")
    print(f" • Dimensiones procesadas: {pw}x{ph} (Reducción: {(1 - (pw*ph)/(w*h))*100:.1f}%)")
    print(f" • Factor escala: sx={sx:.4f}, sy={sy:.4f}")

    assert pw <= 1600, f"Error: ancho procesado {pw} excede límite de 1600px"
    assert ph <= 1600, f"Error: alto procesado {ph} excede límite de 1600px"

    # 3. Probar OCR completo sobre la imagen
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG', quality=85)
    raw_bytes = img_byte_arr.getvalue()

    t1 = time.perf_counter()
    res = ocr_single_image_worker(raw_bytes, "test_12mp")
    t_ocr = time.perf_counter() - t1

    text_extracted = res.get("text", "")
    print(f"\n[*] OCR completado en {t_ocr:.2f} segundos")
    print(f" • Palabras detectadas: {len(res.get('boxes', []))}")
    print(f" • Primeros 150 caracteres extraídos:\n   {text_extracted[:150]}...")

    # Verificaciones de calidad
    assert "SANITAS" in text_extracted or "INCAPACIDAD" in text_extracted, "Fallo al detectar texto clave"
    assert t_ocr < 3.0, f"OCR demasiado lento: {t_ocr:.2f}s (esperado < 3.0s para 12 MP)"

    print("\n✅ SUB-TAREA 1 VALIDADA CON ÉXITO: Downscaling óptimo y OCR veloz.")
    print("=" * 70)

if __name__ == "__main__":
    test_downscale_and_ocr()
