#!/usr/bin/env python3
"""
test_telemetry_stats.py
Prueba unitaria de Sub-tarea 2: Endpoint de Telemetría en Vivo (GET /api/stats).
Verifica que las métricas en memoria rastreen aprobaciones, rechazos, latencias y uptime.
"""

import sys
import os
import asyncio
import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import server
from engine.telemetry import metrics_tracker

@pytest.mark.asyncio
async def test_telemetry():
    print("=" * 70)
    print("🧪 TEST SUB-TAREA 2: TELEMETRÍA Y MÉTRICAS EN VIVO (/api/stats)")
    print("=" * 70)

    # 1. Obtener estado inicial
    initial_stats = await server.get_system_stats()
    print("[*] Estado inicial del servicio:")
    print(f" • Servicio: {initial_stats['service']}")
    print(f" • Uptime: {initial_stats['uptime_seconds']}s")
    print(f" • Total Evaluaciones Inicial: {initial_stats['total_evaluaciones']}")

    # 2. Simular grabación de eventos
    print("\n[*] Simulando eventos de evaluación de prueba...")
    metrics_tracker.record_evaluation(valido=True, manual=False, tipo="inasistencia_medica", latency=11.2)
    metrics_tracker.record_evaluation(valido=False, manual=True, tipo="calamidad", latency=9.8)
    metrics_tracker.record_evaluation(valido=True, manual=False, tipo="falla_tecnica", latency=12.5)
    metrics_tracker.record_evaluation(valido=False, manual=True, tipo="no_identificado", latency=10.1)

    # 3. Consultar /api/stats
    updated_stats = await server.get_system_stats()
    dist = updated_stats["distribucion_veredictos"]
    lat = updated_stats["latencia_metricas"]

    print("\n[*] Métricas actualizadas obtenidas:")
    print(f" • Total Evaluaciones: {updated_stats['total_evaluaciones']}")
    print(f" • Aprobadas Auto: {dist['aprobadas_auto']}")
    print(f" • Rechazadas Auto: {dist['rechazadas_auto']}")
    print(f" • Revisión Manual: {dist['revision_manual']}")
    print(f" • Tasa Aprobación: {dist['tasa_aprobacion_pct']}%")
    print(f" • Latencia Media: {lat['media_segundos']}s (P50: {lat['p50_segundos']}s, P95: {lat['p95_segundos']}s)")
    print(f" • Desglose por tipo: {updated_stats['distribucion_tipos']}")
    print(f" • Timestamp última evaluación: {updated_stats['ultima_evaluacion_timestamp']}")

    # 4. Aserciones
    assert updated_stats["total_evaluaciones"] >= 4, "El total de evaluaciones no incrementó"
    assert dist["aprobadas_auto"] >= 2, "Aprobaciones automáticas no registradas"
    assert dist["revision_manual"] >= 2, "Revisiones manuales no registradas"
    assert lat["media_segundos"] > 0, "Latencia promedio inválida"
    assert updated_stats["distribucion_tipos"].get("falla_tecnica", 0) >= 1, "Falla técnica no contada"

    print("\n✅ SUB-TAREA 2 VALIDADA CON ÉXITO: Endpoint /api/stats funcional y preciso.")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(test_telemetry())
