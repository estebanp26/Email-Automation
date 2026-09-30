"""
Servicio Generador y Exportador de Reportes de Ausentismo (DB-EXT-01).

Genera reportes de inasistencias y justificaciones en formatos CSV y Excel
para el Comité Semanal de HSE y Permanencia conforme a los lineamientos
de Riwi Barranquilla.

Criterios de Aceptación:
- Generación 100% en memoria (Streaming / Buffer io.StringIO / io.BytesIO),
  sin generar archivos temporales huérfanos en disco.
- Formato estructurado con las 9 columnas mandatorias:
  1. Cédula
  2. Nombre Coder
  3. Ruta Formativa
  4. Tipo de Novedad
  5. Fecha Inicio
  6. Fecha Fin
  7. Días Ausente
  8. Estado HSE
  9. Número de Radicado
- Integración dual: Conexión nativa a PostgreSQL / vista v_hse_weekly_summary
  con fallback resiliente al catálogo maestro y orquestador en memoria.
"""

import csv
import io
from datetime import datetime, timezone
from typing import Any, Dict, Generator, List, Optional

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False

try:
    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False

from ..config import settings
from .coder_resolver import coder_resolver
from .orchestrator import orchestrator

# Encabezados oficiales requeridos por Comité HSE
OFFICIAL_REPORT_HEADERS: List[str] = [
    "Cédula",
    "Nombre Coder",
    "Ruta Formativa",
    "Tipo de Novedad",
    "Fecha Inicio",
    "Fecha Fin",
    "Días Ausente",
    "Estado HSE",
    "Número de Radicado"
]


class HSEReportService:
    """Servicio de generación y exportación de reportes analíticos HSE."""

    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or settings.DATABASE_URL

    def _get_db_connection(self):
        """Intenta abrir conexión a PostgreSQL si psycopg2 está disponible."""
        if not HAS_PSYCOPG2 or not self.db_url:
            return None
        try:
            conn = psycopg2.connect(self.db_url, connect_timeout=3)
            return conn
        except Exception:
            return None

    def get_consolidated_report_data(
        self,
        status_filter: Optional[str] = None,
        route_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Consulta las justificaciones e inasistencias consolidadas.
        Intenta obtenerlas directamente de PostgreSQL; si la BD está offline,
        obtiene los registros del catálogo maestro y orquestador en memoria.
        """
        conn = self._get_db_connection()
        if conn:
            try:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    query = """
                        SELECT 
                            COALESCE(c.cedula, 'Sin Cédula')                                        AS cedula,
                            COALESCE(c.full_name, j.sender_name, 'Coder No Identificado')           AS nombre_coder,
                            COALESCE(c.route, 'Sin Ruta')                                           AS ruta_formativa,
                            COALESCE(j.excuse_type, 'no_identificado')                              AS tipo_novedad,
                            TO_CHAR(j.start_date, 'YYYY-MM-DD')                                    AS fecha_inicio,
                            TO_CHAR(j.end_date, 'YYYY-MM-DD')                                      AS fecha_fin,
                            (j.end_date - j.start_date + 1)::INTEGER                                AS dias_ausente,
                            COALESCE(j.hse_decision, j.validation_status, 'REVISION_MANUAL')        AS estado_hse,
                            j.id                                                                    AS numero_radicado
                        FROM public.justifications j
                        LEFT JOIN public.coders c ON j.coder_id = c.id
                        WHERE 1=1
                    """
                    params: List[Any] = []
                    if status_filter:
                        query += " AND (UPPER(j.validation_status) = UPPER(%s) OR UPPER(j.hse_decision) = UPPER(%s))"
                        params.extend([status_filter, status_filter])
                    if route_filter:
                        query += " AND LOWER(COALESCE(c.route, '')) LIKE LOWER(%s)"
                        params.append(f"%{route_filter}%")

                    query += " ORDER BY j.created_at DESC"
                    cur.execute(query, params)
                    rows = cur.fetchall()
                    if rows:
                        return [dict(row) for row in rows]
            except Exception:
                pass
            finally:
                conn.close()

        # Fallback resiliente: obtener registros desde orquestador y resolver con catálogo
        records = orchestrator.list_records(status=status_filter, clan=route_filter)
        data: List[Dict[str, Any]] = []

        for r in records:
            # Buscar datos enriquecidos del coder si están disponibles
            coder = None
            if r.coder_cedula:
                coder = coder_resolver._coders_by_cedula.get(r.coder_cedula.strip())
            if not coder and r.sender_email:
                coder = coder_resolver._coders_by_email.get(r.sender_email.strip().lower())

            cedula = coder.cedula if coder else (r.coder_cedula or "Sin Cédula")
            nombre = coder.full_name if coder else (r.coder_full_name or r.sender_name or "Coder No Identificado")
            ruta = coder.route if coder else (r.coder_route or "Sin Ruta")

            data.append({
                "cedula": str(cedula),
                "nombre_coder": str(nombre),
                "ruta_formativa": str(ruta),
                "tipo_novedad": str(r.excuse_type or "no_identificado"),
                "fecha_inicio": str(r.start_date),
                "fecha_fin": str(r.end_date),
                "dias_ausente": int(r.days_count if r.days_count is not None else 1),
                "estado_hse": str(r.status or "REVISION_MANUAL"),
                "numero_radicado": str(r.id)
            })

        return data

    def generate_csv_buffer(
        self,
        status_filter: Optional[str] = None,
        route_filter: Optional[str] = None,
        data: Optional[List[Dict[str, Any]]] = None
    ) -> io.BytesIO:
        """
        Genera el archivo CSV en un buffer en memoria (io.BytesIO)
        con codificación UTF-8 y BOM (\ufeff) para compatibilidad con Excel.
        """
        if data is None:
            data = self.get_consolidated_report_data(status_filter=status_filter, route_filter=route_filter)

        string_buffer = io.StringIO()
        # Escribir BOM de UTF-8 para apertura correcta con tildes en Excel de Windows
        string_buffer.write("\ufeff")

        writer = csv.writer(string_buffer, delimiter=",", lineterminator="\r\n", quoting=csv.QUOTE_MINIMAL)
        # 1. Escribir fila de encabezados oficiales
        writer.writerow(OFFICIAL_REPORT_HEADERS)

        # 2. Escribir filas de datos
        for row in data:
            writer.writerow([
                row.get("cedula", ""),
                row.get("nombre_coder", ""),
                row.get("ruta_formativa", ""),
                row.get("tipo_novedad", ""),
                row.get("fecha_inicio", ""),
                row.get("fecha_fin", ""),
                row.get("dias_ausente", 1),
                row.get("estado_hse", ""),
                row.get("numero_radicado", "")
            ])

        bytes_buffer = io.BytesIO(string_buffer.getvalue().encode("utf-8"))
        bytes_buffer.seek(0)
        return bytes_buffer

    def stream_csv(
        self,
        status_filter: Optional[str] = None,
        route_filter: Optional[str] = None
    ) -> Generator[bytes, None, None]:
        """
        Generador de streaming para respuestas HTTP sin cargar todo el archivo
        en memoria si el volumen supera miles de filas.
        """
        data = self.get_consolidated_report_data(status_filter=status_filter, route_filter=route_filter)
        buf = io.StringIO()
        buf.write("\ufeff")
        writer = csv.writer(buf, delimiter=",", lineterminator="\r\n")
        writer.writerow(OFFICIAL_REPORT_HEADERS)
        yield buf.getvalue().encode("utf-8")

        for row in data:
            row_buf = io.StringIO()
            row_writer = csv.writer(row_buf, delimiter=",", lineterminator="\r\n")
            row_writer.writerow([
                row.get("cedula", ""),
                row.get("nombre_coder", ""),
                row.get("ruta_formativa", ""),
                row.get("tipo_novedad", ""),
                row.get("fecha_inicio", ""),
                row.get("fecha_fin", ""),
                row.get("dias_ausente", 1),
                row.get("estado_hse", ""),
                row.get("numero_radicado", "")
            ])
            yield row_buf.getvalue().encode("utf-8")

    def generate_excel_buffer(
        self,
        status_filter: Optional[str] = None,
        route_filter: Optional[str] = None,
        data: Optional[List[Dict[str, Any]]] = None
    ) -> io.BytesIO:
        """
        Genera un archivo Excel (.xlsx) estilizado en un buffer en memoria (io.BytesIO).
        """
        if not HAS_OPENPYXL:
            # Fallback a CSV buffer si openpyxl no está instalado
            return self.generate_csv_buffer(status_filter=status_filter, route_filter=route_filter, data=data)

        if data is None:
            data = self.get_consolidated_report_data(status_filter=status_filter, route_filter=route_filter)

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Reporte Ausentismo HSE"

        # Estilos corporativos Riwi
        header_fill = PatternFill(start_color="5B3FF5", end_color="5B3FF5", fill_type="solid")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
        thin_border = Border(
            left=Side(style="thin", color="E0E0E0"),
            right=Side(style="thin", color="E0E0E0"),
            top=Side(style="thin", color="E0E0E0"),
            bottom=Side(style="thin", color="E0E0E0")
        )

        # Fila de encabezado
        ws.append(OFFICIAL_REPORT_HEADERS)
        for col_idx in range(1, len(OFFICIAL_REPORT_HEADERS) + 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = header_align

        # Filas de datos
        row_font = Font(name="Calibri", size=10)
        center_align = Alignment(horizontal="center", vertical="center")
        left_align = Alignment(horizontal="left", vertical="center")

        for r_idx, row in enumerate(data, start=2):
            values = [
                row.get("cedula", ""),
                row.get("nombre_coder", ""),
                row.get("ruta_formativa", ""),
                row.get("tipo_novedad", ""),
                row.get("fecha_inicio", ""),
                row.get("fecha_fin", ""),
                int(row.get("dias_ausente", 1)),
                row.get("estado_hse", ""),
                row.get("numero_radicado", "")
            ]
            ws.append(values)
            for c_idx in range(1, len(values) + 1):
                cell = ws.cell(row=r_idx, column=c_idx)
                cell.font = row_font
                cell.border = thin_border
                # Centrar cédula, fechas, días y estado
                if c_idx in (1, 5, 6, 7, 8):
                    cell.alignment = center_align
                else:
                    cell.alignment = left_align

        # Autoajuste de ancho de columnas
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                val_str = str(cell.value or "")
                if len(val_str) > max_len:
                    max_len = len(val_str)
            ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

        excel_buffer = io.BytesIO()
        wb.save(excel_buffer)
        excel_buffer.seek(0)
        return excel_buffer

    def get_weekly_summary_data(self) -> List[Dict[str, Any]]:
        """
        Consulta la vista analítica v_hse_weekly_summary.
        Si la base de datos no está disponible, calcula el consolidado
        semanal directamente a partir de los registros en memoria.
        """
        conn = self._get_db_connection()
        if conn:
            try:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT 
                            route,
                            ruta_formativa,
                            TO_CHAR(week_start, 'YYYY-MM-DD') AS week_start,
                            week_number,
                            year,
                            total_requests,
                            total_approved,
                            total_disapproved,
                            total_pending,
                            total_absence_days,
                            unique_coders_count
                        FROM public.v_hse_weekly_summary
                        ORDER BY year DESC, week_number DESC, route ASC
                    """)
                    rows = cur.fetchall()
                    if rows:
                        return [dict(r) for r in rows]
            except Exception:
                pass
            finally:
                conn.close()

        # Fallback analítico en memoria
        records = orchestrator.list_records()
        summary_map: Dict[str, Dict[str, Any]] = {}

        for r in records:
            route = r.coder_route or "Sin Ruta Asignada"
            try:
                dt = datetime.strptime(r.start_date, "%Y-%m-%d")
            except Exception:
                dt = datetime.now(timezone.utc)

            year, week_num, _ = dt.isocalendar()
            key = f"{route}_{year}_{week_num}"

            if key not in summary_map:
                summary_map[key] = {
                    "route": route,
                    "ruta_formativa": route,
                    "week_start": dt.strftime("%Y-%m-%d"),
                    "week_number": week_num,
                    "year": year,
                    "total_requests": 0,
                    "total_approved": 0,
                    "total_disapproved": 0,
                    "total_pending": 0,
                    "total_absence_days": 0,
                    "unique_coders": set()
                }

            item = summary_map[key]
            item["total_requests"] += 1
            if r.status == "APPROVED":
                item["total_approved"] += 1
            elif r.status == "DISAPPROVED":
                item["total_disapproved"] += 1
            else:
                item["total_pending"] += 1

            item["total_absence_days"] += (r.days_count if r.days_count is not None else 1)
            item["unique_coders"].add(r.coder_cedula or r.sender_email)

        result: List[Dict[str, Any]] = []
        for v in summary_map.values():
            result.append({
                "route": v["route"],
                "ruta_formativa": v["ruta_formativa"],
                "week_start": v["week_start"],
                "week_number": v["week_number"],
                "year": v["year"],
                "total_requests": v["total_requests"],
                "total_approved": v["total_approved"],
                "total_disapproved": v["total_disapproved"],
                "total_pending": v["total_pending"],
                "total_absence_days": v["total_absence_days"],
                "unique_coders_count": len(v["unique_coders"])
            })

        return sorted(result, key=lambda x: (x["year"], x["week_number"], x["route"]), reverse=True)


report_service = HSEReportService()
