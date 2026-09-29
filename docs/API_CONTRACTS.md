# Contratos de Datos & Interfaces

## 1. Ingesta Nativa Desacoplada: `POST /api/v1/inbound-email` (Samuel -> Strata Core Backend)
Reemplaza el webhook de n8n por un controlador FastAPI nativo con validación Pydantic, deduplicación e idempotencia.

### Request Body (`InboundEmailDTO`):
```json
{
  "source_provider": "OUTLOOK", // o "GMAIL"
  "message_id": "AAMkAGI2...",
  "conversation_id": "AAQkAGI...",
  "sender_email": "coder@riwi.io",
  "sender_name": "Laura Gómez",
  "email_subject": "Justificación inasistencia 25 Septiembre",
  "email_body": "Buenos días, adjunto comprobante médico de mi cita de hoy...",
  "received_at": "2026-09-25T14:10:00Z",
  "attachments": [
    {
      "filename": "incapacidad_eps.pdf",
      "mime_type": "application/pdf",
      "data_base64": "JVBERi0xLjQK..."
    }
  ]
}
```

### Response HTTP 202 Accepted (Nuevo evento encolado):
```json
{
  "status": "ACCEPTED",
  "message": "Event queued for identification and validation",
  "message_id": "AAMkAGI2...",
  "conversation_id": "AAQkAGI...",
  "transaction_id": "8e2a90d0-2150-4be2-bc4d-18237ebc9a2e",
  "state": "PENDING_IDENTIFICATION",
  "attachments_count": 1
}
```

### Response HTTP 200 OK (Idempotencia - Evento duplicado):
```json
{
  "status": "OK",
  "message": "Event already processed",
  "message_id": "AAMkAGI2..."
}
```

## 2. Payload de Salida de la IA (Andres & Sebastian -> n8n)
```json
{
  "valido": true,
  "tipo_novedad": "inasistencia_medica",
  "fecha_afectada": "2026-09-25",
  "motivo_decision": "Incapacidad médica oficial emitida por EPS Sanitas con firma y fecha concordante.",
  "confianza_score": 0.95,
  "requiere_revision_manual": false,
  "detalles_adjunto": {
    "es_legible": true,
    "tiene_firma_o_sello": true,
    "institucion_emisora": "EPS Sanitas"
  }
}
```

## 3. Webhook de Acción Manual desde el Dashboard (Kevin & Camilo -> n8n)
`POST /webhook/manual-action`
```json
{
  "justification_id": "b3e5b611-6b08-4e89-8d14-386fa9f4e412",
  "action": "APPROVE", // "REJECT" | "REQUEST_MORE_INFO"
  "tl_notes": "Aprobado por motivo de fuerza mayor comprobado.",
  "tl_user": "team_leader@institucion.com"
}
```
