import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..schemas.coder import (
    CoderBase,
    CoderIdentificationQuery,
    CoderIdentificationResult,
)
from ..schemas.email import NormalizedEmail


def remove_accents(input_str: str) -> str:
    """Elimina tildes y diacríticos para comparación fonética/textual."""
    nfkd_form = unicodedata.normalize("NFKD", input_str)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)]).lower()


class CoderResolutionService:
    """
    Servicio de Identificación de Coders en Cascada (BE-02).
    Aplica una estrategia de 4 niveles para asociar un correo/remitente con el catálogo maestro:
    1. Match Exacto por Correo Institucional / Registrado (100% confianza)
    2. Match Exacto por Cédula (Documento de Identidad) (100% confianza)
    3. Match de Similitud por Nombre Completo (Fuzzy Matching >= 85%)
    4. Fallback: CODER_NOT_FOUND (Desencadena solicitud de datos de matrícula)
    """

    def __init__(self):
        self._coders_by_email: Dict[str, CoderBase] = {}
        self._coders_by_cedula: Dict[str, CoderBase] = {}
        self._coders_list: List[CoderBase] = []
        self._load_master_coders()

    def _load_master_coders(self):
        """Carga los 297 coders reales desde el script SQL oficial o semillas integradas."""
        sql_path = Path(__file__).resolve().parent.parent.parent.parent / "init_database.sql"
        loaded = 0

        if sql_path.exists():
            try:
                with open(sql_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                
                # Expresión regular para capturar filas de inserción de coders
                # ('1000000001', 'Jose Luis Acevedo Vargas', 'jose.acevedo@riwi.io', 'Node.js Backend', true)
                row_pattern = r"\('(\d+)',\s*'([^']+)',\s*'([^']+)',\s*'([^']+)',\s*(true|false)\)"
                matches = re.findall(row_pattern, content, re.IGNORECASE)

                for cedula, full_name, email, route, is_active_str in matches:
                    coder = CoderBase(
                        id=f"coder-{cedula}",
                        cedula=cedula.strip(),
                        full_name=full_name.strip(),
                        email=email.strip().lower(),
                        route=route.strip(),
                        is_active=is_active_str.lower() == "true"
                    )
                    self._add_coder(coder)
                    loaded += 1
            except Exception as e:
                print(f"[CoderResolutionService] Advertencia cargando SQL: {e}")

        # Si por alguna razón no cargó del archivo, sembramos coders clave de demostración y pruebas
        if loaded == 0:
            fallback_seeds = [
                ("1045892341", "Carlos Andrés Pérez", "carlos.perez@riwi.io", "TypeScript Fullstack"),
                ("1082938475", "Laura Gómez", "laura.gomez@riwi.io", "Java Spring Boot"),
                ("1140889922", "Andrés Felipe Mendoza", "andres.mendoza@riwi.io", "Node.js Backend"),
                ("1000000001", "Jose Luis Acevedo Vargas", "jose.acevedo@riwi.io", "Node.js Backend"),
                ("1000000297", "Andrea Valentina Zárate Rubio", "andrea.zarate@riwi.io", "Analítica de Datos & BI"),
            ]
            for cedula, name, email, route in fallback_seeds:
                self._add_coder(CoderBase(
                    id=f"coder-{cedula}",
                    cedula=cedula,
                    full_name=name,
                    email=email.lower(),
                    route=route,
                    is_active=True
                ))

    def _add_coder(self, coder: CoderBase):
        self._coders_by_email[coder.email.lower()] = coder
        self._coders_by_cedula[coder.cedula] = coder
        self._coders_list.append(coder)

    def identify_coder(self, query: CoderIdentificationQuery) -> CoderIdentificationResult:
        """
        Ejecuta la cascada de resolución:
        Email -> Cédula -> Nombre Fuzzy -> No Encontrado
        """
        # 1. Cascada Nivel 1: Match por Correo
        if query.email:
            clean_email = query.email.strip().lower()
            if clean_email in self._coders_by_email:
                coder = self._coders_by_email[clean_email]
                return CoderIdentificationResult(
                    coder_id=coder.id,
                    identification_status="IDENTIFIED",
                    matched_by="EMAIL",
                    confidence=1.0,
                    coder=coder,
                    resolution_details=f"Identificado con 100% de coincidencia por correo electrónico registrado '{clean_email}'."
                )

        # 2. Cascada Nivel 2: Match por Cédula (Documento)
        if query.cedula:
            clean_cedula = re.sub(r"\D", "", query.cedula)
            if clean_cedula in self._coders_by_cedula:
                coder = self._coders_by_cedula[clean_cedula]
                return CoderIdentificationResult(
                    coder_id=coder.id,
                    identification_status="IDENTIFIED",
                    matched_by="CEDULA",
                    confidence=1.0,
                    coder=coder,
                    resolution_details=f"Identificado con 100% de coincidencia por documento de identidad (Cédula: {clean_cedula})."
                )

        # 3. Cascada Nivel 3: Match Difuso por Nombre Completo (Fuzzy Matching)
        if query.name and len(query.name.strip()) >= 5:
            target_clean = remove_accents(query.name.strip())
            best_match: Optional[CoderBase] = None
            best_ratio = 0.0

            for coder in self._coders_list:
                cand_clean = remove_accents(coder.full_name)
                # Comparación de ratio de caracteres
                ratio = SequenceMatcher(None, target_clean, cand_clean).ratio()

                # Comparación de palabras clave (tokens)
                target_tokens = set(target_clean.split())
                cand_tokens = set(cand_clean.split())
                intersection = target_tokens.intersection(cand_tokens)
                token_ratio = len(intersection) / max(len(target_tokens), len(cand_tokens))

                combined_score = max(ratio, token_ratio)

                if combined_score > best_ratio:
                    best_ratio = combined_score
                    best_match = coder

            # Umbral de aceptación para coincidencia de nombre: >= 82%
            if best_match and best_ratio >= 0.82:
                return CoderIdentificationResult(
                    coder_id=best_match.id,
                    identification_status="IDENTIFIED",
                    matched_by="FUZZY_NAME",
                    confidence=round(best_ratio, 2),
                    coder=best_match,
                    resolution_details=f"Identificado por similitud de nombre '{query.name}' ~ '{best_match.full_name}' (Confianza: {int(best_ratio * 100)}%)."
                )

        # 4. Cascada Nivel 4: Coder no encontrado (Fallback)
        return CoderIdentificationResult(
            coder_id=None,
            identification_status="CODER_NOT_FOUND",
            matched_by="NONE",
            confidence=0.0,
            coder=None,
            resolution_details="No se encontró ningún estudiante registrado que coincida con el correo, cédula o nombre provisto."
        )

    def resolve_from_normalized_email(self, email_norm: NormalizedEmail) -> CoderIdentificationResult:
        """
        Extrae los parámetros del correo normalizado para alimentar la cascada.
        """
        query = CoderIdentificationQuery(
            email=email_norm.sender_email,
            cedula=email_norm.preliminary_extraction.detected_cedula,
            name=email_norm.sender_name,
            clan=email_norm.preliminary_extraction.detected_clan
        )
        return self.identify_coder(query)


coder_resolver = CoderResolutionService()
