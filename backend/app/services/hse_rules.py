"""
Fachada de Reglas HSE con plazos en horas hábiles (QA-04).

Este módulo es la interfaz oficial exigida por la HU ``QA-04`` (módulo
``hse_rules.py``). Es una fachada delgada sobre el motor determinista
``HSEPolicyEngine`` (BE-05, en ``hse_engine.py``): NO duplica la lógica de
negocio, la reutiliza y le añade dos capas:

1. **Plazos en horas hábiles** (lunes a viernes, excluyendo festivos
   colombianos). Conviven dos contextos diferentes:
   - ``48 horas hábiles`` (2 días hábiles): regla GENERAL para eventos
     impredecibles — ``incapacidad_medica``, ``enfermo_sin_incapacidad``,
     ``falla_tecnica`` con comprobante.
   - ``72 horas / 3 días hábiles``: EXCEPCIÓN de **fuerza mayor** —
     ``dificultades_familiares`` (calamidad doméstica / luto G1-G2) y casos
     sensibles. Otorga un plazo de gracia mayor para radicar el acta.
2. **Categoría FUERZA_MAYOR para calamidad/luto**: la falta de soporte en un
   caso de calamidad o luto dentro del plazo NUNCA se cataloga como
   ``POSIBLEMENTE_INVALIDO`` directamente; se clasifica como
   ``REVISION_MANUAL`` con regla ``FUERZA_MAYOR_SIN_SOPORTE_PENDIENTE`` para
   acompañamiento humano de HSE. Solo el vencimiento del plazo (72h hábiles)
   produce ``FUERZA_MAYOR_VENCIDA`` (inválido).
"""

from datetime import date, datetime, timedelta
from typing import FrozenSet, Optional, Set

from ..schemas.policy import PolicyEvaluationInput, PolicyEvaluationResult
from .hse_engine import HSEPolicyEngine, hse_engine

# ---------------------------------------------------------------------------
# Constantes de negocio (QA-04)
# ---------------------------------------------------------------------------

#: Plazo general: 48 horas hábiles = 2 días hábiles.
GENERAL_DEADLINE_BUSINESS_DAYS = 2
GENERAL_DEADLINE_HOURS = 48

#: Plazo de fuerza mayor: 72 horas / 3 días hábiles.
FUERZA_MAYOR_DEADLINE_BUSINESS_DAYS = 3
FUERZA_MAYOR_DEADLINE_HOURS = 72

#: Motivos de fuerza mayor (calamidad doméstica / luto). Se aceptan alias
#: usados por n8n/Strata Core además del motivo oficial del PPTX.
FUERZA_MAYOR_MOTIVES: FrozenSet[str] = frozenset(
    {
        "dificultades_familiares",
        "calamidad_domestica",
        "calamidad",
        "luto",
    }
)

#: Motivos sujetos al plazo general de 48h hábiles.
GENERAL_DEADLINE_MOTIVES: FrozenSet[str] = frozenset(
    {
        "incapacidad_medica",
        "enfermo_sin_incapacidad",
        "falla_tecnica",
    }
)

#: Festivos nacionales de Colombia 2026 (fecha -> nombre). Se usa lista fija
#: para no añadir dependencias externas; puede ampliarse por año.
COLOMBIAN_HOLIDAYS_2026: FrozenSet[date] = frozenset(
    {
        date(2026, 1, 1),  # Año Nuevo
        date(2026, 1, 12),  # Reyes Magos (trasladado)
        date(2026, 3, 23),  # San José (trasladado)
        date(2026, 4, 2),  # Jueves Santo
        date(2026, 4, 3),  # Viernes Santo
        date(2026, 5, 1),  # Día del Trabajo
        date(2026, 6, 8),  # Ascensión (trasladado)
        date(2026, 6, 15),  # Corpus Christi (trasladado)
        date(2026, 6, 29),  # Sagrado Corazón (trasladado)
        date(2026, 7, 20),  # Independencia
        date(2026, 8, 7),  # Batalla de Boyacá
        date(2026, 8, 17),  # Asunción (trasladado)
        date(2026, 10, 12),  # Día de la Raza (trasladado)
        date(2026, 11, 2),  # Todos los Santos (trasladado)
        date(2026, 11, 16),  # Independencia de Cartagena (trasladado)
        date(2026, 12, 8),  # Inmaculada Concepción
        date(2026, 12, 25),  # Navidad
    }
)

#: Grados de consanguinidad válidos para luto con acompañamiento HSE.
VALID_KINSHIP_DEGREES: FrozenSet[str] = frozenset({"G1", "G2"})


# ---------------------------------------------------------------------------
# Helpers de horas/días hábiles
# ---------------------------------------------------------------------------

def is_business_day(day: date, holidays: Optional[Set[date]] = None) -> bool:
    """True si el día es hábil (lunes-viernes y no festivo)."""
    if day.weekday() >= 5:  # sábado=5, domingo=6
        return False
    hol = holidays if holidays is not None else COLOMBIAN_HOLIDAYS_2026
    return day not in hol


def business_days_elapsed(start_d: date, report_d: date,
                           holidays: Optional[Set[date]] = None) -> int:
    """Días hábiles transcurridos en (start_d, report_d].

    Reportar el mismo día o antes del inicio = 0 (oportuno).
    """
    if report_d <= start_d:
        return 0
    elapsed = 0
    current = start_d + timedelta(days=1)
    while current <= report_d:
        if is_business_day(current, holidays):
            elapsed += 1
        current += timedelta(days=1)
    return elapsed


def business_hours_between(start: datetime, end: datetime,
                            holidays: Optional[Set[date]] = None) -> float:
    """Horas hábiles (lun-vie no festivo) entre dos datetimes.

    Los fines de semana y festivos aportan 0 horas; los días hábiles aportan
    las horas de solapamiento con la ventana [start, end]. Permite el caso
    borde "Vie 17:00 -> Mar 17:01 = 48.02h > 48h".
    """
    if end <= start:
        return 0.0
    total_seconds = 0.0
    current_day = start.date()
    while current_day <= end.date():
        if is_business_day(current_day, holidays):
            day_start = datetime.combine(current_day, datetime.min.time())
            day_end = day_start + timedelta(days=1)
            overlap_start = max(start, day_start)
            overlap_end = min(end, day_end)
            if overlap_end > overlap_start:
                total_seconds += (overlap_end - overlap_start).total_seconds()
        current_day += timedelta(days=1)
    return total_seconds / 3600.0


def is_within_general_deadline(start_d: date, report_d: date,
                                holidays: Optional[Set[date]] = None) -> bool:
    """True si el reporte está dentro de las 48h hábiles (2 días hábiles)."""
    return business_days_elapsed(start_d, report_d, holidays) <= GENERAL_DEADLINE_BUSINESS_DAYS


def is_within_fuerza_mayor_deadline(start_d: date, report_d: date,
                                     holidays: Optional[Set[date]] = None) -> bool:
    """True si el reporte está dentro de las 72h hábiles (3 días hábiles)."""
    return business_days_elapsed(start_d, report_d, holidays) <= FUERZA_MAYOR_DEADLINE_BUSINESS_DAYS


def classify_kinship(kinship_degree: Optional[str]) -> str:
    """Normaliza el grado de consanguinidad (G1/G2/G3/None -> etiqueta)."""
    if not kinship_degree:
        return "NO_ESPECIFICADO"
    normalized = kinship_degree.strip().upper()
    if normalized in ("G1", "PRIMER_GRADO", "PRIMERO"):
        return "G1"
    if normalized in ("G2", "SEGUNDO_GRADO", "SEGUNDO"):
        return "G2"
    return "G3_MAS"


# ---------------------------------------------------------------------------
# Fachada de evaluación (QA-04)
# ---------------------------------------------------------------------------

class HSERules:
    """Fachada QA-04 sobre :class:`HSEPolicyEngine`.

    Reutiliza el motor BE-05 y aplica encima:
    - recalculo de oportunidad con horas hábiles (48h general / 72h fuerza mayor),
    - categoría FUERZA_MAYOR para calamidad/luto (nunca INVALIDO directo por
      falta de soporte dentro del plazo),
    - regla de falla técnica con comprobante.
    """

    def __init__(self, engine: Optional[HSEPolicyEngine] = None,
                 holidays: Optional[Set[date]] = None):
        self._engine = engine
        self._holidays = holidays if holidays is not None else set(COLOMBIAN_HOLIDAYS_2026)

    @property
    def engine(self) -> HSEPolicyEngine:
        return self._engine if self._engine is not None else hse_engine

    def evaluate_excuse(self, payload: PolicyEvaluationInput) -> PolicyEvaluationResult:
        start_d = HSEPolicyEngine.parse_date(payload.start_date)
        end_d = HSEPolicyEngine.parse_date(payload.end_date)
        report_d = HSEPolicyEngine.parse_date(payload.report_date) if payload.report_date else date.today()
        motive = payload.excuse_type.strip().lower()

        # 1. Evaluación base del motor determinista (BE-05).
        result = self.engine.evaluate_excuse(payload)

        # 2. Rama de fuerza mayor: calamidad doméstica / luto.
        if motive in FUERZA_MAYOR_MOTIVES:
            return self._apply_fuerza_mayor_rule(payload, result, start_d, report_d)

        # 3. Rama de falla técnica con comprobante.
        if motive == "falla_tecnica":
            return self._apply_falla_tecnica_rule(payload, result, start_d, report_d)

        # 4. Recalculo de oportunidad 48h hábiles para el plazo general.
        if motive in GENERAL_DEADLINE_MOTIVES:
            return self._apply_general_deadline(payload, result, start_d, report_d)

        return result

    # -- reglas privadas ----------------------------------------------------

    def _apply_fuerza_mayor_rule(self, payload: PolicyEvaluationInput,
                                  result: PolicyEvaluationResult,
                                  start_d: date, report_d: date) -> PolicyEvaluationResult:
        """Calamidad/luto: categoría FUERZA_MAYOR, nunca INVALIDO directo por soporte."""
        within = is_within_fuerza_mayor_deadline(start_d, report_d, self._holidays)
        elapsed = business_days_elapsed(start_d, report_d, self._holidays)
        kinship = classify_kinship(getattr(payload, "kinship_degree", None))

        if within:
            result.is_timely = True
            result.timeliness_notes = (
                f"Reporte de fuerza mayor dentro del plazo de gracia "
                f"({elapsed} día(s) hábil(es) transcurridos, máximo 3). "
                f"Parentesco: {kinship}."
            )
            if payload.has_attachment:
                result.decision = "POSIBLEMENTE_VALIDO"
                result.support_valid = True
                result.escalate_to_hse = True  # acompañamiento humano, no sanción
                result.policy_rule_triggered = "FUERZA_MAYOR_SOPORTADA"
                result.support_notes = (
                    f"Calamidad/luto ({kinship}) con soporte documental y dentro de "
                    f"72h hábiles. Se valida y se escala a HSE para acompañamiento."
                )
            else:
                #21 CLAVE QA-04: sin soporte pero dentro del plazo -> REVISION, no INVALIDO.
                result.decision = "REVISION_MANUAL"
                result.support_valid = False
                result.escalate_to_hse = True
                result.policy_rule_triggered = "FUERZA_MAYOR_SIN_SOPORTE_PENDIENTE"
                result.support_notes = (
                    f"Relato de calamidad/luto ({kinship}) sin soporte adjunto. "
                    f"Cuenta con hasta 3 días hábiles para radicar el acta; "
                    f"van {elapsed}. Se remite a HSE para acompañamiento humano, "
                    f"NO se invalida directamente."
                )
            result.requires_human_review = True
            result.confidence = 0.85
        else:
            result.is_timely = False
            result.decision = "POSIBLEMENTE_INVALIDO"
            result.policy_rule_triggered = "FUERZA_MAYOR_VENCIDA"
            result.timeliness_notes = (
                f"Reporte de fuerza mayor vencido ({elapsed} días hábiles "
                f"transcurridos, máximo 3). Parentesco: {kinship}."
            )
        result.recommendation_summary = (
            f"Veredicto: {result.decision}. Motivo: '{payload.excuse_type.strip().lower()}' "
            f"({result.days_calculated} día(s)). "
            f"Oportunidad: {'Oportuno' if result.is_timely else 'Extemporáneo'} "
            f"(fuerza mayor 72h hábiles). "
            f"Soporte: {'Válido' if result.support_valid else 'Inválido/Incompleto'}. "
            f"Escalamiento HSE: {'SÍ' if result.escalate_to_hse else 'NO'}."
        )
        return result

    def _apply_falla_tecnica_rule(self, payload: PolicyEvaluationInput,
                                   result: PolicyEvaluationResult,
                                   start_d: date, report_d: date) -> PolicyEvaluationResult:
        """Falla técnica: con comprobante y oportuna -> válida; si no -> revisión."""
        within = is_within_general_deadline(start_d, report_d, self._holidays)
        elapsed = business_days_elapsed(start_d, report_d, self._holidays)
        if payload.has_attachment and within:
            result.decision = "POSIBLEMENTE_VALIDO"
            result.is_timely = True
            result.support_valid = True
            result.escalate_to_hse = False
            result.policy_rule_triggered = "FALLA_TECNICA_SOPORTADA"
            result.timeliness_notes = (
                f"Falla técnica reportada oportunamente ({elapsed} día(s) hábil(es), "
                f"máximo 2) con comprobante del operador."
            )
            result.support_notes = "Comprobante de falla (ticket/captura del operador) aportado."
            result.requires_human_review = False
        elif not within:
            result.decision = "POSIBLEMENTE_INVALIDO"
            result.is_timely = False
            result.policy_rule_triggered = "FALLA_TECNICA_EXTEMPORANEA"
            result.timeliness_notes = (
                f"Falla técnica reportada fuera de 48h hábiles ({elapsed} días hábiles)."
            )
        else:
            result.decision = "REVISION_MANUAL"
            result.support_valid = False
            result.escalate_to_hse = True
            result.requires_human_review = True
            result.policy_rule_triggered = "FALLA_TECNICA_SIN_COMPROBANTE"
            result.support_notes = (
                "Falla técnica sin comprobante del operador. Requiere verificación manual."
            )
        return result

    def _apply_general_deadline(self, payload: PolicyEvaluationInput,
                                 result: PolicyEvaluationResult,
                                 start_d: date, report_d: date) -> PolicyEvaluationResult:
        """Recalcula oportunidad con 48h hábiles para el plazo general."""
        # Los casos sensibles mantienen su ruta de acompañamiento.
        if result.is_sensitive or payload.excuse_type.strip().lower() == "situacion_emocional_critica":
            return result
        within = is_within_general_deadline(start_d, report_d, self._holidays)
        elapsed = business_days_elapsed(start_d, report_d, self._holidays)
        if within and result.policy_rule_triggered == "FUERZA_MAYOR_VENCIDA":
            # El motor usa días calendario (3 días); en horas hábiles aún está
            # vigente -> se rehabilita la oportunidad, conservando el resto.
            result.is_timely = True
            result.timeliness_notes = (
                f"Reporte dentro de 48h hábiles ({elapsed} día(s) hábil(es) "
                f"transcurridos, máximo 2). Cómputo excluye fines de semana y festivos."
            )
            if result.decision == "POSIBLEMENTE_INVALIDO":
                result.decision = "POSIBLEMENTE_VALIDO"
                result.policy_rule_triggered = "REGLA_GENERAL"
        elif not within and result.is_timely:
            result.is_timely = False
            result.decision = "POSIBLEMENTE_INVALIDO"
            result.policy_rule_triggered = "INCAPACIDAD_EXTEMPORANEA_48H"
            result.timeliness_notes = (
                f"Reporte extemporáneo ({elapsed} días hábiles transcurridos). "
                f"Supera el plazo máximo de 48 horas hábiles."
            )
        return result


#: Instancia compartida (análoga a ``hse_engine``).
hse_rules = HSERules()


def evaluate_excuse(payload: PolicyEvaluationInput) -> PolicyEvaluationResult:
    """Atajo funcional usado por el endpoint y las pruebas QA-04."""
    return hse_rules.evaluate_excuse(payload)
