# =============================================================================
# repositories/_comun.py — Constantes compartidas por los repositorios
# =============================================================================
from datetime import timedelta, timezone
from zoneinfo import ZoneInfo

SANTIAGO = ZoneInfo("America/Santiago")
UTC = timezone.utc
# Dos visitas del mismo operador deben estar separadas por al menos 1 hora.
VISIT_MARGIN = timedelta(hours=1)
# Hasta cuántos días hacia adelante se busca un horario alternativo.
SUGGESTION_SEARCH_DAYS = 7
# Solo estos estados "ocupan" al operador (una visita cancelada no).
_ACTIVE_VISIT_STATES = "('agendada', 'reagendada')"
