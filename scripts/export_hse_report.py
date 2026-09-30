#!/usr/bin/env python3
"""
scripts/export_hse_report.py
=============================================================================
GENERADOR Y EXPORTADOR DE REPORTES DE AUSENTISMO A CSV/EXCEL — TASK [DB-EXT-01]
=============================================================================
Exporta el reporte consolidado de inasistencias y justificaciones para el Comité
Semanal de HSE y Permanencia de Riwi Barranquilla.

Columnas Generadas:
1. Cédula
2. Nombre Coder
3. Ruta Formativa
4. Tipo de Novedad
5. Fecha Inicio
6. Fecha Fin
7. Días Ausente
8. Estado HSE
9. Número de Radicado

Uso:
    python scripts/export_hse_report.py --format csv --output reporte_hse_barranquilla.csv
    python scripts/export_hse_report.py --format excel --output reporte_hse_barranquilla.xlsx
    python scripts/export_hse_report.py --status APPROVED
    python scripts/export_hse_report.py --stdout
"""

import argparse
import os
import sys
from pathlib import Path

# Agregar raíz del proyecto al path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.services.report_service import HSEReportService, report_service


def main():
    parser = argparse.ArgumentParser(
        description="Generador y Exportador de Reportes de Ausentismo HSE (DB-EXT-01)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  %(prog)s --format csv --output reporte_hse_barranquilla.csv
  %(prog)s --format excel --output reporte_hse_barranquilla.xlsx
  %(prog)s --status REVISION_MANUAL --output pendientes.csv
  %(prog)s --route "Node.js Backend"
        """
    )

    parser.add_argument(
        "--format",
        choices=["csv", "excel", "xlsx"],
        default="csv",
        help="Formato del archivo exportado (csv o excel, por defecto: csv)"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Ruta del archivo de salida (por defecto: reporte_hse_barranquilla.csv/.xlsx)"
    )
    parser.add_argument(
        "--status", "-s",
        type=str,
        default=None,
        help="Filtrar por estado HSE (ej. APPROVED, DISAPPROVED, REVISION_MANUAL)"
    )
    parser.add_argument(
        "--route", "-r",
        type=str,
        default=None,
        help="Filtrar por Ruta Formativa (ej. 'Node.js Backend', 'Cloud')"
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Imprimir contenido CSV a la salida estándar (stdout)"
    )

    args = parser.parse_args()

    fmt = args.format.lower()
    default_filename = "reporte_hse_barranquilla.xlsx" if fmt in ("excel", "xlsx") else "reporte_hse_barranquilla.csv"
    output_path = args.output or default_filename

    # Obtener datos consolidados
    records = report_service.get_consolidated_report_data(
        status_filter=args.status,
        route_filter=args.route
    )

    if args.stdout:
        # Generar CSV en memoria y escribir a stdout
        csv_buffer = report_service.generate_csv_buffer(data=records)
        sys.stdout.buffer.write(csv_buffer.getvalue())
        return

    # Exportar a archivo
    out_file = Path(output_path)
    if fmt in ("excel", "xlsx"):
        excel_buffer = report_service.generate_excel_buffer(data=records)
        out_file.write_bytes(excel_buffer.getvalue())
        print(f"✅ Reporte Excel exportado exitosamente: {out_file.resolve()} ({len(records)} registros)")
    else:
        csv_buffer = report_service.generate_csv_buffer(data=records)
        out_file.write_bytes(csv_buffer.getvalue())
        print(f"✅ Reporte CSV exportado exitosamente: {out_file.resolve()} ({len(records)} registros)")


if __name__ == "__main__":
    main()
