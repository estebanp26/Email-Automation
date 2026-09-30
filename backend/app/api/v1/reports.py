from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Query, Response, status
from fastapi.responses import StreamingResponse

from ...services.report_service import report_service

router = APIRouter(prefix="/reports", tags=["Reportes & Analíticas HSE (DB-EXT-01)"])


@router.get(
    "/export-csv",
    summary="Exportar Reporte Consolidado de Ausentismo a CSV (DB-EXT-01)",
    description="""
    Genera y descarga en tiempo real el Reporte Consolidado de Ausentismo en formato CSV
    con streaming en memoria (sin archivos temporales en disco) y codificación UTF-8 BOM.
    
    Campos exportados:
    Cédula, Nombre Coder, Ruta Formativa, Tipo de Novedad, Fecha Inicio, Fecha Fin,
    Días Ausente, Estado HSE, Número de Radicado.
    """,
    responses={
        200: {
            "content": {"text/csv": {}},
            "description": "Descarga de archivo CSV formateado para Comité HSE."
        }
    }
)
async def export_absenteeism_csv(
    status_filter: Optional[str] = Query(None, alias="status", description="Filtrar por estado HSE: APPROVED, DISAPPROVED, REVISION_MANUAL"),
    route_filter: Optional[str] = Query(None, alias="route", description="Filtrar por Ruta Formativa (ej. Node.js Backend, Cloud)")
):
    buffer = report_service.generate_csv_buffer(status_filter=status_filter, route_filter=route_filter)
    
    headers = {
        "Content-Disposition": "attachment; filename=reporte_hse_barranquilla.csv",
        "Content-Type": "text/csv; charset=utf-8",
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0"
    }

    return StreamingResponse(
        buffer,
        media_type="text/csv; charset=utf-8",
        headers=headers
    )


@router.get(
    "/export-excel",
    summary="Exportar Reporte Consolidado de Ausentismo a Excel .xlsx (DB-EXT-01)",
    description="""
    Genera y descarga el Reporte Consolidado de Ausentismo en formato Microsoft Excel (.xlsx)
    estilizado con colores institucionales Riwi y auto-ajuste de columnas directamente en memoria.
    """,
    responses={
        200: {
            "content": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {}},
            "description": "Descarga de archivo Excel (.xlsx) formateado."
        }
    }
)
async def export_absenteeism_excel(
    status_filter: Optional[str] = Query(None, alias="status", description="Filtrar por estado HSE"),
    route_filter: Optional[str] = Query(None, alias="route", description="Filtrar por Ruta Formativa")
):
    buffer = report_service.generate_excel_buffer(status_filter=status_filter, route_filter=route_filter)
    
    headers = {
        "Content-Disposition": "attachment; filename=reporte_hse_barranquilla.xlsx",
        "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0"
    }

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers
    )


@router.get(
    "/weekly-summary",
    response_model=List[Dict[str, Any]],
    summary="Resumen Analítico Semanal de Ausentismo por Ruta (v_hse_weekly_summary)",
    description="""
    Retorna métricas consolidadas agrupadas por Ruta Formativa y semana académica
    correspondientes a la vista PostgreSQL v_hse_weekly_summary.
    """
)
async def get_weekly_summary():
    return report_service.get_weekly_summary_data()
