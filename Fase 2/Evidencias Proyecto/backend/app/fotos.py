# =============================================================================
# fotos.py — Guardar y leer las fotos de referencia de las trampas
# -----------------------------------------------------------------------------
# Las fotos se guardan como archivos en settings.upload_dir (en Docker, el
# volumen /app/uploads), y en la base solo queda el nombre del archivo.
#
# Seguridad:
#   - Se revisan los primeros bytes del archivo ("firma"), no el nombre ni el
#     tipo que dice el teléfono, que se pueden falsificar. Solo JPEG o PNG.
#   - El nombre del archivo lo genera el servidor (un UUID), nunca el usuario,
#     así nadie puede escribir fuera de la carpeta con un nombre como "../x".
#   - Tamaño máximo: settings.max_photo_bytes.
# =============================================================================

import re
import uuid
from pathlib import Path
from typing import BinaryIO

from fastapi import HTTPException, status

from app.config import settings

# Firma de cada formato aceptado -> (extensión, tipo MIME).
_SIGNATURES = {
    b"\xff\xd8\xff": ("jpg", "image/jpeg"),
    b"\x89PNG\r\n\x1a\n": ("png", "image/png"),
}
# Única forma válida de un nombre guardado en la base: UUID + extensión.
_NOMBRE_VALIDO = re.compile(r"^[0-9a-f]{32}\.(jpg|png)$")


def _upload_dir() -> Path:
    path = Path(settings.upload_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def guardar_foto(archivo: BinaryIO) -> str:
    """Valida la foto y la guarda con un nombre nuevo. Devuelve ese nombre.

    Responde 413 si pesa más del máximo y 415 si no es JPEG ni PNG."""
    # Se lee un byte más que el máximo para saber si se pasó, sin leer el
    # archivo completo si es gigante.
    contenido = archivo.read(settings.max_photo_bytes + 1)
    if len(contenido) > settings.max_photo_bytes:
        limite_mb = settings.max_photo_bytes // (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"La foto pesa más de {limite_mb} MB",
        )
    for firma, (extension, _) in _SIGNATURES.items():
        if contenido.startswith(firma):
            break
    else:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="La foto debe ser una imagen JPEG o PNG",
        )

    nombre = f"{uuid.uuid4().hex}.{extension}"
    destino = _upload_dir() / nombre
    # Se escribe primero en un archivo temporal y se renombra al final: así
    # nunca queda una foto a medio escribir con el nombre definitivo.
    temporal = destino.with_suffix(".tmp")
    temporal.write_bytes(contenido)
    temporal.replace(destino)
    return nombre


def ruta_foto(nombre: str) -> tuple[Path, str]:
    """Ruta en disco y tipo MIME de una foto guardada. Responde 404 si el
    nombre no tiene la forma esperada o el archivo ya no existe."""
    if not _NOMBRE_VALIDO.match(nombre or ""):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Foto no encontrada")
    path = _upload_dir() / nombre
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Foto no encontrada")
    media_type = "image/png" if nombre.endswith(".png") else "image/jpeg"
    return path, media_type
