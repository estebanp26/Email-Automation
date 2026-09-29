from abc import ABC, abstractmethod
from datetime import date
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class AttendanceStatus(str, Enum):
    """Estados oficiales de asistencia sincronizados desde plataformas externas."""
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    LATE = "LATE"
    EXCUSED = "EXCUSED"


class ExternalAttendanceRecord(BaseModel):
    """
    Registro individual de asistencia retornado por el puerto de la plataforma hermana.
    Compatible con el modelo de datos de attendance_records (DB-03).
    """
    record_id: str = Field(..., description="ID del registro de asistencia")
    coder_id: str = Field(..., description="Identificador único del coder")
    attendance_date: date = Field(..., description="Fecha de la sesión")
    status: AttendanceStatus = Field(default=AttendanceStatus.ABSENT, description="Estado: PRESENT, ABSENT, LATE, EXCUSED")
    session_type: str = Field(default="CLASE", description="Tipo de sesión: CLASE, TALLER, EVALUACION, OTRO")
    source_platform: str = Field(default="PLATAFORMA_HERMANA", description="Fuente de procedencia del registro")
    external_record_id: Optional[str] = Field(default=None, description="ID externo en el LMS/Plataforma Hermana")
    notes: Optional[str] = Field(default=None, description="Observaciones o metadatos de la sesión")


class AbsenceVerificationResult(BaseModel):
    """
    Resultado del cotejo de inasistencia solicitado por el motor de políticas HSE.
    """
    is_absent_recorded: bool = Field(
        ...,
        description="True si se constata al menos una inasistencia (ABSENT) en el rango consultado"
    )
    has_records: bool = Field(
        ...,
        description="True si existen registros de asistencia en la plataforma para las fechas indicadas"
    )
    total_days_checked: int = Field(default=0, description="Total de días del rango evaluado")
    absent_days: List[str] = Field(
        default_factory=list,
        description="Lista de fechas (YYYY-MM-DD) donde consta inasistencia ABSENT"
    )
    present_days: List[str] = Field(
        default_factory=list,
        description="Lista de fechas (YYYY-MM-DD) donde el coder consta como PRESENT"
    )
    records: List[ExternalAttendanceRecord] = Field(
        default_factory=list,
        description="Lista de registros brutos recuperados"
    )
    details: str = Field(default="", description="Detalle explicativo del resultado del cotejo")


class SisterPlatformAttendancePort(ABC):
    """
    Puerto de Entrada/Salida para Integración con Plataforma Hermana (Arquitectura Hexagonal).
    Desacopla el núcleo de dominio HSE de los detalles de transporte de la API externa.
    """

    @abstractmethod
    def get_attendance_records(
        self,
        coder_id: str,
        start_date: date,
        end_date: date
    ) -> List[ExternalAttendanceRecord]:
        """
        Recupera el historial de registros de asistencia para un coder en un rango de fechas.
        """
        pass

    @abstractmethod
    def verify_absence(
        self,
        coder_id: str,
        start_date: date,
        end_date: date
    ) -> AbsenceVerificationResult:
        """
        Consulta y valida si en las fechas indicadas realmente consta una inasistencia (ABSENT).
        Utilizado principalmente por HSEPolicyEngine durante la evaluación de justificaciones.
        """
        pass
