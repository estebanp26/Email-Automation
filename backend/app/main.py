from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .api.v1.emails import router as emails_router
from .api.v1.coders import router as coders_router
from .api.v1.policy import router as policy_router
from .api.v1.pipeline import router as pipeline_router
from .api.v1.notifications import router as notifications_router
from .api.v1.justifications import router as justifications_router
from .api.v1.stats import router as stats_router
from .api.v1.attendance import router as attendance_router
from .api.v1.reports import router as reports_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="""
    ## Riwi HSE Attendance & Justification Automation System API (Release 3.0)
    
    Servicios nativos de backend para ingesta, percepción, validación determinista y gestión
    de inasistencias de coders conforme a la Regulación de Asistencias y Permanencia de Riwi Barranquilla.
    """
)

# Configuración de Middlewares
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
from .core.middleware import RequestSizeLimitMiddleware
app.add_middleware(RequestSizeLimitMiddleware, max_upload_size_bytes=20 * 1024 * 1024)

# Montaje de Routers API v1
app.include_router(emails_router, prefix=settings.API_V1_PREFIX)
app.include_router(coders_router, prefix=settings.API_V1_PREFIX)
app.include_router(policy_router, prefix=settings.API_V1_PREFIX)
app.include_router(pipeline_router, prefix=settings.API_V1_PREFIX)
app.include_router(notifications_router, prefix=settings.API_V1_PREFIX)
app.include_router(justifications_router, prefix=settings.API_V1_PREFIX)
app.include_router(stats_router, prefix=settings.API_V1_PREFIX)
app.include_router(attendance_router, prefix=settings.API_V1_PREFIX)
app.include_router(reports_router, prefix=settings.API_V1_PREFIX)
app.include_router(reports_router, prefix="/api")


@app.get("/", tags=["Root"])
async def root():
    return {
        "system": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "active",
        "docs_url": "/docs",
        "api_v1": settings.API_V1_PREFIX
    }
