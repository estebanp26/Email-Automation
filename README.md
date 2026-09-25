# Email-Automation (HSE Attendance Justification System con Strata Core)

Sistema automatizado de ingesta, filtración, análisis y resolución de justificaciones de inasistencia/tardanza para el equipo de HSE (Habilidades para la Vida), impulsado por el motor local **Strata Core**.

## 🚀 Arquitectura del Proyecto (Monorepo)

```
Email-Automation/
├── n8n/                # Workflows modulares de orquestación (Squad: Esteban, Jesus, Luis)
├── frontend/           # Dashboard para la Team Leader HSE (Squad: Kevin, Camilo)
├── connection/         # Webhooks y adaptadores Outlook/Gmail (Squad: Samuel)
├── strata-core/        # Motor universal de extracción y evidencia (Squad: Andres, Sebastian)
├── database/           # Schemas PostgreSQL / Supabase y Seeds (Squad: Eliam, Sergio)
├── docs/               # Contratos de API, guías de arquitectura y roadmap
└── .env.example        # Variables de entorno unificadas
```

## 👥 Organización de Squads & Responsables

| Squad | Integrantes | Foco Principal | Rama de Trabajo |
| :--- | :--- | :--- | :--- |
| **n8n Core** | **Esteban (Leader)**, Jesus, Luis | Orquestación, encolamiento y despacho de correos | `feature/n8n-core` |
| **Frontend** | **Kevin**, Camilo | Dashboard Next.js con visor de evidencias espaciales | `feature/frontend-dashboard` |
| **Conexión** | **Samuel** | Webhooks Outlook (Graph API) & Gmail (PubSub) | `feature/email-connections` |
| **Strata Core**| **Andres**, Sebastian | Motor universal de extracción local con Qwen 2.5 y Tesseract | `feature/ai-engine` |
| **Database** | **Eliam**, Sergio | Supabase PostgreSQL, Storage S3 y reglas dinámicas | `feature/db-supabase` |

## 🛠️ Regla de Oro: Config-Driven Architecture
Ninguna regla de negocio o plantilla de correo está quemada en código. Todo se lee dinámicamente de la base de datos para permitir ajustes el lunes sin tocar producción.
