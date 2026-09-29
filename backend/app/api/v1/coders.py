from fastapi import APIRouter, HTTPException, Query, status
from typing import List, Optional

from ...schemas.coder import (
    CoderBase,
    CoderIdentificationQuery,
    CoderIdentificationResult,
)
from ...services.coder_resolver import coder_resolver

router = APIRouter(prefix="/coders", tags=["Coders & Identificación en Cascada (BE-02)"])


@router.post(
    "/resolve",
    response_model=CoderIdentificationResult,
    status_code=status.HTTP_200_OK,
    summary="Identificación de Coder en Cascada (BE-02)"
)
async def resolve_coder(query: CoderIdentificationQuery):
    """
    Ejecuta la cascada determinista de 4 niveles para asociar un remitente con un coder registrado:
    1. Match exacto por Email.
    2. Match exacto por Cédula (7-10 dígitos).
    3. Match de similitud por Nombre Completo (>= 82% confianza).
    4. Fallback: CODER_NOT_FOUND.
    """
    return coder_resolver.identify_coder(query)


@router.get(
    "/count",
    summary="Total de coders registrados en el índice"
)
async def get_coders_count():
    """Retorna la cantidad total de coders cargados en el índice de resolución."""
    return {
        "total_coders": len(coder_resolver._coders_list),
        "status": "ready"
    }


@router.get(
    "/search",
    response_model=List[CoderBase],
    summary="Búsqueda rápida de coders por término"
)
async def search_coders(q: str = Query(..., min_length=2, description="Cédula, nombre o correo")):
    """Búsqueda rápida en el catálogo de coders para autocompletado en el frontend."""
    term = q.strip().lower()
    results = []
    for c in coder_resolver._coders_list:
        if term in c.full_name.lower() or term in c.cedula or term in c.email.lower() or (c.route and term in c.route.lower()):
            results.append(c)
            if len(results) >= 20:
                break
    return results
