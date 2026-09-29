import uuid
from datetime import date, timedelta
from typing import Dict, List, Optional

from ...ports.sister_platform import (
    SisterPlatformAttendancePort,
    ExternalAttendanceRecord,
    AbsenceVerificationResult,
    AttendanceStatus,
)


class MockSisterPlatformAttendanceService(SisterPlatformAttendancePort):
    """
    Adaptador Simulador (Mock Service) para la API de Asistencia de la Plataforma Hermana.
    Cumple con el criterio [CONN-03]: Capaz de generar inasistencias de prueba para cualquier coder,
    permitiendo desarrollar, probar y simular la integración de forma desacoplada.
    """

    def __init__(self, auto_generate: bool = True):
        """
        :param auto_generate: Si es True, cuando se consulte un coder sin registros previos,
                              el simulador generará automáticamente inasistencias (ABSENT) válidas
                              para los días consultados, facilitando pruebas de extremo a extremo.
        """
        self.auto_generate = auto_generate
        # Estructura: records_db[coder_id][date_iso] = ExternalAttendanceRecord
        self._records_db: Dict[str, Dict[str, ExternalAttendanceRecord]] = {}
        self._seed_default_mock_data()

    def _seed_default_mock_data(self) -> None:
        """Carga datos iniciales de prueba para coders conocidos."""
        base_date = date.today()
        test_coders = [
            "coder-1000000001",
            "1000000001",
            "coder-123",
            "coder-dev-01"
        ]
        for cid in test_coders:
            # Generar inasistencias para hoy y los 3 días anteriores
            for offset in range(4):
                d = base_date - timedelta(days=offset)
                self.set_coder_attendance(
                    coder_id=cid,
                    attendance_date=d,
                    status=AttendanceStatus.ABSENT,
                    session_type="CLASE",
                    notes="Inasistencia simulada por defecto para pruebas de desarrollo"
                )

    def generate_mock_absences(
        self,
        coder_id: str,
        dates: List[date],
        session_type: str = "CLASE"
    ) -> List[ExternalAttendanceRecord]:
        """
        Genera explícitamente inasistencias de prueba (ABSENT) para cualquier coder
        en la lista de fechas indicada.
        """
        created_records: List[ExternalAttendanceRecord] = []
        for d in dates:
            rec = self.set_coder_attendance(
                coder_id=coder_id,
                attendance_date=d,
                status=AttendanceStatus.ABSENT,
                session_type=session_type,
                notes=f"Inasistencia generada por mock service para {coder_id}"
            )
            created_records.append(rec)
        return created_records

    def set_coder_attendance(
        self,
        coder_id: str,
        attendance_date: date,
        status: AttendanceStatus,
        session_type: str = "CLASE",
        notes: Optional[str] = None
    ) -> ExternalAttendanceRecord:
        """
        Establece o sobrescribe el estado de asistencia de un coder para una fecha específica.
        Permite simular escenarios controlados (ej: coder estuvo PRESENTE para probar rechazo de excusa).
        """
        if coder_id not in self._records_db:
            self._records_db[coder_id] = {}

        d_str = attendance_date.isoformat()
        rec = ExternalAttendanceRecord(
            record_id=f"mock-att-{uuid.uuid4().hex[:10]}",
            coder_id=coder_id,
            attendance_date=attendance_date,
            status=status,
            session_type=session_type,
            source_platform="SISTER_PLATFORM_MOCK",
            external_record_id=f"ext-lms-{coder_id}-{d_str}",
            notes=notes or f"Registro simulado de asistencia: {status.value}"
        )
        self._records_db[coder_id][d_str] = rec
        return rec

    def clear_coder_records(self, coder_id: Optional[str] = None) -> None:
        """Limpia los registros simulados de un coder específico o de todos."""
        if coder_id:
            self._records_db.pop(coder_id, None)
        else:
            self._records_db.clear()

    def get_attendance_records(
        self,
        coder_id: str,
        start_date: date,
        end_date: date
    ) -> List[ExternalAttendanceRecord]:
        """
        Recupera los registros de asistencia en el intervalo [start_date, end_date].
        Si auto_generate está activo y no hay registros para el coder, genera inasistencias al vuelo.
        """
        if start_date > end_date:
            start_date, end_date = end_date, start_date

        coder_records = self._records_db.get(coder_id, {})

        # Si el coder no tiene registros registrados y auto_generate está activo:
        # Generar inasistencias automáticas para todo el intervalo
        if not coder_records and self.auto_generate:
            curr = start_date
            while curr <= end_date:
                self.set_coder_attendance(
                    coder_id=coder_id,
                    attendance_date=curr,
                    status=AttendanceStatus.ABSENT,
                    session_type="CLASE",
                    notes="Inasistencia autogenerada por MockSisterPlatformAttendanceService"
                )
                curr += timedelta(days=1)
            coder_records = self._records_db.get(coder_id, {})

        # Filtrar por el rango de fechas
        matched: List[ExternalAttendanceRecord] = []
        curr = start_date
        while curr <= end_date:
            d_str = curr.isoformat()
            if d_str in coder_records:
                matched.append(coder_records[d_str])
            curr += timedelta(days=1)

        return matched

    def verify_absence(
        self,
        coder_id: str,
        start_date: date,
        end_date: date
    ) -> AbsenceVerificationResult:
        """
        Coteja si en las fechas indicadas existe una inasistencia (ABSENT) registrada.
        """
        if start_date > end_date:
            start_date, end_date = end_date, start_date

        total_days = (end_date - start_date).days + 1
        records = self.get_attendance_records(coder_id, start_date, end_date)

        if not records:
            return AbsenceVerificationResult(
                is_absent_recorded=False,
                has_records=False,
                total_days_checked=total_days,
                absent_days=[],
                present_days=[],
                records=[],
                details=f"No se encontraron registros de asistencia para coder '{coder_id}' en el periodo {start_date} a {end_date}."
            )

        absent_days: List[str] = []
        present_days: List[str] = []

        for r in records:
            d_str = r.attendance_date.isoformat()
            if r.status == AttendanceStatus.ABSENT:
                absent_days.append(d_str)
            elif r.status in [AttendanceStatus.PRESENT, AttendanceStatus.LATE]:
                present_days.append(d_str)

        is_absent = len(absent_days) > 0

        if is_absent:
            details = (
                f"Inasistencia confirmada: Se constató estado ABSENT en {len(absent_days)} de {total_days} día(s) "
                f"evaluados ({', '.join(absent_days)})."
            )
        else:
            details = (
                f"Sin inasistencia registrada: El coder consta como PRESENTE/TARDANZA en los registros consultados "
                f"({', '.join(present_days)})."
            )

        return AbsenceVerificationResult(
            is_absent_recorded=is_absent,
            has_records=True,
            total_days_checked=total_days,
            absent_days=absent_days,
            present_days=present_days,
            records=records,
            details=details
        )
