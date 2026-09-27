#!/usr/bin/env python3
"""
test_squad2_evaluator.py
=============================================================================
RUNNER OFICIAL DE EVALUACIÓN Y VALIDACIÓN DE CONTRATOS — SQUAD 2 (STRATA CORE)
=============================================================================
Autor: Sebastián (Squad 2: AI Engine / Inference & Validation)
Colaborador: Andrés (Dataset & Prompt Engineering)

Misión:
- Ejecuta los casos de prueba del dataset oficial (cases_manifest.json).
- Valida el contrato JSON contra evaluation_schema.json (100% compliance).
- Calcula métricas avanzadas de clasificación (Matriz de Confusión, Precisión, Recall, F1).
- Mide percentiles de latencia (P50, P90, P95, Min, Max).
- Imprime tablas visuales con Rich y exporta reporte profesional en Markdown y JSON.
=============================================================================
"""

import os
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import json
import time
import math
import asyncio
import argparse
from typing import List, Dict, Any, Optional

import jsonschema

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

import server

MANIFEST_PATH = os.path.join(BASE_DIR, "test_samples", "cases_manifest.json")
SCHEMA_PATH = os.path.join(BASE_DIR, "schemas", "evaluation_schema.json")
DEFAULT_OUTPUT_MD = os.path.join(BASE_DIR, "EVALUATION_REPORT.md")
DEFAULT_OUTPUT_JSON = os.path.join(BASE_DIR, "EVALUATION_REPORT_SEBAS.json")


class MockFastAPIUploadFile:
    """Simulador de archivo para invocar server.evaluate_excuse sin abrir sockets HTTP."""
    def __init__(self, file_path: str):
        self.filename = os.path.basename(file_path)
        self.file = open(file_path, "rb")

    def close(self):
        if not self.file.closed:
            self.file.close()


def calculate_percentiles(values: List[float], percentiles: List[int]) -> Dict[str, float]:
    """Calcula percentiles estadísticos ordenados."""
    if not values:
        return {f"P{p}": 0.0 for p in percentiles}
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    results = {}
    for p in percentiles:
        idx = int(math.ceil((p / 100.0) * n)) - 1
        idx = max(0, min(n - 1, idx))
        results[f"P{p}"] = round(sorted_vals[idx], 3)
    return results


def compute_binary_metrics(y_true: List[bool], y_pred: List[bool]) -> Dict[str, Any]:
    """Calcula matriz de confusión (TP, FP, TN, FN), Precision, Recall, F1 y Accuracy."""
    tp = sum(1 for yt, yp in zip(y_true, y_pred) if yt is True and yp is True)
    fp = sum(1 for yt, yp in zip(y_true, y_pred) if yt is False and yp is True)
    tn = sum(1 for yt, yp in zip(y_true, y_pred) if yt is False and yp is False)
    fn = sum(1 for yt, yp in zip(y_true, y_pred) if yt is True and yp is False)
    total = len(y_true)

    accuracy = (tp + tn) / total if total > 0 else 0.0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "total": total,
        "accuracy": round(accuracy * 100, 2),
        "precision": round(precision * 100, 2),
        "recall": round(recall * 100, 2),
        "f1": round(f1 * 100, 2)
    }


async def evaluate_single_case(
    case: Dict[str, Any],
    schema: Dict[str, Any],
    rules: Dict[str, Any],
    model: str,
    semaphore: asyncio.Semaphore
) -> Dict[str, Any]:
    """Evalúa un caso contra Strata Core garantizando validación de contrato y captura de latencia."""
    async with semaphore:
        cid = case["case_id"]
        title = case["title"]
        fname = case.get("file")
        email_sub = case.get("email_subject")
        email_body = case.get("email_body")
        samples_dir = os.path.join(BASE_DIR, "test_samples")

        upload_obj = None
        if fname:
            fpath = os.path.join(samples_dir, fname)
            if os.path.exists(fpath):
                upload_obj = MockFastAPIUploadFile(fpath)

        t0 = time.perf_counter()
        response_dict = {}
        try:
            response_dict = await server.evaluate_excuse(
                file=upload_obj,
                email_body=email_body,
                email_subject=email_sub,
                rules_json=rules,
                model=model
            )
            # Si server devolvió JSONResponse en caso de error HTTP
            if hasattr(response_dict, "body"):
                response_dict = json.loads(response_dict.body.decode("utf-8"))
        except Exception as exc:
            response_dict = {
                "valido": False,
                "tipo_novedad": "no_identificado",
                "fecha_afectada": "No identificada",
                "motivo_decision": f"Error de ejecución: {str(exc)}",
                "confianza_score": 0.0,
                "requiere_revision_manual": True,
                "error": str(exc)
            }
        finally:
            if upload_obj:
                upload_obj.close()

        elapsed = time.perf_counter() - t0

        # Validación estricta del JSON Schema
        is_valid_schema = False
        schema_err = None
        try:
            jsonschema.validate(instance=response_dict, schema=schema)
            is_valid_schema = True
        except jsonschema.ValidationError as ve:
            schema_err = ve.message

        return {
            "case_id": cid,
            "title": title,
            "latency_sec": round(elapsed, 3),
            "schema_compliant": is_valid_schema,
            "schema_error": schema_err,
            "prediction": response_dict,
            "ground_truth": {
                "valido": case.get("expected_valido"),
                "tipo": case.get("expected_tipo"),
                "manual_review": case.get("expected_manual_review")
            }
        }


def generate_markdown_report(
    results: List[Dict[str, Any]],
    model_name: str,
    valido_metrics: Dict[str, Any],
    review_metrics: Dict[str, Any],
    latency_stats: Dict[str, float],
    schema_rate: float,
    type_accuracy: float
) -> str:
    """Genera el reporte ejecutivo oficial en Markdown listo para copiar a Notion."""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

    md = []
    md.append(f"# 📊 Reporte Oficial de Evaluación: Strata Core HSE Evaluator")
    md.append(f"**Squad 2 — AI Engine** | **Fecha:** `{timestamp}` | **Modelo Evaluado:** `{model_name}`")
    md.append(f"**Responsables:** Sebastián (Test Runner & Schema) & Andrés (Prompt & Dataset)")
    md.append("")
    md.append("---")
    md.append("")
    md.append("## 1. Resumen Ejecutivo (KPIs del Contrato y Desempeño)")
    md.append("")
    md.append("| Métrica | Resultado | Meta / SLA | Estado |")
    md.append("| :--- | :---: | :---: | :---: |")
    md.append(f"| **Cumplimiento JSON Schema** | **{schema_rate:.1f}%** | 100% | {'✅ APROBADO' if schema_rate == 100 else '⚠️ REVISAR'} |")
    md.append(f"| **Exactitud Veredicto (Válido)** | **{valido_metrics['accuracy']:.1f}%** | >= 85.0% | {'✅ APROBADO' if valido_metrics['accuracy'] >= 85 else '⚠️ ALERTA'} |")
    md.append(f"| **F1-Score Veredicto** | **{valido_metrics['f1']:.1f}%** | >= 80.0% | {'✅ APROBADO' if valido_metrics['f1'] >= 80 else '⚠️ ALERTA'} |")
    md.append(f"| **Recall Veredicto (Sensibilidad)** | **{valido_metrics['recall']:.1f}%** | >= 85.0% | {'✅ APROBADO' if valido_metrics['recall'] >= 85 else '⚠️ ALERTA'} |")
    md.append(f"| **F1-Score Revisión Manual** | **{review_metrics['f1']:.1f}%** | >= 80.0% | {'✅ APROBADO' if review_metrics['f1'] >= 80 else '⚠️ ALERTA'} |")
    md.append(f"| **Precisión Tipo de Novedad** | **{type_accuracy:.1f}%** | >= 75.0% | {'✅ APROBADO' if type_accuracy >= 75 else '⚠️ ALERTA'} |")
    md.append(f"| **Latencia Mediana (P50)** | **{latency_stats['P50']}s** | < 8.0s | {'⚡ RÁPIDO' if latency_stats['P50'] < 8 else '⏱️ MODERADO'} |")
    md.append(f"| **Latencia P95** | **{latency_stats['P95']}s** | < 15.0s | {'✅ DENTRO DE SLA' if latency_stats['P95'] < 15 else '⚠️ COLA'} |")
    md.append("")
    md.append("---")
    md.append("")
    md.append("## 2. Matrices de Confusión")
    md.append("")
    md.append("### A. Veredicto de Validez (`valido = true` vs `valido = false`)")
    md.append("")
    md.append("| Ground Truth \\ Predicción | Predicho VÁLIDO (Positivo) | Predicho INVÁLIDO (Negativo) | Total |")
    md.append("| :--- | :---: | :---: | :---: |")
    md.append(f"| **Esperado VÁLIDO** | **TP = {valido_metrics['tp']}** | **FN = {valido_metrics['fn']}** | {valido_metrics['tp'] + valido_metrics['fn']} |")
    md.append(f"| **Esperado INVÁLIDO** | **FP = {valido_metrics['fp']}** | **TN = {valido_metrics['tn']}** | {valido_metrics['fp'] + valido_metrics['tn']} |")
    md.append(f"| **Total** | {valido_metrics['tp'] + valido_metrics['fp']} | {valido_metrics['fn'] + valido_metrics['tn']} | **{valido_metrics['total']}** |")
    md.append("")
    md.append(f"- **Precision:** `{valido_metrics['precision']}%` (De los que el modelo aprobó, cuántos eran realmente legítimos).")
    md.append(f"- **Recall:** `{valido_metrics['recall']}%` (De todas las excusas válidas, cuántas logró rescatar el modelo).")
    md.append(f"- **F1-Score:** `{valido_metrics['f1']}%` (Media armónica entre precisión y recall).")
    md.append("")
    md.append("### B. Bandera de Auditoría (`requiere_revision_manual`)")
    md.append("")
    md.append("| Ground Truth \\ Predicción | Predicho AUDITAR | Predicho AUTOMÁTICO |")
    md.append("| :--- | :---: | :---: |")
    md.append(f"| **Esperado AUDITAR** | **TP = {review_metrics['tp']}** | **FN = {review_metrics['fn']}** |")
    md.append(f"| **Esperado AUTOMÁTICO** | **FP = {review_metrics['fp']}** | **TN = {review_metrics['tn']}** |")
    md.append("")
    md.append(f"- **Accuracy Auditoría:** `{review_metrics['accuracy']}%` | **F1-Score:** `{review_metrics['f1']}%`")
    md.append("")
    md.append("---")
    md.append("")
    md.append("## 3. Distribución de Latencias de Inferencia")
    md.append("")
    md.append("| Mínimo | P50 (Mediana) | P90 | P95 | Máximo | Promedio |")
    md.append("| :---: | :---: | :---: | :---: | :---: | :---: |")
    md.append(f"| `{latency_stats['min']}s` | `{latency_stats['P50']}s` | `{latency_stats['P90']}s` | `{latency_stats['P95']}s` | `{latency_stats['max']}s` | `{latency_stats['mean']}s` |")
    md.append("")
    md.append("---")
    md.append("")
    md.append("## 4. Detalle Caso por Caso (Dataset de 10 Muestras)")
    md.append("")
    md.append("| ID | Título del Caso | Veredicto Pred (Exp) | Novedad Pred (Exp) | Manual Rev | Latencia | Schema |")
    md.append("| :-: | :--- | :---: | :---: | :---: | :---: | :---: |")

    for r in results:
        cid = r["case_id"]
        title = r["title"]
        pv = "✅ Válido" if r["prediction"].get("valido") else "❌ Inválido"
        ev = "✅ Válido" if r["ground_truth"]["valido"] else "❌ Inválido"
        v_match = "🎯" if pv == ev else "⚠️"

        pt = r["prediction"].get("tipo_novedad", "n/a")
        et = r["ground_truth"]["tipo"]
        t_match = "🎯" if pt == et else "⚠️"

        pr = "🚩 Sí" if r["prediction"].get("requiere_revision_manual") else "🟢 No"
        er = "🚩 Sí" if r["ground_truth"]["manual_review"] else "🟢 No"

        sch = "✅ OK" if r["schema_compliant"] else f"❌ Error"
        lat = f"{r['latency_sec']}s"

        md.append(f"| {cid} | {title} | {v_match} {pv} ({ev}) | {t_match} `{pt}` (`{et}`) | {pr} ({er}) | {lat} | {sch} |")

    md.append("")
    md.append("---")
    md.append("")
    md.append("## 5. cURL de Integración para n8n (Squad 1 - Jesús / Esteban / Luis)")
    md.append("")
    md.append("### Caso A: Correo CON archivo adjunto (multipart/form-data)")
    md.append("```bash")
    md.append("curl -X POST \"http://localhost:8001/api/evaluate-excuse\" \\")
    md.append("  -F \"file=@/tmp/incapacidad_estudiante.pdf\" \\")
    md.append("  -F \"email_subject=Justificante médico - Juan Pérez\" \\")
    md.append("  -F \"email_body=Buenos días, adjunto certificado de EPS Sanitas.\" \\")
    md.append("  -F \"model=qwen2.5:1.5b\"")
    md.append("```")
    md.append("")
    md.append("### Caso B: Correo SIN archivo adjunto (application/json)")
    md.append("```bash")
    md.append("curl -X POST \"http://localhost:8001/api/evaluate-excuse\" \\")
    md.append("  -H \"Content-Type: application/json\" \\")
    md.append("  -d '{")
    md.append("    \"email_subject\": \"Inasistencia por calamidad doméstica\",")
    md.append("    \"email_body\": \"Equipo HSE, hoy no podré asistir debido a un evento de fuerza mayor.\",")
    md.append("    \"model\": \"qwen2.5:1.5b\"")
    md.append("  }'")
    md.append("```")
    md.append("")
    md.append("---")
    md.append("*(Reporte generado automáticamente por `strata-core/test_squad2_evaluator.py`)*")

    return "\n".join(md)


def print_rich_dashboard(
    results: List[Dict[str, Any]],
    model: str,
    valido_metrics: Dict[str, Any],
    review_metrics: Dict[str, Any],
    latency_stats: Dict[str, float],
    schema_rate: float,
    type_accuracy: float
):
    """Imprime resumen visual de alta calidad en terminal con Rich."""
    try:
        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel
        from rich.text import Text
    except ImportError:
        # Fallback a terminal standard si rich no está instalado
        print("\n" + "=" * 80)
        print(f"📊 RESUMEN EJECUTIVO (Modelo: {model})")
        print(f"Schema Compliance: {schema_rate:.1f}%")
        print(f"Accuracy Veredicto: {valido_metrics['accuracy']:.1f}% | Precision: {valido_metrics['precision']:.1f}% | Recall: {valido_metrics['recall']:.1f}% | F1: {valido_metrics['f1']:.1f}%")
        print(f"Latencias: P50={latency_stats['P50']}s | P90={latency_stats['P90']}s | P95={latency_stats['P95']}s")
        print("=" * 80)
        return

    console = Console()

    # Título principal
    console.print()
    console.print(Panel.fit(
        f"[bold cyan]STRATA CORE (SQUAD 2)[/bold cyan] - [bold green]EVALUACIÓN Y MÉTRICAS AVANZADAS[/bold green]\n"
        f"Modelo: [yellow]{model}[/yellow] | Casos: [bold]{len(results)}[/bold] | Contrato: [bold]{schema_rate:.1f}% Válido[/bold]",
        border_style="cyan"
    ))

    # Tabla 1: KPIs Globales
    kpi_table = Table(title="🎯 KPIs de Desempeño y Validación de Contrato", border_style="bright_blue")
    kpi_table.add_column("Métrica Clave", style="bold white")
    kpi_table.add_column("Valor Obtenido", justify="center", style="bold green")
    kpi_table.add_column("Meta / SLA", justify="center", style="dim")
    kpi_table.add_column("Estado", justify="center")

    kpi_table.add_row(
        "Cumplimiento JSON Schema",
        f"{schema_rate:.1f}%",
        "100.0%",
        "[bold green]PASS[/bold green]" if schema_rate == 100 else "[bold red]FAIL[/bold red]"
    )
    kpi_table.add_row(
        "Accuracy Veredicto (Válido)",
        f"{valido_metrics['accuracy']:.1f}%",
        ">= 85.0%",
        "[bold green]PASS[/bold green]" if valido_metrics['accuracy'] >= 85 else "[bold yellow]WARN[/bold yellow]"
    )
    kpi_table.add_row(
        "Precision Veredicto",
        f"{valido_metrics['precision']:.1f}%",
        ">= 80.0%",
        "[bold green]PASS[/bold green]" if valido_metrics['precision'] >= 80 else "[bold yellow]WARN[/bold yellow]"
    )
    kpi_table.add_row(
        "Recall Veredicto",
        f"{valido_metrics['recall']:.1f}%",
        ">= 85.0%",
        "[bold green]PASS[/bold green]" if valido_metrics['recall'] >= 85 else "[bold yellow]WARN[/bold yellow]"
    )
    kpi_table.add_row(
        "F1-Score Veredicto",
        f"{valido_metrics['f1']:.1f}%",
        ">= 80.0%",
        "[bold green]PASS[/bold green]" if valido_metrics['f1'] >= 80 else "[bold yellow]WARN[/bold yellow]"
    )
    kpi_table.add_row(
        "F1-Score Bandera Revisión",
        f"{review_metrics['f1']:.1f}%",
        ">= 80.0%",
        "[bold green]PASS[/bold green]" if review_metrics['f1'] >= 80 else "[bold yellow]WARN[/bold yellow]"
    )
    kpi_table.add_row(
        "Exactitud Tipo de Novedad",
        f"{type_accuracy:.1f}%",
        ">= 75.0%",
        "[bold green]PASS[/bold green]" if type_accuracy >= 75 else "[bold yellow]WARN[/bold yellow]"
    )

    console.print(kpi_table)

    # Tabla 2: Matriz de Confusión
    cm_table = Table(title="📐 Matriz de Confusión (Veredicto de Validez)", border_style="magenta")
    cm_table.add_column("Esperado \\ Predicho", style="bold white")
    cm_table.add_column("Predicho VÁLIDO (Pos)", justify="center", style="cyan")
    cm_table.add_column("Predicho INVÁLIDO (Neg)", justify="center", style="yellow")
    cm_table.add_column("Total Real", justify="center", style="bold")

    cm_table.add_row(
        "Esperado VÁLIDO",
        f"[bold green]TP = {valido_metrics['tp']}[/bold green]",
        f"[bold red]FN = {valido_metrics['fn']}[/bold red]",
        str(valido_metrics['tp'] + valido_metrics['fn'])
    )
    cm_table.add_row(
        "Esperado INVÁLIDO",
        f"[bold red]FP = {valido_metrics['fp']}[/bold red]",
        f"[bold green]TN = {valido_metrics['tn']}[/bold green]",
        str(valido_metrics['fp'] + valido_metrics['tn'])
    )

    console.print(cm_table)

    # Tabla 3: Latencias
    lat_table = Table(title="⚡ Distribución de Latencias (Segundos)", border_style="yellow")
    lat_table.add_column("Mínimo", justify="center")
    lat_table.add_column("P50 (Mediana)", justify="center", style="bold green")
    lat_table.add_column("P90", justify="center", style="bold cyan")
    lat_table.add_column("P95", justify="center", style="bold magenta")
    lat_table.add_column("Máximo", justify="center")
    lat_table.add_column("Promedio", justify="center")

    lat_table.add_row(
        f"{latency_stats['min']}s",
        f"{latency_stats['P50']}s",
        f"{latency_stats['P90']}s",
        f"{latency_stats['P95']}s",
        f"{latency_stats['max']}s",
        f"{latency_stats['mean']}s"
    )
    console.print(lat_table)

    # Tabla 4: Detalle Caso por Caso
    case_table = Table(title="📋 Detalle Caso por Caso", border_style="white")
    case_table.add_column("ID", justify="center", style="bold")
    case_table.add_column("Título", style="dim")
    case_table.add_column("Veredicto Pred (Exp)", justify="center")
    case_table.add_column("Tipo Pred (Exp)", justify="center")
    case_table.add_column("Manual", justify="center")
    case_table.add_column("Latencia", justify="right")
    case_table.add_column("Schema", justify="center")

    for r in results:
        cid = str(r["case_id"])
        title = r["title"][:38] + ("..." if len(r["title"]) > 38 else "")
        pv = "VAL" if r["prediction"].get("valido") else "INV"
        ev = "VAL" if r["ground_truth"]["valido"] else "INV"
        v_str = f"[green]{pv}[/green]" if pv == ev else f"[red]{pv}({ev})[/red]"

        pt = (r["prediction"].get("tipo_novedad") or "n/a")[:10]
        et = (r["ground_truth"]["tipo"] or "n/a")[:10]
        t_str = f"[green]{pt}[/green]" if pt == et else f"[yellow]{pt}[/yellow]"

        pr = "SI" if r["prediction"].get("requiere_revision_manual") else "NO"
        er = "SI" if r["ground_truth"]["manual_review"] else "NO"
        r_str = f"[green]{pr}[/green]" if pr == er else f"[red]{pr}[/red]"

        lat = f"{r['latency_sec']}s"
        sch = "[green]OK[/green]" if r["schema_compliant"] else "[red]FAIL[/red]"

        case_table.add_row(cid, title, v_str, t_str, r_str, lat, sch)

    console.print(case_table)
    console.print()


async def main():
    parser = argparse.ArgumentParser(description="Runner oficial de evaluación Squad 2 (Strata Core)")
    parser.add_argument("--model", type=str, default="qwen2.5:1.5b", help="Modelo LLM de Ollama a evaluar")
    parser.add_argument("--cases", type=str, default="all", help="Casos a evaluar: 'all', número (ej: '10') o lista '1,2,5'")
    parser.add_argument("--concurrent", type=int, default=1, help="Concurrencia máxima (1=secuencial)")
    parser.add_argument("--output-md", type=str, default=DEFAULT_OUTPUT_MD, help="Ruta de exportación del reporte Markdown")
    parser.add_argument("--output-json", type=str, default=DEFAULT_OUTPUT_JSON, help="Ruta de exportación JSON crudo")
    args = parser.parse_args()

    print("=" * 80)
    print("🚀 INICIANDO TEST RUNNER STRATA CORE — SQUAD 2 (AI ENGINE)")
    print(f"   Modelo: {args.model} | Concurrencia: {args.concurrent}")
    print("=" * 80)

    if not os.path.exists(MANIFEST_PATH):
        print(f"❌ Error: No se encontró el dataset en {MANIFEST_PATH}")
        sys.exit(1)

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        cases = json.load(f)

    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = json.load(f)

    # Filtrar casos si se especificó
    if args.cases != "all":
        if "," in args.cases:
            target_ids = [int(x.strip()) for x in args.cases.split(",") if x.strip().isdigit()]
            cases = [c for c in cases if c["case_id"] in target_ids]
        elif args.cases.isdigit():
            limit = int(args.cases)
            cases = cases[:limit]

    # Reglas dinámicas de HSE
    rules = {
        "max_hours_allowed": 48,
        "valid_reasons": ["medica", "calamidad", "tramite_oficial", "falla_tecnica"],
        "requires_attachment": True,
        "min_confidence_score": 0.80
    }

    semaphore = asyncio.Semaphore(max(1, args.concurrent))
    print(f"📦 Casos a procesar: {len(cases)}")
    print("⏳ Ejecutando inferencia y validaciones de contrato...\n")

    tasks = [
        evaluate_single_case(case, schema, rules, args.model, semaphore)
        for case in cases
    ]

    results = await asyncio.gather(*tasks)

    # 1. Métricas de Veredicto (Válido vs Inválido)
    y_true_valido = [bool(r["ground_truth"]["valido"]) for r in results]
    y_pred_valido = [bool(r["prediction"].get("valido", False)) for r in results]
    valido_metrics = compute_binary_metrics(y_true_valido, y_pred_valido)

    # 2. Métricas de Auditoría (Requiere Revisión Manual)
    y_true_rev = [bool(r["ground_truth"]["manual_review"]) for r in results]
    y_pred_rev = [bool(r["prediction"].get("requiere_revision_manual", False)) for r in results]
    review_metrics = compute_binary_metrics(y_true_rev, y_pred_rev)

    # 3. Métricas de Tipo de Novedad
    type_matches = sum(
        1 for r in results
        if r["prediction"].get("tipo_novedad") == r["ground_truth"]["tipo"]
    )
    type_accuracy = round((type_matches / len(results)) * 100, 2) if results else 0.0

    # 4. Cumplimiento de Schema
    compliant_count = sum(1 for r in results if r["schema_compliant"])
    schema_rate = round((compliant_count / len(results)) * 100, 2) if results else 0.0

    # 5. Estadísticas de Latencia
    latencies = [r["latency_sec"] for r in results]
    percentiles = calculate_percentiles(latencies, [50, 90, 95])
    latency_stats = {
        **percentiles,
        "min": round(min(latencies), 3) if latencies else 0.0,
        "max": round(max(latencies), 3) if latencies else 0.0,
        "mean": round(sum(latencies) / len(latencies), 3) if latencies else 0.0
    }

    # Visualización en consola con Rich
    print_rich_dashboard(
        results=results,
        model=args.model,
        valido_metrics=valido_metrics,
        review_metrics=review_metrics,
        latency_stats=latency_stats,
        schema_rate=schema_rate,
        type_accuracy=type_accuracy
    )

    # Exportación Markdown para Notion
    md_content = generate_markdown_report(
        results=results,
        model_name=args.model,
        valido_metrics=valido_metrics,
        review_metrics=review_metrics,
        latency_stats=latency_stats,
        schema_rate=schema_rate,
        type_accuracy=type_accuracy
    )
    with open(args.output_md, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"📝 Reporte en Markdown exportado exitosamente en:\n   {args.output_md}")

    # Exportación JSON
    export_payload = {
        "metadata": {
            "model": args.model,
            "evaluated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_cases": len(results),
            "schema_compliance_rate": schema_rate,
            "type_accuracy": type_accuracy
        },
        "metrics": {
            "valido": valido_metrics,
            "revision_manual": review_metrics,
            "latencies": latency_stats
        },
        "results": results
    }
    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(export_payload, f, indent=2, ensure_ascii=False)
    print(f"💾 Reporte crudo JSON exportado en:\n   {args.output_json}\n")


if __name__ == "__main__":
    asyncio.run(main())
