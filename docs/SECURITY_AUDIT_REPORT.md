# Reporte de Auditoría de Seguridad: Carga de Archivos y Sanitización (QA-01)

**Fecha:** 29 de Septiembre de 2026
**Responsable QA:** Arley / Sec Eng
**Estado Global:** 🔴 CRÍTICO - Vulnerabilidades Detectadas
**Endpoint Auditado:** `POST /api/v1/emails/ingest`

## Resumen Ejecutivo
Durante la auditoría de seguridad del mecanismo de recepción y procesamiento de evidencias adjuntas, se ejecutó una batería de pruebas orientada a vulnerabilidades de inyección de archivos. El endpoint falló en el 100% de los casos de prueba, devolviendo `Status 200 OK` y procesando payloads maliciosos, lo que incumple el criterio de aceptación principal del ticket [QA-01].

---

## Hallazgos y Pruebas de Concepto (PoC)

### 1. Falsificación de MIME Type (Content-Type Spoofing)
* **Descripción:** El sistema confía ciegamente en el nombre del archivo (extensión) y en el MIME type declarado en el payload JSON, sin verificar la firma real del archivo.
* **Vector de Ataque:** Se inyectó un archivo ejecutable (con cabeceras `MZ`) renombrado como `malware.pdf` y `application/pdf`.
* **Resultado:** ❌ Aceptado (Status 200).
* **Riesgo:** Ejecución de código remoto (RCE) si el archivo es almacenado y posteriormente accedido o interpretado por el sistema.

### 2. Path Traversal (Salto de Directorio)
* **Descripción:** Falta de sanitización en el parámetro `filename` del adjunto.
* **Vector de Ataque:** Se envió el nombre `../../../etc/passwd` junto con contenido válido.
* **Resultado:** ❌ Aceptado (Status 200).
* **Riesgo:** Sobrescritura de archivos críticos del sistema operativo local o del contenedor Docker al momento de guardar la evidencia.

### 3. Ausencia de Filtrado de Malware (EICAR Bypass)
* **Descripción:** El sistema no posee un control heurístico ni de firmas básicas para archivos maliciosos conocidos.
* **Vector de Ataque:** Se inyectó la firma estándar de prueba antivirus EICAR en Base64.
* **Resultado:** ❌ Aceptado (Status 200).
* **Riesgo:** Infección transversal de los repositorios de S3/Supabase y distribución de malware a la Team Leader HSE cuando descargue la evidencia desde el dashboard.

### 4. Denegación de Servicio por Exceso de Memoria (DoS)
* **Descripción:** El límite teórico definido (`MAX_ATTACHMENT_SIZE_BYTES`) no está siendo forzado en el endpoint de recepción.
* **Vector de Ataque:** Se envió un payload Base64 masivo (20MB+).
* **Resultado:** ❌ Aceptado (Status 200).
* **Riesgo:** Caída del servidor FastAPI por agotamiento de memoria (OOM) si un atacante lanza envíos concurrentes con adjuntos pesados.

---

## Recomendaciones de Remediación para el Equipo de Backend

Para corregir estas vulnerabilidades y dar el ticket por aprobado, el equipo debe implementar los siguientes controles en `backend/app/services/ingestion.py` y `backend/app/api/v1/emails.py`:

1. **Inspección de Magic Bytes (Strict MIME Validation):**
   Reemplazar la validación basada en `Path(filename).suffix` por inspección real de bytes. Se recomienda implementar la librería `python-magic` sobre los bytes decodificados antes de aceptarlos como evidencia válida.
2. **Sanitización Estricta de Rutas:**
   Utilizar utilidades como `secure_filename` (de `werkzeug.utils` o implementación propia en Python) para limpiar cualquier salto de directorio (`../`, `\`, `/`) del parámetro `filename`.
3. **Control de Tamaño a Nivel Middleware:**
   Bloquear los payloads excesivamente grandes antes de que lleguen al parser de JSON de FastAPI (y por ende a la memoria RAM). Configurar un límite de `Content-Length` en la ingesta.
4. **Respuesta HTTP Adecuada:**
   Cualquier adjunto que falle estas validaciones debe interrumpir la transacción o marcarse explícitamente, retornando obligatoriamente un código `400 Bad Request` o `422 Unprocessable Entity` en lugar de `200 OK`.