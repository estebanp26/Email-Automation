# 🧠 Strata Core — Motor de Percepción & Evidencia On-Premise

**Squad Responsable:** Andres & Sebastian  
**Rama Git:** `feature/ai-engine`

---

## 🎯 ¿Qué es Strata Core?
**Strata Core** es el motor universal de procesamiento de datos desestructurados del sistema de automatización HSE. Procesa tanto texto plano como archivos adjuntos (PDFs digitales, escaneos ruidosos, fotos de celular en JPG/PNG) y extrae evidencia estructurada en JSON con cero alucinación y sin enviar datos a la nube.

---

## 🚀 Arquitectura Interna del Pipeline

```
[Entrada: Texto Plano / Foto / PDF]
      │
      ▼
1. Triaje C-Level (PyMuPDF) ──────► ¿Tiene texto digital? ──► Extrae en 5ms (Sin OCR)
      │
      ▼ (Si es imagen / escaneo)
2. Visión Adaptativa Anti-Todo ──► Contraste dinámico + Pase de sellos y firmas
      │
      ▼
3. Normalizador & Radar Léxico  ──► Diccionario FastVocabCleaner + Coordenadas espaciales
      │
      ▼
4. Smart Context Pruning        ──► Poda de contexto (< 600 tokens)
      │
      ▼
5. Inferencia Qwen 2.5 (Ollama) ──► JSON estructurado con Veredicto HSE (Aprobado/Rechazado)
```

---

## 🛠️ Cómo Iniciar el Servicio Localmente

```bash
cd strata-core
./run.sh
```
El servidor quedará escuchando en `http://localhost:8001`.

---

## 📡 Endpoints de la API (Consumidos por n8n y el Dashboard)

### 1. `GET /health`
Verifica que el servicio esté arriba y que Ollama tenga cargado `qwen2.5:1.5b`.

### 2. `POST /api/evaluate-excuse` *(Llamado por el Subflujo 2 de n8n)*
Recibe el correo y su adjunto, aplica los criterios de HSE y devuelve el veredicto para n8n:
* **Parámetros (Multipart Form):**
  * `file`: Archivo adjunto (PDF, JPG, PNG) [Opcional].
  * `email_body`: Cuerpo del correo en texto plano [Opcional].
  * `email_subject`: Asunto del correo [Opcional].
  * `rules_json`: Reglas dinámicas inyectadas desde Supabase `hse_system_config` [Opcional].

* **Respuesta JSON:**
```json
{
  "valido": true,
  "tipo_novedad": "inasistencia_medica",
  "fecha_afectada": "25/09/2026",
  "motivo_decision": "Documento médico/oficial válido con fecha y soporte verificable.",
  "confianza_score": 0.95,
  "requiere_revision_manual": false,
  "detalles_adjunto": {
    "coder_detectado": "Juan Pérez",
    "motivo_extraido": "Gastroenteritis aguda (CIE-10: A09)",
    "tiene_firma_o_sello": true,
    "paginas_consultadas": [1]
  },
  "tiempo_procesamiento_segundos": 8.42
}
```

### 3. `POST /api/search` *(Llamado por el Dashboard de Camilo)*
Búsqueda espacial que devuelve las coordenadas exactas `[x0, y0, x1, y1]` de cada coincidencia para resaltar las cajas en el visor visual.
