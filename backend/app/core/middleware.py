"""
Middlewares de Seguridad y Control de Recursos (QA-01).

Incluye:
- RequestSizeLimitMiddleware: Intercepta peticiones HTTP masivas a nivel de cabecera Content-Length
  antes de que el cuerpo JSON sea volcado en la memoria RAM, previniendo ataques de Denegación de Servicio (DoS).
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from fastapi import status


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware que rechaza de forma inmediata peticiones con cuerpos masivos
    evaluando la cabecera Content-Length antes de parsear el JSON.
    """
    def __init__(self, app, max_upload_size_bytes: int = 20 * 1024 * 1024):
        super().__init__(app)
        self.max_upload_size_bytes = max_upload_size_bytes

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                length = int(content_length)
                if length > self.max_upload_size_bytes:
                    max_mb = self.max_upload_size_bytes // (1024 * 1024)
                    current_mb = round(length / (1024 * 1024), 2)
                    return JSONResponse(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        content={
                            "detail": f"Payload Too Large: El cuerpo de la petición ({current_mb}MB) excede el límite permitido de {max_mb}MB (Protección DoS QA-01)."
                        }
                    )
            except ValueError:
                pass

        return await call_next(request)
