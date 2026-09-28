# 🔌 Guía de Integración y Nodo HTTP Request para n8n
**De:** Sebastián (Squad 2 — Strata Core)  
**Para:** Jesús & Esteban (Squad 1 — n8n Core)  
**Fecha:** 2026-09-26  
**Endpoint:** `POST http://localhost:8001/api/evaluate-excuse`  

---

## 📌 Estado de la Integración

Hola Jesús, Strata Core ya está listo para recibir las peticiones de tu flujo (`workflows/02_evaluacion_ai.json`). 

Para facilitarte el trabajo, el microservicio soporta **ambas modalidades**:
1. **Multipart/form-data:** Si n8n pasa el archivo binario directamente desde el nodo de correo.
2. **Application/json:** Si n8n pasa el archivo codificado en Base64 dentro del payload JSON.

> ⚠️ **IMPORTANTE (SLA y Timeout):**  
> En las pruebas de latencia del modelo local (`qwen2.5:1.5b`), la mediana de procesamiento es de ~11 segundos y el percentil 95 en PDFs densos llega a ~28 segundos.  
> **Debes configurar en las opciones del nodo HTTP Request un timeout de al menos `60000` ms (60 segundos)** para evitar que n8n aborte la ejecución prematuramente.

---

## 🧩 Opción 1: Nodo n8n para `multipart/form-data` (Recomendado si manejas binario)

Puedes copiar este bloque JSON y pegarlo directamente con `Ctrl + V` en el canvas de n8n:

```json
{
  "nodes": [
    {
      "parameters": {
        "method": "POST",
        "url": "http://localhost:8001/api/evaluate-excuse",
        "sendBody": true,
        "contentType": "multipart-form-data",
        "bodyParameters": {
          "parameters": [
            {
              "parameterType": "formBinaryData",
              "name": "file",
              "inputDataFieldName": "data"
            },
            {
              "name": "email_subject",
              "value": "={{ $json.subject }}"
            },
            {
              "name": "email_body",
              "value": "={{ $json.body }}"
            },
            {
              "name": "model",
              "value": "qwen2.5:1.5b"
            }
          ]
        },
        "options": {
          "timeout": 60000
        }
      },
      "id": "strata-core-eval-multipart",
      "name": "Strata Core - Evaluar Justificante (Multipart)",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.2,
      "position": [480, 300]
    }
  ],
  "connections": {}
}
```

---

## 🧩 Opción 2: Nodo n8n para `application/json` (Con Base64)

Si en n8n ya convertiste el adjunto a base64 o si el correo no trae adjunto:

```json
{
  "nodes": [
    {
      "parameters": {
        "method": "POST",
        "url": "http://localhost:8001/api/evaluate-excuse",
        "sendHeaders": true,
        "headerParameters": {
          "parameters": [
            {
              "name": "Content-Type",
              "value": "application/json"
            }
          ]
        },
        "sendBody": true,
        "specifyBody": "json",
        "jsonBody": "={\n  \"email_subject\": {{ JSON.stringify($json.subject || '') }},\n  \"email_body\": {{ JSON.stringify($json.body || '') }},\n  \"model\": \"qwen2.5:1.5b\",\n  \"attachments\": [\n    {\n      \"filename\": {{ JSON.stringify($binary.data ? $binary.data.fileName : 'adjunto.pdf') }},\n      \"data_base64\": {{ JSON.stringify($binary.data ? $binary.data.data : '') }}\n    }\n  ]\n}",
        "options": {
          "timeout": 60000
        }
      },
      "id": "strata-core-eval-json",
      "name": "Strata Core - Evaluar Justificante (JSON)",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.2,
      "position": [480, 300]
    }
  ],
  "connections": {}
}
```

---

## 📤 Contrato de Respuesta Garantizado (JSON Schema 100% Validado)

Strata Core siempre te devolverá este esquema de respuesta con HTTP 200:

```json
{
  "valido": true,
  "tipo_novedad": "inasistencia_medica",
  "fecha_afectada": "2026-09-25",
  "motivo_decision": "Incapacidad médica de EPS Sanitas emitida por médico tratante con sello y fecha dentro del periodo permitido.",
  "confianza_score": 0.95,
  "requiere_revision_manual": false,
  "detalles_adjunto": {
    "es_legible": true,
    "tiene_firma_o_sello": true,
    "institucion_emisora": "EPS Sanitas",
    "paginas_consultadas": 1
  },
  "tiempo_procesamiento_segundos": 10.65
}
```

### 🚦 Lógica para tu nodo `Switch` / `If` en n8n:
- **Camino Verde (Aprobado):** `$json.valido === true && $json.requiere_revision_manual === false`
- **Camino Amarillo (Revisión Humana / Dashboard):** `$json.requiere_revision_manual === true`
- **Camino Rojo (Rechazado):** `$json.valido === false && $json.requiere_revision_manual === false`
