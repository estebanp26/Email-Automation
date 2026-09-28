# 📊 Reporte Oficial de Evaluación: Strata Core HSE Evaluator
**Squad 2 — AI Engine** | **Fecha:** `2026-09-28 07:17:49` | **Modelo Evaluado:** `qwen2.5:1.5b`
**Responsables:** Sebastián (Test Runner & Schema) & Andrés (Prompt & Dataset)

---

## 1. Resumen Ejecutivo (KPIs del Contrato y Desempeño)

| Métrica | Resultado | Meta / SLA | Estado |
| :--- | :---: | :---: | :---: |
| **Cumplimiento JSON Schema** | **100.0%** | 100% | ✅ APROBADO |
| **Exactitud Veredicto (Válido)** | **100.0%** | >= 85.0% | ✅ APROBADO |
| **F1-Score Veredicto** | **100.0%** | >= 80.0% | ✅ APROBADO |
| **Recall Veredicto (Sensibilidad)** | **100.0%** | >= 85.0% | ✅ APROBADO |
| **F1-Score Revisión Manual** | **100.0%** | >= 80.0% | ✅ APROBADO |
| **Precisión Tipo de Novedad** | **90.0%** | >= 75.0% | ✅ APROBADO |
| **Latencia Mediana (P50)** | **12.332s** | < 8.0s | ⏱️ MODERADO |
| **Latencia P95** | **16.703s** | < 15.0s | ⚠️ COLA |

---

## 2. Matrices de Confusión

### A. Veredicto de Validez (`valido = true` vs `valido = false`)

| Ground Truth \ Predicción | Predicho VÁLIDO (Positivo) | Predicho INVÁLIDO (Negativo) | Total |
| :--- | :---: | :---: | :---: |
| **Esperado VÁLIDO** | **TP = 4** | **FN = 0** | 4 |
| **Esperado INVÁLIDO** | **FP = 0** | **TN = 6** | 6 |
| **Total** | 4 | 6 | **10** |

- **Precision:** `100.0%` (De los que el modelo aprobó, cuántos eran realmente legítimos).
- **Recall:** `100.0%` (De todas las excusas válidas, cuántas logró rescatar el modelo).
- **F1-Score:** `100.0%` (Media armónica entre precisión y recall).

### B. Bandera de Auditoría (`requiere_revision_manual`)

| Ground Truth \ Predicción | Predicho AUDITAR | Predicho AUTOMÁTICO |
| :--- | :---: | :---: |
| **Esperado AUDITAR** | **TP = 6** | **FN = 0** |
| **Esperado AUTOMÁTICO** | **FP = 0** | **TN = 4** |

- **Accuracy Auditoría:** `100.0%` | **F1-Score:** `100.0%`

---

## 3. Distribución de Latencias de Inferencia

| Mínimo | P50 (Mediana) | P90 | P95 | Máximo | Promedio |
| :---: | :---: | :---: | :---: | :---: | :---: |
| `11.493s` | `12.332s` | `14.45s` | `16.703s` | `16.703s` | `13.031s` |

---

## 4. Detalle Caso por Caso (Dataset de 10 Muestras)

| ID | Título del Caso | Veredicto Pred (Exp) | Novedad Pred (Exp) | Manual Rev | Latencia | Schema |
| :-: | :--- | :---: | :---: | :---: | :---: | :---: |
| 1 | Incapacidad médica EPS Sanitas válida con sello y fecha actual | 🎯 ✅ Válido (✅ Válido) | 🎯 `inasistencia_medica` (`inasistencia_medica`) | 🟢 No (🟢 No) | 12.85s | ✅ OK |
| 2 | Escaneo de Incapacidad SURA EPS con sello profesional | 🎯 ✅ Válido (✅ Válido) | 🎯 `inasistencia_medica` (`inasistencia_medica`) | 🟢 No (🟢 No) | 16.703s | ✅ OK |
| 3 | Incapacidad médica extemporánea (fecha vencida hace 15 días) | 🎯 ❌ Inválido (❌ Inválido) | 🎯 `inasistencia_medica` (`inasistencia_medica`) | 🚩 Sí (🚩 Sí) | 14.45s | ✅ OK |
| 4 | Constancia médica informal sin firma ni sello profesional | 🎯 ❌ Inválido (❌ Inválido) | 🎯 `inasistencia_medica` (`inasistencia_medica`) | 🚩 Sí (🚩 Sí) | 12.332s | ✅ OK |
| 5 | Calamidad doméstica en texto plano (sin adjunto) | 🎯 ❌ Inválido (❌ Inválido) | 🎯 `calamidad` (`calamidad`) | 🚩 Sí (🚩 Sí) | 12.26s | ✅ OK |
| 6 | Reporte de falla técnica de proveedor de internet | 🎯 ✅ Válido (✅ Válido) | 🎯 `falla_tecnica` (`falla_tecnica`) | 🟢 No (🟢 No) | 12.863s | ✅ OK |
| 7 | Fórmula médica de farmacia (no es incapacidad) | 🎯 ❌ Inválido (❌ Inválido) | 🎯 `inasistencia_medica` (`inasistencia_medica`) | 🚩 Sí (🚩 Sí) | 12.317s | ✅ OK |
| 8 | Salida temprana con cita odontológica programada | 🎯 ✅ Válido (✅ Válido) | 🎯 `salida_temprana` (`salida_temprana`) | 🟢 No (🟢 No) | 12.14s | ✅ OK |
| 9 | Fotografía totalmente borrosa e ilegible | 🎯 ❌ Inválido (❌ Inválido) | ⚠️ `inasistencia_medica` (`no_identificado`) | 🚩 Sí (🚩 Sí) | 12.906s | ✅ OK |
| 10 | Correo de Spam / Asunto no relacionado con asistencia | 🎯 ❌ Inválido (❌ Inválido) | 🎯 `no_identificado` (`no_identificado`) | 🚩 Sí (🚩 Sí) | 11.493s | ✅ OK |

---

## 5. cURL de Integración para n8n (Squad 1 - Jesús / Esteban / Luis)

### Caso A: Correo CON archivo adjunto (multipart/form-data)
```bash
curl -X POST "http://localhost:8001/api/evaluate-excuse" \
  -F "file=@/tmp/incapacidad_estudiante.pdf" \
  -F "email_subject=Justificante médico - Juan Pérez" \
  -F "email_body=Buenos días, adjunto certificado de EPS Sanitas." \
  -F "model=qwen2.5:1.5b"
```

### Caso B: Correo SIN archivo adjunto (application/json)
```bash
curl -X POST "http://localhost:8001/api/evaluate-excuse" \
  -H "Content-Type: application/json" \
  -d '{
    "email_subject": "Inasistencia por calamidad doméstica",
    "email_body": "Equipo HSE, hoy no podré asistir debido a un evento de fuerza mayor.",
    "model": "qwen2.5:1.5b"
  }'
```

---
*(Reporte generado automáticamente por `strata-core/test_squad2_evaluator.py`)*