"""
[IA-EXT-01] Algoritmo Predictivo de Score de Riesgo de Deserción Escolar
Strata Core AI Engine - Riwi Permanencia y Semáforo de Riesgo
"""

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional


def _parse_event_date(date_val: Any) -> Optional[date]:
    if isinstance(date_val, datetime):
        return date_val.date()
    if isinstance(date_val, date):
        return date_val
    if isinstance(date_val, str) and date_val.strip():
        for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y/%m/%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(date_val[:10], fmt).date()
            except ValueError:
                continue
    return None


def calculate_coder_risk_score(
    attendance_history: List[Dict[str, Any]],
    justifications_count: Optional[Dict[str, int]] = None,
    coder_id: str = "coder-default",
    coder_name: Optional[str] = None,
    reference_date: Optional[date] = None,
) -> Dict[str, Any]:
    """
    Calcula el Score de Riesgo de Deserción Escolar (0 - 100) y semáforo para un coder.
    """
    parsed_dates = []
    for event in attendance_history:
        d = _parse_event_date(event.get("date"))
        if d:
            parsed_dates.append(d)

    if not reference_date:
        reference_date = max(parsed_dates) if parsed_dates else date.today()

    cutoff_30d = reference_date - timedelta(days=30)
    cutoff_14d = reference_date - timedelta(days=14)
    cutoff_7d = reference_date - timedelta(days=7)

    absences_30d = 0
    absences_14d = 0
    absences_7d = 0

    history_unjustified = 0
    history_justified = 0

    sorted_events = []
    for event in attendance_history:
        d = _parse_event_date(event.get("date"))
        if d and d >= cutoff_30d:
            sorted_events.append((d, event))

    sorted_events.sort(key=lambda x: x[0])

    current_streak = 0
    max_streak = 0

    for d, ev in sorted_events:
        status = str(ev.get("status", "")).upper()
        is_absent = (
            "ABSEN" in status
            or "FALTA" in status
            or "INASISTENCIA" in status
            or "UNJUSTIFIED" in status
            or status == "JUSTIFIED"
            or ev.get("absent") is True
            or ev.get("is_absent") is True
            or (ev.get("justified") is False)
        )
        is_unjustified = (
            "UNJUSTIFIED" in status
            or ev.get("justified") is False
            or ev.get("is_justified") is False
        )
        is_justified = (not is_unjustified) and (
            "JUSTIFIED" in status
            or "EXCUSED" in status
            or ev.get("justified") is True
            or ev.get("is_justified") is True
        )

        if is_absent:
            absences_30d += 1
            if d >= cutoff_14d:
                absences_14d += 1
            if d >= cutoff_7d:
                absences_7d += 1

            if is_justified:
                history_justified += 1
            else:
                history_unjustified += 1

            current_streak += 1
            if current_streak > max_streak:
                max_streak = current_streak
        else:
            current_streak = 0

    if justifications_count:
        approved_ext = int(justifications_count.get("approved", 0))
        disapproved_ext = int(justifications_count.get("disapproved", 0))

        unjustified_count = max(history_unjustified, disapproved_ext)
        justified_count = max(history_justified, approved_ext)
    else:
        unjustified_count = history_unjustified
        justified_count = history_justified

    total_absences = max(absences_30d, unjustified_count + justified_count)
    unjustified_ratio = round(
        (unjustified_count / total_absences) if total_absences > 0 else 0.0, 2
    )

    if absences_14d >= 3 and (absences_14d / max(1, absences_30d)) >= 0.6:
        velocity_trend = "ACCELERATING"
    elif absences_30d >= 3 and absences_14d <= 1:
        velocity_trend = "RECOVERING"
    else:
        velocity_trend = "STABLE"

    if unjustified_count >= 15 or absences_30d >= 15:
        threshold = "UMBRAL_4"
    elif unjustified_count >= 10 or absences_30d >= 10:
        threshold = "UMBRAL_3"
    elif unjustified_count >= 3 or absences_14d >= 4:
        threshold = "UMBRAL_2"
    elif unjustified_count >= 1 or absences_14d >= 1:
        threshold = "UMBRAL_1"
    else:
        threshold = "NINGUNO"

    score_freq = min(35.0, absences_30d * 7.0)
    score_recency = min(25.0, absences_14d * 6.5)
    score_unjustified = (unjustified_ratio * 15.0) + min(10.0, unjustified_count * 2.5)
    score_streak = min(15.0, max_streak * 5.0)

    raw_score = score_freq + score_recency + score_unjustified + score_streak

    if threshold == "UMBRAL_4":
        raw_score = max(raw_score, 95.0)
    elif threshold == "UMBRAL_3":
        raw_score = max(raw_score, 85.0)
    elif threshold == "UMBRAL_2":
        raw_score = max(raw_score, 78.0)
    elif threshold == "UMBRAL_1":
        raw_score = max(raw_score, 45.0)

    risk_score = int(round(min(100.0, max(0.0, raw_score))))

    if risk_score >= 70 or threshold in ("UMBRAL_2", "UMBRAL_3", "UMBRAL_4"):
        risk_level = "ALTO"
        color = "ROJO"
        u_label = "U2" if threshold == "UMBRAL_2" else ("U3" if threshold == "UMBRAL_3" else "U4")
        if absences_14d > 0:
            reason = f"El coder acumula {absences_14d} ausencias en 14 días. Supera el umbral de alerta {u_label} según reglamento Riwi."
        else:
            reason = f"El coder acumula {absences_30d} ausencias ({unjustified_count} injustificadas). Supera el umbral de alerta {u_label} según reglamento Riwi."
        suggested_action = "Citar a sesión 1 a 1 con Bienestar y Psicología HSE"

    elif risk_score >= 40 or threshold == "UMBRAL_1":
        risk_level = "MEDIO"
        color = "AMARILLO"
        reason = f"El coder registra {absences_30d} ausencias en los últimos 30 días ({absences_14d} recientes). Activa alerta {threshold} con tendencia {velocity_trend.lower()}."
        suggested_action = "Seguimiento preventivo por Team Leader (TL) y verificación de compromisos de asistencia"

    else:
        risk_level = "BAJO"
        color = "VERDE"
        reason = "Asistencia regular dentro de los parámetros esperados de permanencia en Riwi. Sin alertas de deserción activas."
        suggested_action = "Mantener monitoreo estándar en el dashboard de asistencia"

    result = {
        "risk_level": risk_level,
        "risk_score": risk_score,
        "color": color,
        "reason": reason,
        "suggested_action": suggested_action,
        "metrics": {
            "absences_last_30d": absences_30d,
            "absences_last_14d": absences_14d,
            "unjustified_count": unjustified_count,
            "justified_count": justified_count,
            "unjustified_ratio": unjustified_ratio,
            "consecutive_absences": max_streak,
            "current_threshold": threshold,
            "velocity_trend": velocity_trend,
        },
    }

    if coder_id:
        result["coder_id"] = coder_id
    if coder_name:
        result["coder_name"] = coder_name

    return result
