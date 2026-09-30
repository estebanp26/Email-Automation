"""
Módulo de Seguridad y Sanitización de Archivos Adjuntos (QA-01).

Implementa controles preventivos contra:
- Content-Type Spoofing (Inspección estricta de Magic Bytes).
- Path Traversal (Salto de Directorio y sanitización segura).
- Filtrado de firmas de Malware conocidas (EICAR, scripts, webshells).
- Protección DoS por exceso de tamaño de adjuntos.
"""

import re
import os
from typing import Optional, Tuple


class SecurityValidationException(Exception):
    """Excepción base para violaciones de seguridad en archivos adjuntos."""
    def __init__(self, message: str, code: str = "SECURITY_VIOLATION"):
        super().__init__(message)
        self.message = message
        self.code = code


class PathTraversalException(SecurityValidationException):
    """Se intentó manipular la ruta de almacenamiento con path traversal."""
    def __init__(self, message: str):
        super().__init__(message, code="PATH_TRAVERSAL_DETECTED")


class MalwareDetectedException(SecurityValidationException):
    """Se detectó una firma de malware o script potencialmente dañino."""
    def __init__(self, message: str):
        super().__init__(message, code="MALWARE_SIGNATURE_DETECTED")


class ContentSpoofingException(SecurityValidationException):
    """Los magic bytes reales del archivo difieren de la extensión o tipo declarado."""
    def __init__(self, message: str):
        super().__init__(message, code="CONTENT_SPOOFING_DETECTED")


class PayloadTooLargeException(SecurityValidationException):
    """El archivo adjunto excede el límite máximo de tamaño permitido."""
    def __init__(self, message: str):
        super().__init__(message, code="PAYLOAD_TOO_LARGE")


import base64

# Firma estándar antivirus EICAR (construida dinámicamente para prevenir falsos positivos de antivirus en disco)
EICAR_PARTIAL_MARKER = b"EICAR" + b"-STANDARD" + b"-ANTIVIRUS" + b"-TEST-FILE"
EICAR_STANDARD_SIGNATURE = base64.b64decode(b"WDVPIVAlQEFQWzRcUFpYNTQoUF4pN0NDKTd9JEVJQ0FSLVNUQU5EQVJELUFOVElWSVJVUy1URVNULUZJTEUhJEgrSCo=")

# Magic bytes de ejecutables o formatos explícitamente vetados
PROHIBITED_MAGIC_SIGNATURES = [
    (b"MZ", "Ejecutable Windows/DOS (MZ/PE)"),
    (b"\x7fELF", "Binario ejecutable Linux (ELF)"),
    (b"\xca\xfe\xba\xbe", "Bytecode Java / Class"),
    (b"\xfe\xed\xfa\xce", "Binario Mach-O"),
    (b"\xfe\xed\xfa\xcf", "Binario Mach-O 64-bit"),
    (b"\xce\xfa\xed\xfe", "Binario Mach-O reverse"),
    (b"\xcf\xfa\xed\xfe", "Binario Mach-O 64-bit reverse"),
    (b"#!", "Script ejecutable de Shell / Shebang"),
    (b"PK\x03\x04", "Archivo comprimido ZIP / JAR / APK (no permitido como soporte médico)"),
]

# Magic bytes de formatos permitidos
ALLOWED_MAGIC_BYTES = {
    ".pdf": b"%PDF-",
    ".png": b"\x89PNG\r\n\x1a\n",
    ".jpg": b"\xff\xd8\xff",
    ".jpeg": b"\xff\xd8\xff",
}


class FileSecurityValidator:
    """Validador centralizado de seguridad e integridad para archivos adjuntos."""

    @staticmethod
    def validate_and_sanitize_filename(filename: str) -> str:
        """
        Valida que el nombre de archivo no contenga intentos de Path Traversal
        y retorna una versión saneada y segura.
        """
        if not filename or not filename.strip():
            raise PathTraversalException("El nombre del archivo adjunto no puede estar vacío.")

        raw_name = filename.strip()

        # 1. Detección estricta de secuencias de path traversal
        traversal_patterns = [
            r"\.\.",               # Salto hacia directorio padre
            r"[/\\]",              # Separadores de directorio unix o windows
            r"\x00",               # Null bytes
            r"%2e%2e",             # URL encoded ..
            r"%2f|%5c",            # URL encoded / o \
        ]
        for pattern in traversal_patterns:
            if re.search(pattern, raw_name, flags=re.IGNORECASE):
                raise PathTraversalException(
                    f"Intento de salto de directorio (Path Traversal) detectado en el nombre del archivo: '{filename}'."
                )

        # 2. Sanitización estricta (secure_filename)
        # Extraer solo la parte base
        base = os.path.basename(raw_name)
        # Reemplazar espacios por guiones bajos
        base = re.sub(r"\s+", "_", base)
        # Mantener solo caracteres alfanuméricos, puntos, guiones y guiones bajos
        sanitized = re.sub(r"[^a-zA-Z0-9_.-]", "", base)
        # Eliminar puntos iniciales repetidos para evitar archivos ocultos
        sanitized = sanitized.lstrip(".")

        if not sanitized or "." not in sanitized:
            raise PathTraversalException(
                f"Nombre de archivo inválido o sin extensión tras sanitización: '{filename}'."
            )

        return sanitized

    @staticmethod
    def scan_malware_signatures(data: bytes, filename: str = "") -> None:
        """
        Escanea los bytes del archivo en busca de firmas de malware estándar (EICAR)
        o scripts ejecutables maliciosos incrustados.
        """
        if not data:
            return

        # 1. Comprobación EICAR (completo o fragmento canónico)
        if EICAR_PARTIAL_MARKER in data or EICAR_STANDARD_SIGNATURE in data:
            raise MalwareDetectedException(
                f"Firma de malware detectada en el archivo '{filename}': Archivo de prueba estándar EICAR."
            )

        # 2. Detección de webshells o scripts embebidos en archivos no de texto
        dangerous_script_tags = [
            b"<?php",
            b"<script",
            b"eval(",
            b"system(",
            b"passthru(",
            b"shell_exec(",
            b"cmd.exe",
            b"/bin/sh",
            b"/bin/bash",
        ]
        # Si el payload es muy grande, inspeccionar solo los primeros 4KB y últimos 4KB para scripts
        sample = data[:4096] + (data[-4096:] if len(data) > 4096 else b"")
        sample_lower = sample.lower()
        for tag in dangerous_script_tags:
            if tag in sample_lower:
                raise MalwareDetectedException(
                    f"Código malicioso o script no autorizado detectado en el archivo '{filename}': patrón '{tag.decode('latin1')}'."
                )

    @staticmethod
    def validate_magic_bytes(filename: str, declared_mime: Optional[str], data: bytes) -> str:
        """
        Inspecciona los magic bytes del archivo binario decodificado.
        Garantiza que no sea un ejecutable y que la cabecera real coincida
        con el tipo de soporte médico permitido (PDF o imágenes).
        Retorna el MIME type verificado.
        """
        if not data:
            raise ContentSpoofingException(f"El archivo '{filename}' está vacío (0 bytes).")

        # 1. Bloqueo inmediato de firmas de ejecutables conocidos
        for sig, description in PROHIBITED_MAGIC_SIGNATURES:
            if data.startswith(sig):
                raise ContentSpoofingException(
                    f"Falsificación o archivo peligroso detectado en '{filename}': Contiene cabecera de {description}."
                )

        # 2. Inspeccionar extensión declarada
        _, ext = os.path.splitext(filename.lower())
        if ext not in [".pdf", ".png", ".jpg", ".jpeg", ".webp"]:
            raise ContentSpoofingException(
                f"Extensión no permitida '{ext}' en archivo '{filename}'. Formatos admitidos: .pdf, .png, .jpg, .jpeg, .webp."
            )

        # 3. Validación de Magic Bytes por formato
        verified_mime = "application/octet-stream"

        if ext == ".pdf":
            # PDF debe comenzar con '%PDF-'
            # Nota: Según la especificación PDF-1.7, el encabezado %PDF- debe estar en los primeros 1024 bytes
            header_sample = data[:1024]
            if not header_sample.startswith(b"%PDF-") and b"%PDF-" not in header_sample:
                raise ContentSpoofingException(
                    f"Falsificación de tipo MIME: El archivo '{filename}' tiene extensión .pdf pero carece de la cabecera mágica '%PDF-'."
                )
            verified_mime = "application/pdf"

        elif ext == ".png":
            # PNG debe comenzar exactamente con \x89PNG\r\n\x1a\n
            if not data.startswith(ALLOWED_MAGIC_BYTES[".png"]):
                raise ContentSpoofingException(
                    f"Falsificación de tipo MIME: El archivo '{filename}' no es una imagen PNG válida (cabecera corrupta o falsificada)."
                )
            verified_mime = "image/png"

        elif ext in [".jpg", ".jpeg"]:
            # JPEG debe comenzar con \xff\xd8\xff
            if not data.startswith(b"\xff\xd8\xff"):
                raise ContentSpoofingException(
                    f"Falsificación de tipo MIME: El archivo '{filename}' no es una imagen JPEG válida (cabecera corrupta o falsificada)."
                )
            verified_mime = "image/jpeg"

        elif ext == ".webp":
            # WEBP: RIFF....WEBP (bytes 0-4 == RIFF, bytes 8-12 == WEBP)
            if len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"WEBP":
                raise ContentSpoofingException(
                    f"Falsificación de tipo MIME: El archivo '{filename}' no es una imagen WEBP válida (cabecera corrupta o falsificada)."
                )
            verified_mime = "image/webp"

        return verified_mime

    @staticmethod
    def validate_attachment_size(byte_len: int, max_bytes: int = 15 * 1024 * 1024, filename: str = "") -> None:
        """
        Valida que el archivo decodificado no supere el tamaño máximo permitido.
        """
        if byte_len > max_bytes:
            max_mb = max_bytes // (1024 * 1024)
            actual_mb = round(byte_len / (1024 * 1024), 2)
            raise PayloadTooLargeException(
                f"El archivo '{filename}' excede el límite máximo permitido de {max_mb}MB (Tamaño actual: {actual_mb}MB)."
            )
