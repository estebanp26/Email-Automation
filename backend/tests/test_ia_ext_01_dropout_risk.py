"""
[IA-EXT-01] Tests Unitarios e Integración: Algoritmo Predictivo de Score de Riesgo de Deserción Escolar
Riwi Permanencia y Semáforo de Riesgo (Bajo, Medio, Alto).
"""

import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.dropout_risk_engine import calculate_coder_risk_score, dropout_risk_engine

client = TestClient(app)


def test_dropout_risk_low_green():
    """
    Caso 1: Riesgo Bajo (VERDE)
    Coder con asistencia casi perfecta: 1 sola inasistencia justificada en 30 días.
    """
    today = date(2026, 9, 30)
    history = [
        {"date": str(today - timedelta(days=25)), "status": "PRESENT"},
        {"date": str(today - timedelta(days=20)), "status": "PRESENT"},
        {"date": str(today - timedelta(days=15)), "status": "JUSTIFIED_ABSENCE", "justified": True},
        {"date": str(today - timedelta(days=10)), "status": "PRESENT"},
        {"date": str(today - timedelta(days=2)), "status": "PRESENT"},
    ]
    justifications = {"approved": 1, "disapproved": 0, "pending": 0}

    result = calculate_coder_risk_score(
        attendance_history=history,
        justifications_count=justifications,
        coder_id="coder-low-01",
        coder_name="Coder Asistente Ejemplar",
        reference_date=today,
    )

    assert result["risk_level"] == "BAJO"
    assert result["color"] == "VERDE"
    assert result["risk_score"] < 40
    assert "regular" in result["reason"].lower() or "sin alertas" in result["reason"].lower()
    assert "monitoreo" in result["suggested_action"].lower()
    assert result["metrics"]["absences_last_30d"] == 1
    assert result["metrics"]["unjustified_count"] == 0


def test_dropout_risk_medium_yellow():
    """
    Caso 2: Riesgo Medio (AMARILLO)
    Coder con ausencias moderadas (2 ausencias en 30 días, 1 injustificada) que activa Alerta Preventiva U1.
    """
    today = date(2026, 9, 30)
    history = [
        {"date": str(today - timedelta(days=22)), "status": "PRESENT"},
        {"date": str(today - timedelta(days=18)), "status": "JUSTIFIED_ABSENCE", "justified": True},
        {"date": str(today - timedelta(days=12)), "status": "PRESENT"},
        {"date": str(today - timedelta(days=5)), "status": "UNJUSTIFIED_ABSENCE", "justified": False},
        {"date": str(today - timedelta(days=1)), "status": "PRESENT"},
    ]
    justifications = {"approved": 1, "disapproved": 1, "pending": 0}

    result = calculate_coder_risk_score(
        attendance_history=history,
        justifications_count=justifications,
        coder_id="coder-med-02",
        coder_name="Coder Alerta U1",
        reference_date=today,
    )

    assert result["risk_level"] == "MEDIO"
    assert result["color"] == "AMARILLO"
    assert 40 <= result["risk_score"] < 70
    assert "UMBRAL_1" in result["reason"]
    assert "Team Leader" in result["suggested_action"] or "TL" in result["suggested_action"]
    assert result["metrics"]["absences_last_30d"] == 2
    assert result["metrics"]["unjustified_count"] == 1


def test_dropout_risk_high_red():
    """
    Caso 3: Riesgo Alto (ROJO)
    Coder que acumula 4 ausencias en 14 días con racha consecutiva y faltas injustificadas.
    Supera el umbral U2 según el reglamento de Riwi.
    """
    today = date(2026, 9, 30)
    history = [
        {"date": str(today - timedelta(days=10)), "status": "UNJUSTIFIED_ABSENCE", "justified": False},
        {"date": str(today - timedelta(days=9)), "status": "UNJUSTIFIED_ABSENCE", "justified": False},
        {"date": str(today - timedelta(days=4)), "status": "UNJUSTIFIED_ABSENCE", "justified": False},
        {"date": str(today - timedelta(days=3)), "status": "UNJUSTIFIED_ABSENCE", "justified": False},
    ]
    justifications = {"approved": 0, "disapproved": 4, "pending": 0}

    result = calculate_coder_risk_score(
        attendance_history=history,
        justifications_count=justifications,
        coder_id="coder-high-03",
        coder_name="Coder En Riesgo Critico",
        reference_date=today,
    )

    assert result["risk_level"] == "ALTO"
    assert result["color"] == "ROJO"
    assert result["risk_score"] >= 70
    assert "4 ausencias en 14 días" in result["reason"]
    assert "U2" in result["reason"] or "UMBRAL_2" in result["reason"]
    assert "Bienestar y Psicología HSE" in result["suggested_action"]
    assert result["metrics"]["absences_last_14d"] == 4
    assert result["metrics"]["unjustified_count"] == 4
    assert result["metrics"]["consecutive_absences"] >= 2


def test_dropout_risk_api_endpoint():
    """
    Verifica la exposición del endpoint GET /api/v1/coders/{coder_id}/risk-score
    y que la respuesta cumpla con el contrato Pydantic.
    """
    response = client.get("/api/v1/coders/1000000001/risk-score")
    assert response.status_code == 200

    data = response.json()
    assert "risk_level" in data
    assert data["risk_level"] in ("BAJO", "MEDIO", "ALTO")
    assert "risk_score" in data
    assert 0 <= data["risk_score"] <= 100
    assert "color" in data
    assert data["color"] in ("VERDE", "AMARILLO", "ROJO")
    assert "reason" in data
    assert "suggested_action" in data
    assert "metrics" in data
    assert "current_threshold" in data["metrics"]
