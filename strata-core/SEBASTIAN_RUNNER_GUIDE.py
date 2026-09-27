#!/usr/bin/env python3
"""
SEBASTIAN_RUNNER_GUIDE.py
=============================================================================
PLANTILLA DE REFERENCIA Y GUÍA PARA SEBASTIÁN (SQUAD 2 - AI ENGINE)
=============================================================================
Autor base: Andrés (Dataset & Prompt Engineering)
Destinatario: Sebastián (Test Runner, JSON Schema Validation & Advanced Metrics)

Contexto:
- Andrés preparó el Prompt Parametrizado (strata-core/prompts/evaluator_system_prompt.md)
  y los 10 casos de prueba con ground truth (strata-core/test_samples/cases_manifest.json).
- Este archivo sirve como base mínima funcional para que Sebastián construya
  el script definitivo de evaluación con métricas profesionales para el equipo.

Métricas sugeridas a incorporar por Sebastián:
1. Matriz de Confusión (TP, FP, TN, FN) comparando resultado vs ground truth (expected).
2. Precisión, Recall, F1-Score y Exactitud (Accuracy) global y por categoría.
3. Distribución de latencias: Percentiles (P50, P90, P95, Min, Max).
4. Tasa de cumplimiento estricto del JSON Schema (schemas/evaluation_schema.json).
5. Desglose de banderas de auditoría (requiere_revision_manual vs ground truth).
6. Exportación opcional a Markdown / CSV / JSON o reporte gráfico con Rich/Tabulate.
=============================================================================
"""

import os
import sys
import json
import time
import asyncio
from typing import List, Dict, Any
import jsonschema

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

import server

MANIFEST_PATH = os.path.join(BASE_DIR, "test_samples", "cases_manifest.json")
SCHEMA_PATH = os.path.join(BASE_DIR, "schemas", "evaluation_schema.json")
DEFAULT_OUTPUT_JSON = os.path.join(BASE_DIR, "EVALUATION_REPORT_SEBAS.json")


class MockFastAPIUploadFile:
    """Mock para simular subida de archivos multipart en FastAPI sin abrir socket HTTP."""
    def __init__(self, file_path: str):
        self.filename = os.path.basename(file_path)
        self.file = open(file_path, "rb")

    def close(self):
        if not self.file.closed:
            self.file.close()


async def evaluate_single_case(case: Dict[str, Any], schema: Dict[str, Any], rules_json_str: str) -> Dict[str, Any]:
    """Evalúa un caso contra el motor Strata Core y valida su contrato JSON."""
    cid = case["case_id"]
    title = case["title"]
    fname = case.get("file")
    email_sub = case.get("email_subject")
    email_body = case.get("email_body")
    samples_dir = os.path.join(BASE_DIR, "test_samples")

    upload_obj = None
    if fname:
        fpath = os.path.join(samples_dir, fname)
        upload_obj = MockFastAPIUploadFile(fpath)

    t0 = time.perf_counter()
    try:
        response_dict = await server.evaluate_excuse(
            file=upload_obj,
            email_body=email_body,
            email_subject=email_sub,
            rules_json=rules_json_str,
            model="qwen2.5:1.5b"
        )
    finally:
        if upload_obj:
            upload_obj.close()
    elapsed = time.perf_counter() - t0

    # Validación de Schema
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


def calculate_baseline_metrics(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    TODO (Sebastián):
    Expandir esta función con cálculos estadísticos y métricas de clasificación:
    - True Positives (TP), False Positives (FP), True Negatives (TN), False Negatives (FN).
    - Precision = TP / (TP + FP)
    - Recall = TP / (TP + FN)
    - F1-Score = 2 * (P * R) / (P + R)
    - Percentiles de latencia (P50, P90, P95) usando numpy o statistics
    """
    total = len(results)
    compliant = sum(1 for r in results if r["schema_compliant"])
    latencies = [r["latency_sec"] for r in results]
    avg_latency = sum(latencies) / total if total > 0 else 0.0

    # Matriz básica de aciertos en validez
    correct_verdicts = sum(
        1 for r in results 
        if r["prediction"].get("valido") == r["ground_truth"]["valido"]
    )
    accuracy_verdict = (correct_verdicts / total) * 100 if total > 0 else 0.0

    return {
        "total_cases": total,
        "schema_compliance_rate": f"{compliant}/{total} ({(compliant/total)*100:.1f}%)",
        "verdict_accuracy": f"{correct_verdicts}/{total} ({accuracy_verdict:.1f}%)",
        "avg_latency_sec": round(avg_latency, 2),
        "min_latency_sec": round(min(latencies), 2) if latencies else 0,
        "max_latency_sec": round(max(latencies), 2) if latencies else 0,
    }


async def main():
    print("=" * 80)
    print("📋 GUÍA BASE DE EJECUCIÓN - SQUAD 2 (AI ENGINE)")
    print("Diseñado para que Sebastián amplíe el cálculo de métricas y validación")
    print("=" * 80)

    if not os.path.exists(MANIFEST_PATH):
        print(f"❌ Error: No se encontró el dataset en {MANIFEST_PATH}")
        sys.exit(1)

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        cases = json.load(f)

    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = json.load(f)

    # Reglas dinámicas de prueba
    rules = {
        "max_hours_allowed": 48,
        "valid_reasons": ["medica", "calamidad", "tramite_oficial", "falla_tecnica"],
        "requires_attachment": True,
        "min_confidence_score": 0.80
    }
    rules_json_str = json.dumps(rules)

    print(f"Cargados {len(cases)} casos desde el manifest.")
    print("Iniciando evaluación secuencial (Sebastián puede paralelizar o añadir CLI args)...")

    results = []
    for case in cases:
        print(f" -> Procesando Caso {case['case_id']:02d}: {case['title']} ...", end="", flush=True)
        res = await evaluate_single_case(case, schema, rules_json_str)
        pred_val = "VÁLIDO" if res["prediction"].get("valido") else "INVÁLIDO"
        exp_val = "VÁLIDO" if res["ground_truth"]["valido"] else "INVÁLIDO"
        match_icon = "✅" if pred_val == exp_val else "⚠️"
        print(f" {match_icon} [{pred_val}] en {res['latency_sec']}s (Schema: {'OK' if res['schema_compliant'] else 'FAIL'})")
        results.append(res)

    metrics = calculate_baseline_metrics(results)
    
    print("\n" + "=" * 80)
    print("📊 MÉTRICAS BASE OBTENIDAS:")
    print("=" * 80)
    for k, v in metrics.items():
        print(f" • {k:25s}: {v}")
    print("=" * 80)
    print("💡 Sebastián: Puedes agregar generación de tablas (Rich/Tabulate), matriz de confusión,")
    print("   exportación en Markdown para el Notion y argumentos con argparse (--cases, --model).")


if __name__ == "__main__":
    asyncio.run(main())
