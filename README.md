# Email-Automation (HSE Attendance Justification System)

Sistema automatizado de ingesta, filtración, análisis multimodal con IA y resolución de justificaciones de inasistencia/tardanza para el equipo de HSE (Habilidades para la Vida).

## 🚀 Arquitectura del Proyecto (Monorepo)

```
Email-Automation/
├── n8n/                # Workflows modulares de orquestación (Squad: Esteban, Jesus, Luis)
├── frontend/           # Dashboard para la Team Leader HSE (Squad: Kevin, Camilo)
├── connection/         # Webhooks y adaptadores Outlook/Gmail (Squad: Samuel)
├── ai-engine/          # Prompts, schemas y validación multimodal (Squad: Andres, Sebastian)
├── database/           # Schemas PostgreSQL / Supabase y Seeds (Squad: Eliam, Sergio)
├── docs/               # Contratos de API, guías de arquitectura y roadmap
└── .env.example        # Variables de entorno unificadas
```

## 👥 Organización de Squads & Responsables

| Squad | Integrantes | Foco Principal | Rama de Trabajo |
| :--- | :--- | :--- | :--- |
| **n8n Core** | **Esteban (Leader)**, Jesus, Luis | Orquestación, lógica de negocio y subflujos | `feature/n8n-core` |
| **Frontend** | **Kevin**, Camilo | Dashboard Next.js + Tailwind (Split-view & 1-click actions) | `feature/frontend-dashboard` |
| **Conexión** | **Samuel** | Webhooks Outlook (Graph API) & Gmail (PubSub) | `feature/email-connections` |
| **AI Engine** | **Andres**, Sebastian | Prompt Multimodal Gemini Flash, OCR y JSON Schemas | `feature/ai-engine` |
| **Database** | **Eliam**, Sergio | Supabase PostgreSQL, Storage S3 y reglas dinámicas | `feature/db-supabase` |

## 🛠️ Regla de Oro: Config-Driven Architecture
Ninguna regla de negocio o plantilla de correo está quemada en código. Todo se lee dinámicamente de la base de datos para permitir ajustes el lunes sin tocar producción.
