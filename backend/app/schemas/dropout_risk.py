from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

class RiskMetricsBreakdown(BaseModel):
    absences_last_30d: int = Field(..., description="Ausencias totales en los últimos 30 días")
    absences_last_14d: int = Field(..., description="Ausencias en ventana reciente de 14 días")
    unjustified_count: int = Field(..., description="Cantidad de faltas injustificadas")
    justified_count: int = Field(..., description="Cantidad de faltas justificadas")
    unjustified_ratio: float = Field(..., description="Proporción de faltas injustificadas sobre el total")
    consecutive_absences: int = Field(..., description="Racha máxima de ausencias consecutivas recientes")
    current_threshold: str = Field(..., description="Nivel de umbral reglamentario Riwi (NINGUNO, UMBRAL_1, UMBRAL_2, etc.)")
    velocity_trend: str = Field(..., description="Tendencia de inasistencia: STABLE | ACCELERATING | RECOVERING")

class CoderDropoutRiskResponse(BaseModel):
    coder_id: str = Field(..., description="Identificador único del coder")
    coder_name: Optional[str] = Field(None, description="Nombre completo del estudiante")
    risk_level: str = Field(..., description="Nivel de riesgo: BAJO | MEDIO | ALTO")
    risk_score: int = Field(..., ge=0, le=100, description="Score predictivo de probabilidad de deserción (0-100)")
    color: str = Field(..., description="Color del semáforo: VERDE | AMARILLO | ROJO")
    reason: str = Field(..., description="Explicación detallada de la causa del riesgo basada en el reglamento")
    suggested_action: str = Field(..., description="Acción de intervención recomendada para TL y Bienestar HSE")
    metrics: Optional[RiskMetricsBreakdown] = Field(None, description="Desglose analítico de factores predictivos")
