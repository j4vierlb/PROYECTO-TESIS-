from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.security import ACCESS_TOKEN_MINUTES


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


class LoginRequest(BaseModel):
    usuario: str = Field(min_length=3)
    clave: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = ACCESS_TOKEN_MINUTES * 60


class ClientSummary(BaseModel):
    id: UUID
    nombre: str
    telefono_whatsapp: str
    direccion: str
    lat: float
    lng: float


class VisitResponse(BaseModel):
    id: UUID
    cliente: ClientSummary
    operador_id: UUID
    fecha_hora: datetime
    estado: VisitStatus
    origen_agendamiento: str
    notas: str | None = None


class VisitUpdate(BaseModel):
    """Body de PATCH /visitas/{id}. Todos los campos son opcionales: solo se
    actualiza lo que venga presente en el JSON (exclude_unset en el router)."""
    estado: VisitStatus | None = None
    notas: str | None = None


class DeviceResponse(BaseModel):
    id: UUID
    codigo: str
    tipo: str
    lat: float
    lng: float
    sugerido_por_ia: bool
    confirmado: bool
    estado: str


class CroquisResponse(BaseModel):
    id: UUID
    visita_id: UUID
    cliente_id: UUID
    version: int
    imagen_satelital_url: str | None = None
    sugerido_por_ia: bool
    validado_por_operador: bool
    dispositivos: list[DeviceResponse]


class DeviceUpdate(BaseModel):
    """- confirmar: no necesita lat/lng.
    - mover: obliga a mandar lat y lng (se valida abajo).
    - eliminar: solo marca el dispositivo como retirado, no lo borra."""
    accion: DeviceAction
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)

    @model_validator(mode="after")
    def validate_coordinates_for_move(self) -> "DeviceUpdate":
        if self.accion == DeviceAction.mover and (self.lat is None or self.lng is None):
            raise ValueError("lat y lng son obligatorios para mover el dispositivo")
        return self


class CurrentUser(BaseModel):
    """Usuario autenticado, resuelto a partir del JWT en cada request protegido."""
    id: UUID
    nombre: str
    rol: str
    empresa_id: UUID
