#!/usr/bin/env python3
"""
test_failover_resilience.py
Prueba unitaria de Sub-tarea 3: Failover de Alta Resiliencia ante desconexión o caída de Ollama.
Verifica que cuando Ollama está offline, Strata Core responda con un JSON válido de revisión manual
en lugar de crashear el servidor o generar un error HTTP 500.
"""

import sys
import os
import asyncio
import json
import jsonschema
import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import server
SCHEMA_PATH = os.path.join(BASE_DIR, "schemas", "evaluation_schema.json")

@pytest.mark.asyncio
async def test_failover():
    print("=" * 70)
    print("🧪 TEST SUB-TAREA 3: FAILOVER DE RESILIENCIA ANTE CAÍDA DE OLLAMA")
    print("=" * 70)

    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = json.load(f)

    # 1. Guardar URL original de Ollama y simular caída apuntando a puerto cerrado
    original_url = server.ai_client.ollama_url
    fake_offline_url = "http://127.0.0.1:59999"  # Puerto no existente
    print(f"[*] Simulando caída de Ollama redirigiendo a puerto offline: {fake_offline_url}")
    server.ai_client.ollama_url = fake_offline_url

    try:
        # 2. Ejecutar evaluación con Ollama offline
        res = await server.evaluate_excuse(
            file=None,
            email_subject="Incapacidad médica - Prueba de caída de servicio",
            email_body="Adjunto comprobante médico pero el servidor LLM está caído.",
            rules_json=json.dumps({"max_hours_allowed": 48})
        )

        print("\n[*] Respuesta obtenida bajo caída simulada:")
        print(f" • valido: {res.get('valido')}")
        print(f" • requiere_revision_manual: {res.get('requiere_revision_manual')}")
        print(f" • confianza_score: {res.get('confianza_score')}")
        print(f" • tipo_novedad: {res.get('tipo_novedad')}")
        print(f" • motivo_decision: {res.get('motivo_decision')}")
        print(f" • tiempo_procesamiento: {res.get('tiempo_procesamiento_segundos')}s")

        # 3. Validar cumplimiento del JSON Schema oficial
        jsonschema.validate(instance=res, schema=schema)
        print(" • Validación JSON Schema: ✅ 100% CUMPLIDO (No rompe el contrato)")

        # 4. Aserciones de seguridad
        assert res.get("valido") is False, "El veredicto no debe ser válido si la IA está caída"
        assert res.get("requiere_revision_manual") is True, "Debe marcar revisión manual obligatoria"
        assert res.get("confianza_score") == 0.0, "El score de confianza debe ser 0.0"
        assert "Ollama Offline" in res.get("motivo_decision", ""), "El motivo debe reflejar la indisponibilidad"

        print("\n✅ SUB-TAREA 3 VALIDADA CON ÉXITO: Failover a prueba de fallos activo.")
        print("=" * 70)

    finally:
        # Restaurar URL original
        server.ai_client.ollama_url = original_url
        print(f"[*] URL original de Ollama restaurada: {original_url}")

if __name__ == "__main__":
    asyncio.run(test_failover())
