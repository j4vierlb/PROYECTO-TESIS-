# =============================================================================
# repositories/croquis.py — Consultas de croquis y dispositivos (trampas)
# (ver repositories/__init__.py para el patrón general de las consultas)
# =============================================================================

from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.engine import Connection


# ---------------------------------------------------------------------------
# Consultas relacionadas a croquis y dispositivos
# ---------------------------------------------------------------------------
# Parte común de las consultas de trampas: convierte la ubicación PostGIS
# en lat/lng, igual que en las visitas.
_DEVICE_SELECT = """
    SELECT id, croquis_id, codigo, tipo, sugerido_por_ia, confirmado, estado, foto_path,
           ST_Y(ubicacion::geometry) AS lat, ST_X(ubicacion::geometry) AS lng
    FROM dispositivos_trampa
"""


def fetch_croquis_for_visit(db: Connection, visit_id: UUID) -> dict[str, Any]:
    """Busca el croquis asociado a una visita. Si no tiene, responde 404."""
    row = db.execute(
        text(
            """
            SELECT id, visita_id, cliente_id, version, imagen_satelital_url,
                   sugerido_por_ia, validado_por_operador
            FROM croquis
            WHERE visita_id = :visita_id
            """
        ),
        {"visita_id": str(visit_id)},
    ).mappings().first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Croquis no encontrado")
    return dict(row)


def fetch_devices_for_croquis(db: Connection, croquis_id: UUID) -> list[dict[str, Any]]:
    """Todas las trampas de un croquis, ordenadas por su código (T-01, T-02...)."""
    rows = db.execute(
        text(_DEVICE_SELECT + " WHERE croquis_id = :croquis_id ORDER BY codigo"),
        {"croquis_id": str(croquis_id)},
    ).mappings().all()
    return [dict(row) for row in rows]


def fetch_device(db: Connection, device_id: UUID) -> dict[str, Any]:
    """Busca una trampa por su id. Si no existe, responde 404."""
    row = db.execute(text(_DEVICE_SELECT + " WHERE id = :id"), {"id": str(device_id)}).mappings().first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispositivo no encontrado")
    return dict(row)


def confirm_device(db: Connection, device_id: UUID) -> None:
    """Marca la trampa como confirmada por el operador en terreno."""
    db.execute(text("UPDATE dispositivos_trampa SET confirmado = TRUE WHERE id = :id"), {"id": str(device_id)})
    db.commit()


def move_device(db: Connection, device_id: UUID, lat: float, lng: float) -> None:
    """Cambia la ubicación de una trampa."""
    # ST_MakePoint crea un punto (ojo: primero longitud, después latitud).
    # ST_SetSRID(..., 4326) indica que son coordenadas GPS normales (WGS 84)
    # y ::geography lo convierte al tipo de la columna.
    db.execute(
        text(
            """
            UPDATE dispositivos_trampa
            SET ubicacion = ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography
            WHERE id = :id
            """
        ),
        {"id": str(device_id), "lat": lat, "lng": lng},
    )
    db.commit()


def remove_device(db: Connection, device_id: UUID) -> None:
    """No borra el registro: lo marca 'retirado' (soft delete), para
    conservar el historial del dispositivo."""
    db.execute(text("UPDATE dispositivos_trampa SET estado = 'retirado' WHERE id = :id"), {"id": str(device_id)})
    db.commit()


def save_client_location(db: Connection, cliente_id: UUID, lat: float, lng: float) -> None:
    """Guarda las coordenadas del cliente si todavía no tiene."""
    db.execute(
        text("""
            UPDATE clientes SET ubicacion = ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography
            WHERE id = :id AND ubicacion IS NULL
        """),
        {"id": str(cliente_id), "lat": lat, "lng": lng},
    )
    db.commit()


def fetch_device_context(db: Connection, device_id: UUID) -> dict[str, Any]:
    """Una trampa junto con los datos de la visita a la que pertenece su
    croquis (operador, estado y empresa). Sirve para decidir quién puede ver
    o modificar la trampa. Si la trampa no existe, responde 404."""
    row = db.execute(
        text(
            """
            SELECT d.id, d.croquis_id, d.foto_path,
                   v.id AS visita_id, v.operador_id, v.estado AS visita_estado, v.empresa_id
            FROM dispositivos_trampa d
            JOIN croquis c ON c.id = d.croquis_id
            LEFT JOIN visitas v ON v.id = c.visita_id
            WHERE d.id = :id
            """
        ),
        {"id": str(device_id)},
    ).mappings().first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispositivo no encontrado")
    return dict(row)


def create_croquis_for_visit(db: Connection, visit: dict[str, Any], operador_id: UUID) -> tuple[UUID, bool]:
    """Crea el croquis de una visita que todavía no tiene. Devuelve
    (id del croquis, True si se creó ahora / False si ya existía).

    Si el cliente ya tuvo un croquis en una visita anterior, el nuevo parte
    como una versión siguiente con sus trampas activas copiadas (mismo código,
    tipo, ubicación y foto), pero sin confirmar: el técnico debe revisarlas
    otra vez en terreno."""
    # FOR UPDATE bloquea la fila de la visita hasta el commit: si la app manda
    # dos peticiones a la vez, la segunda espera y encuentra el croquis creado.
    db.execute(text("SELECT id FROM visitas WHERE id = :id FOR UPDATE"), {"id": str(visit["id"])})
    existing = db.execute(
        text("SELECT id FROM croquis WHERE visita_id = :visita_id"), {"visita_id": str(visit["id"])}
    ).scalar()
    if existing is not None:
        db.commit()
        return existing, False

    # Croquis de la visita más reciente del mismo cliente anterior a esta.
    previous = db.execute(
        text(
            """
            SELECT c.id
            FROM croquis c
            JOIN visitas pv ON pv.id = c.visita_id
            WHERE c.cliente_id = :cliente_id AND pv.fecha_hora < :fecha_hora
            ORDER BY pv.fecha_hora DESC
            LIMIT 1
            """
        ),
        {"cliente_id": str(visit["cliente_id"]), "fecha_hora": visit["fecha_hora"]},
    ).mappings().first()
    # La versión sigue la numeración de todos los croquis del cliente.
    version = db.execute(
        text("SELECT COALESCE(MAX(version), 0) + 1 FROM croquis WHERE cliente_id = :cliente_id"),
        {"cliente_id": str(visit["cliente_id"])},
    ).scalar_one()

    croquis_id = db.execute(
        text(
            """
            INSERT INTO croquis (cliente_id, visita_id, operador_id, version, sugerido_por_ia, validado_por_operador)
            VALUES (:cliente_id, :visita_id, :operador_id, :version, FALSE, FALSE)
            RETURNING id
            """
        ),
        {
            "cliente_id": str(visit["cliente_id"]),
            "visita_id": str(visit["id"]),
            "operador_id": str(operador_id),
            "version": version,
        },
    ).scalar_one()

    if previous:
        db.execute(
            text(
                """
                INSERT INTO dispositivos_trampa
                    (croquis_id, codigo, tipo, ubicacion, sugerido_por_ia, confirmado, estado, foto_path)
                SELECT :nuevo, codigo, tipo, ubicacion, sugerido_por_ia, FALSE, estado, foto_path
                FROM dispositivos_trampa
                WHERE croquis_id = :anterior AND estado IN ('activo', 'revisar')
                """
            ),
            {"nuevo": str(croquis_id), "anterior": str(previous["id"])},
        )
    db.commit()
    return croquis_id, True


def add_device(
    db: Connection, croquis_id: UUID, tipo: str, lat: float, lng: float, device_id: UUID | None = None
) -> UUID | None:
    """Agrega una trampa instalada por el operador y le asigna el siguiente
    código libre del croquis (T-01, T-02...). Queda confirmada, porque la
    puso el propio técnico, y no sugerida por la IA.

    Si viene `device_id` (la app lo genera sin señal) la operación es
    idempotente: si esa trampa ya existe en este croquis se devuelve tal cual,
    sin duplicarla. Si el id ya lo usa un dispositivo de otro croquis, devuelve
    None y el endpoint responde 409."""
    # Bloquea el croquis para que dos trampas agregadas a la vez no reciban
    # el mismo código.
    db.execute(text("SELECT id FROM croquis WHERE id = :id FOR UPDATE"), {"id": str(croquis_id)})
    if device_id is not None:
        existing = db.execute(
            text("SELECT croquis_id FROM dispositivos_trampa WHERE id = :id"), {"id": str(device_id)}
        ).scalar_one_or_none()
        if existing is not None:
            db.commit()
            return device_id if str(existing) == str(croquis_id) else None
    # Mayor número entre los códigos con forma "T-<número>" (ignora otros).
    last = db.execute(
        text(
            """
            SELECT COALESCE(MAX(substring(codigo FROM '^T-([0-9]+)$')::int), 0)
            FROM dispositivos_trampa WHERE croquis_id = :croquis_id
            """
        ),
        {"croquis_id": str(croquis_id)},
    ).scalar_one()
    new_id = db.execute(
        text(
            """
            INSERT INTO dispositivos_trampa (id, croquis_id, codigo, tipo, ubicacion, sugerido_por_ia, confirmado, estado)
            VALUES (COALESCE(CAST(:id AS uuid), uuid_generate_v4()), :croquis_id, :codigo, :tipo,
                    ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography, FALSE, TRUE, 'activo')
            RETURNING id
            """
        ),
        {
            "id": str(device_id) if device_id is not None else None,
            "croquis_id": str(croquis_id),
            "codigo": f"T-{last + 1:02d}",
            "tipo": tipo,
            "lat": lat,
            "lng": lng,
        },
    ).scalar_one()
    db.commit()
    return new_id


def set_device_photo(db: Connection, device_id: UUID, foto_path: str) -> None:
    """Guarda el nombre del archivo de la foto de referencia de la trampa."""
    db.execute(
        text("UPDATE dispositivos_trampa SET foto_path = :foto_path WHERE id = :id"),
        {"id": str(device_id), "foto_path": foto_path},
    )
    db.commit()


def add_suggested_devices(
    db: Connection,
    croquis_id: UUID,
    imagen_satelital_url: str | None,
    devices: list[dict[str, Any]],
) -> None:
    """Agrega al croquis las trampas que propuso la IA (o el plan B), sin
    confirmar: el técnico las revisa en terreno. Marca el croquis como
    sugerido por IA y guarda la URL de la foto satelital (sin la clave)."""
    # Mismo bloqueo y numeración que add_device, para no repetir códigos.
    db.execute(text("SELECT id FROM croquis WHERE id = :id FOR UPDATE"), {"id": str(croquis_id)})
    last = db.execute(
        text(
            """
            SELECT COALESCE(MAX(substring(codigo FROM '^T-([0-9]+)$')::int), 0)
            FROM dispositivos_trampa WHERE croquis_id = :croquis_id
            """
        ),
        {"croquis_id": str(croquis_id)},
    ).scalar_one()
    for n, device in enumerate(devices, start=last + 1):
        db.execute(
            text(
                """
                INSERT INTO dispositivos_trampa (croquis_id, codigo, tipo, ubicacion, sugerido_por_ia, confirmado, estado)
                VALUES (:croquis_id, :codigo, :tipo, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography,
                        TRUE, FALSE, 'activo')
                """
            ),
            {"croquis_id": str(croquis_id), "codigo": f"T-{n:02d}", "tipo": device["tipo"],
             "lat": device["lat"], "lng": device["lng"]},
        )
    db.execute(
        text(
            """
            UPDATE croquis
            SET sugerido_por_ia = TRUE,
                imagen_satelital_url = COALESCE(:imagen, imagen_satelital_url)
            WHERE id = :id
            """
        ),
        {"id": str(croquis_id), "imagen": imagen_satelital_url},
    )
    db.commit()
