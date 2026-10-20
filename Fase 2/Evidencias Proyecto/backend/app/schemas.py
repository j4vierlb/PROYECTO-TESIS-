# =============================================================================
# schemas.py — Forma de los datos que entran y salen de la API
# -----------------------------------------------------------------------------
# Cada clase describe un JSON: qué campos tiene y de qué tipo es cada uno.
# FastAPI usa estas clases (modelos de Pydantic) para tres cosas:
#   1. Validar lo que llega: si falta un campo o viene mal, responde 422 solo.
#   2. Armar la respuesta: solo se envían los campos declarados aquí.
#   3. Generar la documentación de /docs automáticamente.
# Los nombres van en snake_case (fecha_hora, operador_id), como se acordó.
# =============================================================================

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

from app.security import ACCESS_TOKEN_MINUTES


# ---------------------------------------------------------------------------
# Valores fijos permitidos (Enums)
# ---------------------------------------------------------------------------
# Equivalen a la restricción CHECK de la tabla visitas en schema.sql: si llega
# un estado que no está en esta lista, la API lo rechaza antes de tocar la base.
class VisitStatus(str, Enum):
    agendada = "agendada"
    en_curso = "en_curso"
    completada = "completada"
    cancelada = "cancelada"
    reagendada = "reagendada"


class DeviceAction(str, Enum):
    """Acciones que un operador puede aplicar sobre un dispositivo trampa
    desde el PATCH /dispositivos-trampa/{id}."""
    confirmar = "confirmar"
    mover = "mover"
    eliminar = "eliminar"


class DeviceType(str, Enum):
    """Tipos de trampa: los mismos del CHECK de dispositivos_trampa."""
    cebadero = "cebadero"
    trampa_pegamento = "trampa_pegamento"
    trampa_luz = "trampa_luz"
    otro = "otro"


# ---------------------------------------------------------------------------
# Autenticación
# ---------------------------------------------------------------------------
class LoginRequest(BaseModel):
    """Lo que la app manda a POST /auth/login."""
    usuario: str = Field(min_length=3)  # el email del operador o del admin
    clave: str = Field(min_length=1)


class TokenResponse(BaseModel):
    """Lo que devuelve un login exitoso."""
    access_token: str       # pase de sesión corto (8 h), se manda en cada request
    refresh_token: str      # pase largo (30 días), para renovar el anterior
    token_type: str = "bearer"
    expires_in: int = ACCESS_TOKEN_MINUTES * 60  # duración del access_token en segundos


# ---------------------------------------------------------------------------
# Visitas
# ---------------------------------------------------------------------------
class ClientSummary(BaseModel):
    """Datos del cliente que van dentro de cada visita."""
    id: UUID
    nombre: str
    telefono_whatsapp: str
    # Dirección y coordenadas pueden venir vacías (null): un cliente que llega
    # por WhatsApp se registra solo con su teléfono, antes de dar su dirección,
    # y nunca trae coordenadas. Exigirlas hacía que la agenda y el panel
    # respondieran error 500 apenas existía uno de esos clientes.
    direccion: str | None = None
    # Coordenadas sueltas (no GeoJSON), como se acordó en el formato de la API.
    lat: float | None = None
    lng: float | None = None


class VisitResponse(BaseModel):
    """Una visita tal como la ve la app (agenda y detalle)."""
    id: UUID
    cliente: ClientSummary
    operador_id: UUID | None = None
    fecha_hora: datetime  # se envía en ISO 8601 UTC, ej: "2026-09-24T10:00:00Z"
    estado: VisitStatus
    origen_agendamiento: str  # "whatsapp_ia" o "manual"
    notas: str | None = None  # `| None` = el campo puede venir vacío (null)


class VisitHistoryItem(VisitResponse):
    """Visita del historial: incluye cuántas trampas quedaron instaladas
    (las no retiradas) en su croquis."""
    # Hereda todos los campos de VisitResponse y agrega este.
    dispositivos_instalados: int


class VisitUpdate(BaseModel):
    """Body de PATCH /visitas/{id}. Todos los campos son opcionales: solo se
    actualiza lo que venga presente en el JSON (exclude_unset en el router)."""
    estado: VisitStatus | None = None
    notas: str | None = None


class ClientCreate(BaseModel):
    nombre: str = Field(min_length=2, max_length=150)
    telefono_whatsapp: str = Field(min_length=5, max_length=30)
    direccion: str = Field(min_length=2)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)

    @model_validator(mode="after")
    def complete_location(self):
        if (self.lat is None) != (self.lng is None):
            raise ValueError("Completa ambas coordenadas o deja ambas vacías")
        return self

    @field_validator("nombre", "telefono_whatsapp", "direccion", mode="before")
    @classmethod
    def trim_text(cls, value):
        return value.strip() if isinstance(value, str) else value


class ClientUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=150)
    telefono_whatsapp: str | None = Field(default=None, min_length=5, max_length=30)
    direccion: str | None = Field(default=None, min_length=2)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)

    @field_validator("nombre", "telefono_whatsapp", mode="before")
    @classmethod
    def nonempty_text(cls, value):
        if value is None:
            raise ValueError("El nombre y el teléfono no pueden quedar vacíos")
        return value.strip() if isinstance(value, str) else value


class OperatorSummary(BaseModel):
    id: UUID
    nombre: str
    email: str | None = None


class VisitCreate(BaseModel):
    cliente_id: UUID
    operador_id: UUID | None = None
    fecha_hora: AwareDatetime
    notas: str | None = None


class PanelVisitUpdate(VisitUpdate):
    """Edición administrativa; no amplía el PATCH de la aplicación móvil."""

    model_config = ConfigDict(extra="forbid")
    operador_id: UUID | None = None
    fecha_hora: AwareDatetime | None = None

    @field_validator("fecha_hora", "estado")
    @classmethod
    def required_when_present(cls, value):
        if value is None:
            raise ValueError("La fecha y el estado no pueden quedar vacíos")
        return value


class PanelVisitResponse(VisitResponse):
    operador: OperatorSummary | None = None


class PanelStats(BaseModel):
    clientes: int
    visitas_hoy: int
    pendientes: int

# ---------------------------------------------------------------------------
# Croquis y dispositivos trampa
# ---------------------------------------------------------------------------
class DeviceResponse(BaseModel):
    """Una trampa (cebadero, trampa de pegamento, etc.) dentro de un croquis."""
    id: UUID
    codigo: str            # etiqueta física, ej: "T-01"
    tipo: str              # cebadero, trampa_pegamento, trampa_luz u otro
    lat: float
    lng: float
    sugerido_por_ia: bool  # True si la ubicación la propuso la IA
    confirmado: bool       # True si el operador la validó en terreno
    estado: str            # activo, retirado o revisar
    # Dirección (relativa al backend) para ver la foto de referencia de la
    # trampa, o null si no tiene. Se pide con el mismo token de la sesión.
    foto_url: str | None = None

    @classmethod
    def from_row(cls, row: dict) -> "DeviceResponse":
        """Convierte una fila de dispositivos_trampa (con lat/lng) en la
        respuesta de la API. `?v=` cambia cuando se sube otra foto, para que
        la app no muestre la anterior guardada en su caché."""
        foto_path = row.get("foto_path")
        return cls(
            id=row["id"],
            codigo=row["codigo"],
            tipo=row["tipo"],
            lat=row["lat"],
            lng=row["lng"],
            sugerido_por_ia=row["sugerido_por_ia"],
            confirmado=row["confirmado"],
            estado=row["estado"],
            foto_url=f"/dispositivos-trampa/{row['id']}/foto?v={foto_path[:8]}" if foto_path else None,
        )


class CroquisResponse(BaseModel):
    """El plano de una visita con la lista de sus trampas."""
    id: UUID
    visita_id: UUID
    cliente_id: UUID
    version: int
    imagen_satelital_url: str | None = None
    sugerido_por_ia: bool
    validado_por_operador: bool
    dispositivos: list[DeviceResponse]


class DeviceCreate(BaseModel):
    """Body de POST /croquis/{visita_id}/dispositivos: una trampa que el
    operador instala en terreno. El código (T-01, T-02...) lo asigna el
    backend, para que nunca se repita dentro del croquis."""
    tipo: DeviceType
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class DeviceUpdate(BaseModel):
    """- confirmar: no necesita lat/lng.
    - mover: obliga a mandar lat y lng (se valida abajo).
    - eliminar: solo marca el dispositivo como retirado, no lo borra."""
    accion: DeviceAction
    # ge/le = "mayor o igual" / "menor o igual": rango válido de coordenadas
    # en la Tierra. Una latitud de 500 se rechaza automáticamente.
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)

    # Validación que depende de dos campos a la vez: se ejecuta después de
    # validar cada campo por separado (mode="after").
    @model_validator(mode="after")
    def validate_coordinates_for_move(self) -> "DeviceUpdate":
        if self.accion == DeviceAction.mover and (self.lat is None or self.lng is None):
            raise ValueError("lat y lng son obligatorios para mover el dispositivo")
        return self


# ---------------------------------------------------------------------------
# Usuario de la sesión
# ---------------------------------------------------------------------------
class CurrentUser(BaseModel):
    """Usuario autenticado, resuelto a partir del JWT en cada request protegido."""
    id: UUID
    nombre: str
    rol: str  # "operador", "admin" o "coordinador"
    empresa_id: UUID
