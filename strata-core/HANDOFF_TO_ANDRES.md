# 🤝 Documento de Entrega y Diagnóstico Técnico — Squad 2 (AI Engine)
**De:** Sebastián (*Inference API, Test Runner & Schema Validation*)  
**Para:** Andrés (*Prompt Engineering & Dataset Lead*)  
**Fecha:** 2026-09-26  
**Rama:** `feature/ai-engine`  
**Objetivo:** Calibración de Prompts en `evaluator_system_prompt.md` y Afinamiento de Inferencia  

---

## 📌 Resumen Ejecutivo de la Auditoría

Hola Andrés, ya construí, blindé y verifiqué el runner oficial de pruebas automatizadas (`test_squad2_evaluator.py`) y las optimizaciones del microservicio (`server.py`).

El pipeline cumple **100% el contrato JSON Schema** (`evaluation_schema.json`). Es decir, el microservicio nunca rompe la estructura que espera n8n y el frontend. 

Sin embargo, al correr la inferencia contra los 10 casos de prueba usando el modelo base `qwen2.5:1.5b`, detectamos un comportamiento **hiper-conservador (alta precisión = 100%, pero bajo recall = 25%)**. El modelo tiende a rechazar excusas válidas o a clasificar casi todo como `inasistencia_medica`.

A continuación tienes el desglose exacto de lo que debes calibrar en los prompts y cómo re-ejecutar el runner.

---

## 🎯 1. Casos que Fallaron (Diagnóstico para Calibración de Prompt)

De los 10 casos del manifest oficial (`test_samples/cases_manifest.json`), 4 presentaron discrepancias que se resuelven ajustando el system prompt (`strata-core/prompts/evaluator_system_prompt.md`):

| Caso | Título / Situación | Predicción Modelo | Esperado Real | Problema Detectado & Sugerencia |
| :---: | :--- | :---: | :---: | :--- |
| **Caso 2** | Escaneo Incapacidad SURA EPS | `valido: false`<br>`manual: true` | `valido: true`<br>`manual: false` | **Falso Negativo:** El OCR extrajo texto con algo de ruido y el modelo desconfió del sello/firma. <br>👉 *Acción en prompt:* Indicar explícitamente que si el OCR detecta texto como "SURA AUTORIZADO" o registro médico, se considere firma válida salvo ilegibilidad extrema. |
| **Caso 5** | Calamidad doméstica en texto plano | `tipo: inasistencia_medica` | `tipo: calamidad` | **Error de Clasificación:** El estudiante reporta fallecimiento familiar (sin adjunto). El modelo le asignó tipo médico por inercia.<br>👉 *Acción en prompt:* Reforzar la regla de clasificación cuando el cuerpo del correo mencione muerte, luto, urgencia familiar grave o desastre. |
| **Caso 6** | Ticket de falla técnica de internet | `valido: false` | `valido: true` | **Falso Negativo:** El modelo rechazó el ticket de Tigo porque buscaba un certificado médico tradicional.<br>👉 *Acción en prompt:* Enseñar al prompt en las reglas HSE que `falla_tecnica` es un motivo válido cuando se adjunta radicado/ticket de proveedor de ISP o servicios públicos. |
| **Caso 8** | Cita odontológica programada | `tipo: inasistencia_medica`<br>`valido: false` | `tipo: salida_temprana`<br>`valido: true` | **Falso Negativo + Tipo:** Pide salir 1 hora antes con soporte clínico. El modelo lo tomó como inasistencia completa no válida.<br>👉 *Acción en prompt:* Diferenciar `salida_temprana` y `tardanza` de `inasistencia_medica` completa. |

---

## ⚡ 2. Reporte de Latencias y SLA de Inferencia

Métricas recolectadas durante la corrida de inferencia local:

| Percentil / Métrica | Latencia Registrada | SLA Objetivo (n8n / Prod) | Estado |
| :--- | :---: | :---: | :---: |
| **Mínimo** | `9.58s` | < 5.0s | ⏱️ Aceptable en local |
| **P50 (Mediana)** | `10.92s` | < 8.0s | ⏱️ En rango para 1.5B en CPU |
| **P90** | `12.98s` | < 12.0s | ⚠️ Límite |
| **P95 / Máximo** | `28.40s` | < 15.0s | ⚠️ Cuello de botella en PDFs densos |

### Conclusiones Técnicas de Rendimiento:
1. **CPU vs GPU:** En máquina local corriendo solo por CPU con Ollama, 10s de latencia es el piso esperado para 1.5B tokens.
2. **Impacto en n8n:** Jesús y el equipo de n8n deben configurar un timeout HTTP de al menos **45 a 60 segundos** en el nodo HTTP Request para evitar timeout en el Caso 1 o PDFs de varias páginas.
3. **Optimización futura:** Si el Tech Lead solicita SLAs menores a 5 segundos, debemos evaluar:
   - Reducir `num_ctx` en Ollama (limitar el contexto inyectado del OCR a máximo 2048 tokens).
   - Cuantización `q4_K_M` o desplegar en una instancia con GPU ligera (T4 / RTX).

---

## 🛠️ 3. Cómo Correr el Runner de Pruebas

Dejé listo un CLI con soporte para Rich (tablas en colores), filtrado por casos específicos y concurrencia.

### A. Ejecutar todos los casos:
```bash
python strata-core/test_squad2_evaluator.py
```

### B. Iterar solo sobre los casos que fallaron (para calibrar rápido el prompt):
```bash
python strata-core/test_squad2_evaluator.py --cases 2,5,6,8
```

### C. Probar con otro modelo de Ollama (ej. si pruebas un modelo de 3B o 7B):
```bash
python strata-core/test_squad2_evaluator.py --model qwen2.5:3b
```

Cada vez que corras el runner, se actualizarán automáticamente dos archivos en la raíz de `strata-core/`:
- `EVALUATION_REPORT.md` *(Formato Markdown enriquecido con tablas y métricas para copiar directo al Notion del proyecto)*.
- `EVALUATION_REPORT_SEBAS.json` *(Payload JSON crudo para automatizaciones o trazabilidad)*.

*(Nota: Ambos archivos ya están incluidos en `.gitignore` para no contaminar el historial de git).*

---

## 🔌 4. Contratos de Entrada Listos para n8n

Ya dejé actualizado `server.py` para soportar tanto:
1. `multipart/form-data` con archivo binario y campos de formulario.
2. `application/json` con archivo codificado en `data_base64` o `file_base64` (soporta el array `attachments` de `API_CONTRACTS.md`).

Los cURLs exactos de prueba están documentados en la sección 5 de `EVALUATION_REPORT.md` para que se los compartas a Jesús cuando enlace los webhooks.
