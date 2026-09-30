from typing import Optional

from ...config import settings
from ...ports.sister_platform import SisterPlatformAttendancePort
from .mock_service import MockSisterPlatformAttendanceService
from .http_adapter import HttpSisterPlatformAttendanceAdapter

_mock_instance: Optional[MockSisterPlatformAttendanceService] = None


def get_sister_platform_attendance_service() -> SisterPlatformAttendancePort:
    """
    Factory para obtener la instancia adecuada del puerto de asistencia de la plataforma hermana.
    Si SISTER_PLATFORM_USE_MOCK es True, retorna el servicio simulador (Mock Service).
    Si es False, retorna el adaptador HTTP para la API externa real.
    """
    global _mock_instance

    if settings.SISTER_PLATFORM_USE_MOCK:
        if _mock_instance is None:
            _mock_instance = MockSisterPlatformAttendanceService(auto_generate=True)
        return _mock_instance

    return HttpSisterPlatformAttendanceAdapter(
        api_url=settings.SISTER_PLATFORM_API_URL,
        api_key=settings.SISTER_PLATFORM_API_KEY
    )


def reset_mock_instance() -> None:
    """Función de utilidad para reiniciar el singleton de mock en tests."""
    global _mock_instance
    _mock_instance = None
