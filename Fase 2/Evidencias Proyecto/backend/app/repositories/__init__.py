# =============================================================================
# repositories/ — Todas las consultas a la base de datos
# -----------------------------------------------------------------------------
# Aquí vive todo el SQL del backend. Los routers (la capa de endpoints) nunca
# escriben SQL directamente: llaman a estas funciones. Así, si cambia una
# tabla, solo hay que tocar este archivo.
#
# Seguridad: los valores siempre van como parámetros con nombre (:id, :email)
# y nunca pegados dentro del texto del SQL. SQLAlchemy los envía por separado
# a PostgreSQL, lo que evita ataques de "inyección SQL".
#
# Patrón que se repite en casi todas las funciones:
#   db.execute(text("SQL..."), {"parametro": valor})  -> ejecuta la consulta
#   .mappings()                                        -> filas como diccionarios
#   .first() / .all()                                  -> una fila / todas
#   db.commit()                                        -> confirma un cambio (UPDATE)
# =============================================================================

# El código antes vivía en un solo archivo repositories.py. Se dividió por tema,
# pero aquí se reexporta todo: los routers siguen importando igual
# (from app.repositories import fetch_visit).
#   visitas.py       visitas del técnico (agenda, historial, edición)
#   croquis.py       croquis y dispositivos (trampas)
#   auth.py          cuentas de técnicos y de usuarios del panel
#   whatsapp.py      clientes, conversaciones, mensajes y recordatorios
#   agendamiento.py  horarios, técnicos y creación de la visita pedida por la IA
#   _comun.py        constantes compartidas (zona horaria, margen entre visitas)

from app.repositories.visitas import (  # noqa: F401
    _VISIT_SELECT,
    fetch_visit,
    fetch_visits_for_today,
    fetch_upcoming_visits,
    fetch_visit_history,
    update_visit_fields,
)
from app.repositories.croquis import (  # noqa: F401
    _DEVICE_SELECT,
    fetch_croquis_for_visit,
    fetch_devices_for_croquis,
    fetch_device,
    confirm_device,
    move_device,
    remove_device,
    save_client_location,
    fetch_device_context,
    create_croquis_for_visit,
    add_device,
    set_device_photo,
    add_suggested_devices,
)
from app.repositories.auth import (  # noqa: F401
    fetch_operator_by_email,
    fetch_web_user_by_email,
    fetch_operator_by_id,
    fetch_web_user_by_id,
)
from app.repositories.whatsapp import (  # noqa: F401
    normalize_phone,
    fetch_or_create_whatsapp_client,
    count_client_visits,
    update_whatsapp_client_name,
    update_whatsapp_client_address,
    fetch_active_whatsapp_conversation,
    whatsapp_message_exists,
    insert_whatsapp_message,
    fetch_whatsapp_history,
    DELIVERY_RANK,
    _DELIVERY_RANK_SQL,
    update_whatsapp_delivery,
    fetch_whatsapp_client,
    client_wrote_since,
    _CONVERSATION_SELECT,
    list_whatsapp_conversations,
    fetch_whatsapp_conversation,
    fetch_conversation_messages,
    set_conversation_human,
    claim_visits_for_reminder,
    release_reminder_claim,
)
from app.repositories.agendamiento import (  # noqa: F401
    HorarioNoDisponible,
    _is_within_business_hours,
    _configured_operator_id,
    _find_available_operator,
    _find_next_available_slot,
    create_whatsapp_visit,
)
from app.repositories._comun import (  # noqa: F401
    SANTIAGO,
    UTC,
    VISIT_MARGIN,
    SUGGESTION_SEARCH_DAYS,
    _ACTIVE_VISIT_STATES,
)
