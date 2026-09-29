from typing import Optional, List
from pydantic import BaseModel, Field

class CoderBase(BaseModel):
    id: Optional[str] = None
    cedula: str
    full_name: str
    email: str
    route: Optional[str] = Field(default="TypeScript Fullstack", description="Ruta o Clan técnico en Riwi")
    is_active: bool = True

class CoderIdentificationQuery(BaseModel):
    email: Optional[str] = None
    cedula: Optional[str] = None
    name: Optional[str] = None
    clan: Optional[str] = None

class CoderIdentificationResult(BaseModel):
    coder_id: Optional[str] = None
    identification_status: str = Field(..., description="IDENTIFIED | CODER_NOT_FOUND")
    matched_by: str = Field(..., description="EMAIL | CEDULA | FUZZY_NAME | NONE")
    confidence: float = Field(..., ge=0.0, le=1.0)
    coder: Optional[CoderBase] = None
    resolution_details: str
