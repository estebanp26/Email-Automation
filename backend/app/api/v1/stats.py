from fastapi import APIRouter, status

from ...schemas.coder_portal import DashboardGlobalStats
from ...services.portal_service import portal_service

router = APIRouter(prefix="/stats", tags=["Métricas & Dashboard (BE-07)"])


@router.get(
    "/dashboard",
    response_model=DashboardGlobalStats,
    status_code=status.HTTP_200_OK,
    summary="Métricas Globales del Dashboard HSE & Team Leader"
)
async def get_dashboard_metrics():
    """
    Retorna métricas consolidadas de solicitudes totales, aprobadas,
    rechazadas, pendientes, alertas de permanencia activas y casos sensibles.
    """
    return portal_service.get_dashboard_global_stats()
