# =============================================================================
# zona_horaria.py — Qué día es "hoy" para la empresa
# -----------------------------------------------------------------------------
# Las fechas se GUARDAN y se ENVÍAN en UTC (decisión de formato de la API),
# pero "hoy" es el día de Chile: la empresa opera en Macul. Si "hoy" se
# calculara en UTC, desde las 21:00 (o 20:00 en invierno) hora de Chile ya
# sería "mañana" en UTC, y la agenda mostraría las visitas del día siguiente.
#
# ZoneInfo("America/Santiago") incluye el cambio de horario de verano/invierno
# (UTC-3 / UTC-4), así que no hay que ajustar nada a mano cuando cambia.
# =============================================================================

from datetime import date, datetime

from zoneinfo import ZoneInfo

ZONA_CHILE = ZoneInfo("America/Santiago")

# Nombre de la zona para las consultas SQL (AT TIME ZONE 'America/Santiago').
ZONA_CHILE_SQL = "America/Santiago"


def ahora_chile() -> datetime:
    """Fecha y hora actual en Chile. Es una función aparte para que las
    pruebas puedan reemplazarla por una hora fija (ej: 22:30)."""
    return datetime.now(ZONA_CHILE)


def hoy_chile(ahora: datetime | None = None) -> date:
    """El día de hoy según Chile. Si se pasa `ahora` (con zona horaria), se
    calcula para ese instante; si no, para el momento actual."""
    instante = ahora if ahora is not None else ahora_chile()
    return instante.astimezone(ZONA_CHILE).date()
