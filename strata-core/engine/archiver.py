"""
archiver.py
Módulo de compactación y archivado periódico de evidencias probatorias.
Email-Automation con Strata Core.

Misión:
Permite compactar lotes de evidencias o archivos temporales antiguos en archivos .zip
comprimidos con integridad verificada (CRC32), liberando hasta el 80% del espacio en disco
sin perder la capacidad de extraer y visualizar cualquier justificante bajo demanda.
"""

import os
import zipfile
import hashlib
import json
import time
from typing import List, Dict, Any, Optional


def _calculate_sha256(file_path: str) -> str:
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


class EvidenceArchiver:
    """Gestor de empaquetado y recuperación de evidencias en ZIPs indexados."""

    @staticmethod
    def archive_files(
        files: List[str],
        zip_output_path: str,
        delete_sources: bool = True
    ) -> Dict[str, Any]:
        """
        Empaqueta una lista de archivos en un archivo ZIP comprimido.
        Verifica la integridad de cada archivo mediante CRC32 y solo elimina
        las fuentes si el archivo comprimido es 100% válido.
        """
        os.makedirs(os.path.dirname(os.path.abspath(zip_output_path)), exist_ok=True)
        manifest: List[Dict[str, Any]] = []
        total_original_bytes = 0

        # Filtrar archivos existentes
        valid_files = [f for f in files if os.path.exists(f) and os.path.isfile(f)]
        if not valid_files:
            return {
                "success": False,
                "error": "No se encontraron archivos válidos para archivar.",
                "archived_count": 0,
                "saved_bytes": 0
            }

        with zipfile.ZipFile(zip_output_path, "w", compression=zipfile.ZIP_DEFLATED) as zipf:
            for fpath in valid_files:
                fname = os.path.basename(fpath)
                fsize = os.path.getsize(fpath)
                fsha = _calculate_sha256(fpath)
                total_original_bytes += fsize

                zipf.write(fpath, arcname=fname)
                manifest.append({
                    "filename": fname,
                    "original_path": fpath,
                    "size_bytes": fsize,
                    "sha256": fsha,
                    "archived_at": time.strftime("%Y-%m-%d %H:%M:%S")
                })

            # Incluir manifiesto indexado dentro del ZIP
            zipf.writestr("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False))

        # Test de integridad del ZIP
        with zipfile.ZipFile(zip_output_path, "r") as test_zip:
            bad_file = test_zip.testzip()
            if bad_file is not None:
                raise IOError(f"El archivo ZIP generado está corrupto en el elemento: {bad_file}")

        compressed_size = os.path.getsize(zip_output_path)
        saved_bytes = max(0, total_original_bytes - compressed_size)

        # Si se solicitó borrado y el ZIP pasó la prueba de integridad
        deleted_count = 0
        if delete_sources:
            for fpath in valid_files:
                try:
                    os.remove(fpath)
                    deleted_count += 1
                except OSError:
                    pass

        return {
            "success": True,
            "zip_path": zip_output_path,
            "archived_count": len(valid_files),
            "deleted_count": deleted_count,
            "original_bytes": total_original_bytes,
            "compressed_bytes": compressed_size,
            "saved_bytes": saved_bytes,
            "compression_ratio_pct": round((1 - (compressed_size / total_original_bytes)) * 100, 1) if total_original_bytes > 0 else 0.0,
            "manifest": manifest
        }

    @staticmethod
    def extract_file_from_archive(
        zip_path: str,
        filename_inside: str,
        target_dir: str
    ) -> Optional[str]:
        """Extrae un archivo específico de un ZIP archivado hacia un directorio destino."""
        if not os.path.exists(zip_path):
            return None

        os.makedirs(target_dir, exist_ok=True)
        with zipfile.ZipFile(zip_path, "r") as zipf:
            namelist = zipf.namelist()
            if filename_inside not in namelist:
                return None

            extracted_path = zipf.extract(filename_inside, path=target_dir)
            return extracted_path

    @staticmethod
    def list_archived_files(zip_path: str) -> List[Dict[str, Any]]:
        """Lee el manifiesto de un ZIP sin descomprimir los archivos."""
        if not os.path.exists(zip_path):
            return []

        try:
            with zipfile.ZipFile(zip_path, "r") as zipf:
                if "manifest.json" in zipf.namelist():
                    manifest_data = zipf.read("manifest.json").decode("utf-8")
                    return json.loads(manifest_data)
                return [{"filename": name} for name in zipf.namelist()]
        except Exception:
            return []
