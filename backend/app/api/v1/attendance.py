from datetime import date
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from ...adapters.sister_platform.factory import get_sister_platform_attendance_service
from ...adapters.sister_platform.mock_service import MockSisterPlatformAttendanceService
from ...ports.sister_platform import (
    ExternalAttendanceRecord,
    AbsenceVerificationResult,
    AttendanceStatus,
)

router = APIRouter(prefix="/attendance", tags=["Sister Platform Attendance (CONN-03)"])


class GenerateMockAbsencesRequest(BaseModel):
    coder_id: str = Field(..., description="ID del coder")
    dates: List[date] = Field(..., description="Lista de fechas en formato YYYY-MM-DD")
    session_type: str = Field(default="CLASE", description="Tipo de sesión: CLASE, TALLER, EVALUACION, OTRO")


class SetMockAttendanceRequest(BaseModel):
    coder_id: str = Field(..., description="ID del coder")
    attendance_date: date = Field(..., description="Fecha de la sesión")
    status: AttendanceStatus = Field(..., description="Estado: PRESENT, ABSENT, LATE, EXCUSED")
    session_type: str = Field(default="CLASE", description="Tipo de sesión")
    notes: Optional[str] = Field(default=None, description="Observaciones")


@router.get(
    "/records",
    response_model=List[ExternalAttendanceRecord],
    summary="Consultar registros de asistencia de la Plataforma Hermana"
)
async def get_attendance_records(
    coder_id: str = Query(..., description="ID del coder"),
    start_date: date = Query(..., description="Fecha inicio YYYY-MM-DD"),
    end_date: date = Query(..., description="Fecha fin YYYY-MM-DD"),
):
    adapter = get_sister_platform_attendance_service()
    return adapter.get_attendance_records(coder_id=coder_id, start_date=start_date, end_date=end_date)


@router.get(
    "/verify",
    response_model=AbsenceVerificationResult,
    summary="Cotejar inasistencia (ABSENT) en la Plataforma Hermana"
)
async def verify_absence(
    coder_id: str = Query(..., description="ID del coder"),
    start_date: date = Query(..., description="Fecha inicio YYYY-MM-DD"),
    end_date: date = Query(..., description="Fecha fin YYYY-MM-DD"),
):
    adapter = get_sister_platform_attendance_service()
    return adapter.verify_absence(coder_id=coder_id, start_date=start_date, end_date=end_date)


@router.post(
    "/mock/absences",
    response_model=List[ExternalAttendanceRecord],
    status_code=status.HTTP_201_CREATED,
    summary="Generar inasistencias de prueba para cualquier coder (Mock Service)"
)
async def generate_mock_absences(payload: GenerateMockAbsencesRequest):
    adapter = get_sister_platform_attendance_service()
    if not isinstance(adapter, MockSisterPlatformAttendanceService):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El servicio actual no es MockSisterPlatformAttendanceService (SISTER_PLATFORM_USE_MOCK está en false)."
        )
    return adapter.generate_mock_absences(
        coder_id=payload.coder_id,
        dates=payload.dates,
        session_type=payload.session_type
    )


@router.post(
    "/mock/status",
    response_model=ExternalAttendanceRecord,
    status_code=status.HTTP_200_OK,
    summary="Fijar estado de asistencia simulado para un coder (Mock Service)"
)
async def set_mock_status(payload: SetMockAttendanceRequest):
    adapter = get_sister_platform_attendance_service()
    if not isinstance(adapter, MockSisterPlatformAttendanceService):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El servicio actual no es MockSisterPlatformAttendanceService."
        )
    return adapter.set_coder_attendance(
        coder_id=payload.coder_id,
        attendance_date=payload.attendance_date,
        status=payload.status,
        session_type=payload.session_type,
        notes=payload.notes
    )
