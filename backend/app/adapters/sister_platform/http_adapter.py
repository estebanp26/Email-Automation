import logging
from datetime import date
from typing import List, Optional
import httpx

from ...ports.sister_platform import (
    SisterPlatformAttendancePort,
    ExternalAttendanceRecord,
    AbsenceVerificationResult,
    AttendanceStatus,
)

logger = logging.getLogger(__name__)


class HttpSisterPlatformAttendanceAdapter(SisterPlatformAttendancePort):
    """
    Adaptador HTTP para comunicación REST nativa con la API de Asistencia de la Plataforma Hermana.
    Preparado para conectar con el servicio externo real una vez desplegado en producción.
    """

    def __init__(
        self,
        api_url: str,
        api_key: Optional[str] = None,
        timeout: float = 10.0
    ):
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key or ""
        self.timeout = timeout

    def _get_headers(self) -> dict:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Riwi-HSE-Attendance-Adapter/3.0",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            headers["X-API-Key"] = self.api_key
        return headers

    def get_attendance_records(
        self,
        coder_id: str,
        start_date: date,
        end_date: date
    ) -> List[ExternalAttendanceRecord]:
        """
        Consulta el endpoint GET /attendance/records de la plataforma hermana.
        """
        endpoint = f"{self.api_url}/attendance/records"
        params = {
            "coder_id": coder_id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(endpoint, params=params, headers=self._get_headers())
                if response.status_code == 200:
                    data = response.json()
                    items = data if isinstance(data, list) else data.get("records", [])
                    records: List[ExternalAttendanceRecord] = []
                    for item in items:
                        rec = ExternalAttendanceRecord(
                            record_id=str(item.get("id") or item.get("record_id")),
                            coder_id=str(item.get("coder_id", coder_id)),
                            attendance_date=date.fromisoformat(str(item.get("attendance_date") or item.get("date"))[:10]),
                            status=AttendanceStatus(str(item.get("status", "ABSENT")).upper()),
                            session_type=str(item.get("session_type", "CLASE")),
                            source_platform=str(item.get("source_platform", "PLATAFORMA_HERMANA")),
                            external_record_id=str(item.get("external_record_id") or item.get("id")),
                            notes=item.get("notes")
                        )
                        records.append(rec)
                    return records
                else:
                    logger.warning(
                        "Plataforma Hermana retornó status %d: %s",
                        response.status_code,
                        response.text
                    )
                    return []
        except Exception as e:
            logger.error("Error al consultar API de la plataforma hermana: %s", str(e))
            return []

    def verify_absence(
        self,
        coder_id: str,
        start_date: date,
        end_date: date
    ) -> AbsenceVerificationResult:
        """
        Consulta y valida si en las fechas indicadas existe una inasistencia (ABSENT).
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
                details=f"No se obtuvieron registros remotos para el coder '{coder_id}' en {start_date} a {end_date}."
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

        details = (
            f"Cotejo API Externa: {'Inasistencia ABSENT confirmada' if is_absent else 'Sin inasistencia registrada'} "
            f"({len(absent_days)} faltas detectadas en {total_days} días)."
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
