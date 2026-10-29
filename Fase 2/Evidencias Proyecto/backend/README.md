# Backend Kill Bichos IA

API FastAPI conectada a PostgreSQL + PostGIS (carpeta `../database/`).

## Ubicación de clientes por dirección — panel web

`POST /clientes` calcula la ubicación si no recibe coordenadas. Usa el servicio
existente `app/geocoding.py`, con `GOOGLE_MAPS_API_KEY` configurada en el `.env`
raíz al ejecutar Docker. La clave debe autorizar Geocoding API y nunca llevar
el prefijo `VITE_` ni enviarse al navegador.

`PATCH /clientes/{id}` recalcula al cambiar la dirección o al volver a guardar
una dirección todavía sin ubicación. Si falla, deja `ubicacion` en NULL: no
conserva coordenadas de una dirección anterior. Borrar la dirección también
borra su punto. La edición se serializa por cliente con `FOR UPDATE`; la
consulta externa conserva el timeout de 5 segundos del servicio existente.

Se aceptan direcciones de todo Chile: el resultado debe pertenecer a Chile y
la comuna o ciudad encontrada debe aparecer en la dirección escrita. Se conservan
el descarte de coincidencias parciales, ambiguas o aproximadas y el aislamiento
por empresa. El fallo de
Google no impide guardar el cliente. El panel interpreta `lat/lng` nulos como
ubicación pendiente y explica cómo reintentar. Una dirección sin cambios y con
punto válido no genera una nueva consulta; editar solo nombre/teléfono tampoco.

Por compatibilidad, enviar coordenadas explícitas continúa siendo válido y
prioritario, incluida la limpieza explícita con ambos valores nulos en PATCH.
El formulario nuevo solo envía nombre, teléfono y dirección. No se altera el
contrato móvil ni la lógica de las trampas, ni se necesita una migración para
esta mejora. Las migraciones pendientes de WhatsApp/recuperación corresponden
a sus entregas anteriores y deben aplicarse antes de desplegar todo el código.

## Instalación y ejecución

**Con Docker (recomendado):** desde la raíz del repo, `docker compose up --build` levanta la base, este backend y el panel web. Ver el `README.md` de la raíz.

**Sin Docker, para desarrollar el backend** (con recarga automática al editar):

1. Levanta solo la base de datos, desde la raíz del repo:
   ```bash
   docker compose up -d db
   ```
2. Instala y corre el backend:
   ```bash
   cd "Fase 2/Evidencias Proyecto/backend"
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env
   uvicorn app.main:app --reload
   ```

Swagger queda disponible en <http://127.0.0.1:8000/docs>.

## Recuperación de contraseña del panel

El login web incluye **Olvidé mi contraseña** para administradores/coordinadores.
Requiere configurar SMTP y aplicar `../database/migracion_password_reset.sql`
**antes de desplegar este backend**, incluso si el envío sigue deshabilitado.
Ver [configuración, endpoints, seguridad y despliegue](docs/recuperacion_password_panel.md).
Deshabilitado por defecto: no envía correos ni cambia claves sin configuración.

## Credenciales de prueba (seed.sql)

- Operador: `tecnico1@killbichos.cl` / `demo1234`
- Administrador: `admin@killbichos.cl` / `demo1234`

El login recibe JSON con `usuario` y `clave`, y entrega un `access_token` de 8 horas y un `refresh_token` de 30 días.

`POST /auth/refresh` recibe `{"refresh_token": "..."}` y entrega un par nuevo de tokens, sin pedir la clave. Responde 401 si el token es falso, venció, es un `access_token` o la cuenta fue desactivada. La app lo usa para no pedir el login cada vez que se abre: mientras el técnico la use al menos una vez cada 30 días, no vuelve a escribir su clave.

## Fechas y zona horaria

Las fechas se guardan y se envían en **UTC** (ISO 8601), pero **"hoy" es el día de Chile** (`America/Santiago`): la agenda del técnico y la del panel comparan cada visita convertida a la hora de Chile. Si se calculara en UTC, desde las 21:00 hora de Chile (20:00 en invierno) la agenda mostraría las visitas del día siguiente. El cálculo está en `app/zona_horaria.py`. El paquete `tzdata` (en `requirements.txt`) asegura los datos de zonas horarias aunque el sistema no los traiga, como en Windows o en imágenes de Docker mínimas.

## Croquis en terreno (trampas y fotos)

| Endpoint | Quién | Qué hace |
|---|---|---|
| `GET /croquis/{visita_id}` | operador de la visita o panel | El croquis con sus trampas; cada trampa trae `foto_url` (o `null`) |
| `POST /croquis/{visita_id}` | operador de la visita | Crea el croquis si no existe (201) o devuelve el que ya hay (200). Copia, sin confirmar, las trampas activas de la visita anterior del mismo cliente |
| `POST /croquis/{visita_id}/dispositivos` | operador de la visita | Agrega una trampa instalada en terreno: `{"tipo": "cebadero", "lat": -33.48, "lng": -70.59}`. El código (T-01, T-02...) lo asigna el backend |
| `PATCH /dispositivos-trampa/{id}` | operador de la visita | Confirmar, mover o retirar |
| `POST /dispositivos-trampa/{id}/foto` | operador de la visita | Sube la foto (campo `foto`, multipart). Solo JPEG o PNG (se revisan los bytes), máximo 5 MB |
| `GET /dispositivos-trampa/{id}/foto` | operador de la visita o panel de la misma empresa | Descarga la foto. No es pública: requiere el token |

Si la visita está **completada o cancelada**, todo lo que modifica el croquis responde **409**: queda solo de consulta. Las fotos se guardan en `UPLOAD_DIR` (en Docker, el volumen `uploads_data` montado en `/app/uploads`), y en la base solo queda el nombre del archivo.

## Pruebas

Desde esta carpeta. Las unitarias no necesitan base de datos:

```bash
python -m unittest discover tests
```

Las de integración usan PostgreSQL/PostGIS real en una base **aislada** y se saltan si no se indica la variable. Nunca usar la base de trabajo: cada prueba se deshace al final, pero igual exigen un nombre de base fijo:

```bash
# Croquis en terreno: base croquis_regression con schema.sql + migracion_croquis_terreno.sql
CROQUIS_TEST_DATABASE_URL=postgresql+psycopg://usuario:clave@127.0.0.1:15434/croquis_regression python -m unittest discover tests
# Panel web: base panel_regression (ver ../pruebas/Panel_regresion_2026-10-09.md)
PANEL_TEST_DATABASE_URL=postgresql+psycopg://usuario:clave@127.0.0.1:15432/panel_regression python -m unittest discover tests
```

## Estructura

```
app/
├── main.py          # crea la app FastAPI, monta los routers y el CORS
├── config.py        # variables de entorno (.env)
├── database.py       # engine de SQLAlchemy y la dependencia get_db
├── security.py        # hashing de contraseñas (passlib/bcrypt) y JWT
├── schemas.py          # modelos Pydantic (request/response)
├── dependencies.py      # auth: get_current_user, require_operator
├── repositories.py       # consultas SQL a Postgres/PostGIS
├── geocoding.py          # dirección → lat/lng (Google Geocoding API)
├── fotos.py              # guardar/leer fotos de trampas (validación de imagen y tamaño)
├── whatsapp_saliente.py  # avisos, recordatorios y mensajes del operador (API REST de Twilio)
├── ai/
│   ├── agent.py          # agente conversacional (OpenAI) para WhatsApp
│   └── croquis_agent.py  # sugerencia de trampas con la foto satelital
└── routers/
    ├── auth.py
    ├── panel.py       # CRUD de clientes, agenda y operadores del panel web
    ├── visitas.py
    ├── croquis.py        # ver y crear croquis, agregar trampas y POST /croquis/{id}/sugerencia (IA)
    ├── dispositivos.py   # confirmar/mover/retirar trampas y sus fotos
    ├── whatsapp.py       # webhooks de Twilio: mensajes entrantes y estado de entrega
    └── conversaciones.py # bandeja de WhatsApp del panel y recordatorios manuales
```

## Panel web

El frontend está en `../frontend/` y consume los endpoints protegidos del panel:

- `GET /panel/stats`, `GET /panel/operadores`
- `GET/POST /clientes`, `PATCH/DELETE /clientes/{id}`
- `GET/POST /panel/visitas`, `PATCH/DELETE /panel/visitas/{id}` (el `PATCH` también acepta `fecha_hora` y `operador_id` para reagendar)
- `GET /panel/conversaciones`, `GET/PATCH /panel/conversaciones/{id}`, `POST /panel/conversaciones/{id}/mensajes`
- `POST /panel/whatsapp/recordatorios`

El acceso está limitado a usuarios con rol `admin` o `coordinador`; todas las consultas
se filtran por `empresa_id` para mantener el aislamiento del tenant.

Las coordenadas se guardan en PostgreSQL como `GEOGRAPHY(Point, 4326)` (PostGIS) y se convierten a `lat`/`lng` sueltos en las respuestas de la API con `ST_Y`/`ST_X`.

## Agente de WhatsApp + IA

`POST /webhooks/whatsapp` recibe los mensajes que los clientes escriben al WhatsApp de la empresa (vía Twilio), guarda la conversación y usa OpenAI para responder o agendar una visita. Requiere Python 3.11 o superior.

### Qué hace al agendar

- La IA devuelve la fecha en ISO 8601 con zona horaria. El backend valida que tenga zona horaria, que esté en el futuro y a no más de 60 días, y la guarda en UTC.
- A un cliente nuevo se le pide la dirección antes de agendar; se guarda en `clientes.direccion` (la ubicación `lat`/`lng` queda vacía).
- La visita se crea con operador: el de `KILLBICHOS_OPERADOR_ID`, o si está vacío, el operador libre con menos visitas ese día.
- No se agenda fuera del horario de atención (`KILLBICHOS_OPEN_TIME`, `KILLBICHOS_CLOSE_TIME`, `KILLBICHOS_OPERATING_DAYS`) ni a menos de 1 hora de otra visita del mismo operador. En ese caso se le ofrece al cliente el siguiente horario libre.
- Si OpenAI o la base de datos fallan, el cliente recibe igual un mensaje ("un operador te contactará pronto") y el error queda en la consola del backend.
- Los reintentos de Twilio (mismo `MessageSid`) se ignoran, para no crear la visita dos veces.

### Variables del `.env`

Copia `.env.example` a `.env` y completa. **Nunca subas el `.env` ni claves reales a git.**

| Variable | Qué poner |
|---|---|
| `OPENAI_API_KEY` | Clave de <https://platform.openai.com/api-keys> |
| `OPENAI_MODEL` | Modelo a usar (por defecto `gpt-4.1-mini`) |
| `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` | Están en la portada de la consola de Twilio |
| `TWILIO_WHATSAPP_NUMBER` | Número del Sandbox, `whatsapp:+14155238886` |
| `TWILIO_WEBHOOK_URL` | URL pública exacta configurada en Twilio, terminada en `/webhooks/whatsapp` |
| `TWILIO_VALIDATE_SIGNATURE` | `true` en producción; `false` solo para probar en local con `curl` |
| `TWILIO_STATUS_CALLBACK_URL` | Opcional: URL del estado de entrega. Vacía = `TWILIO_WEBHOOK_URL` + `/estado` |
| `TWILIO_CONTENT_SID_RECORDATORIO`, `TWILIO_CONTENT_SID_AVISO` | Opcionales: plantillas aprobadas (`HX...`) para clientes que no escriben hace más de 24 h |
| `WHATSAPP_AVISOS_ACTIVOS` | `true`: avisar al cliente cuando el panel agenda, reagenda o cancela su visita |
| `WHATSAPP_RECORDATORIOS_ACTIVOS`, `WHATSAPP_RECORDATORIO_HORA` | Recordatorio del día anterior, desde esa hora de Chile (por defecto `18:00`) |
| `WHATSAPP_OPERADOR_MAX_HORAS` | Horas sin actividad del operador tras las que la conversación vuelve sola a la IA (por defecto `2`; `0` = nunca) |
| `KILLBICHOS_EMPRESA_ID` | Empresa que recibe las visitas (por defecto la del `seed.sql`) |
| `KILLBICHOS_OPERADOR_ID` | Opcional: operador fijo para las visitas de WhatsApp |
| `KILLBICHOS_OPEN_TIME`, `KILLBICHOS_CLOSE_TIME` | Horario de atención, por defecto `08:00` a `18:00` |
| `KILLBICHOS_OPERATING_DAYS` | Días de atención, `0`=lunes … `6`=domingo; por defecto `0,1,2,3,4,5` |

### Base de datos existente: migración de `message_sid`

Si tu base se creó antes de este cambio, agrega la columna nueva (una base creada desde cero con `schema.sql` ya la trae):

```bash
docker compose exec -T db psql -U killbichos -d killbichos < "Fase 2/Evidencias Proyecto/database/migracion_message_sid.sql"
```

### Prueba local rápida (sin Twilio)

Con `TWILIO_VALIDATE_SIGNATURE=false` en el `.env` y el backend corriendo, simula un mensaje del cliente de prueba del `seed.sql`:

```bash
curl -X POST http://127.0.0.1:8000/webhooks/whatsapp \
  -d "From=whatsapp:+56911111111" \
  -d "Body=Hola, quiero agendar mañana a las 10" \
  -d "MessageSid=SM-prueba-001"
```

La respuesta es XML (TwiML) con el texto que recibiría el cliente. Si repites el comando con el mismo `MessageSid`, se ignora (así se comporta ante un reintento de Twilio). Usa un `MessageSid` distinto para cada mensaje nuevo, y un `From` distinto para simular un cliente nuevo (la IA le pedirá la dirección).

En Windows (PowerShell) usa `curl.exe` en lugar de `curl` y escribe el comando en una sola línea.

### Prueba real con WhatsApp (Twilio Sandbox + ngrok)

1. Crea una cuenta gratuita en <https://www.twilio.com> y copia el Account SID y el Auth Token al `.env`. **Ojo con cuál:** si levantas todo con Docker (`docker compose up` desde la raíz del repo), el backend lee el `.env` **de la raíz**; `backend/.env` solo se usa al correr `uvicorn` directamente.
2. En la consola de Twilio entra a **Messaging → Try it out → Send a WhatsApp message**. Desde tu WhatsApp envía el mensaje `join <código>` que aparece ahí al número del Sandbox, para unir tu teléfono.
3. Levanta el backend (`uvicorn app.main:app --reload`, o `docker compose up` desde la raíz) y, en otra terminal, expónlo a internet con ngrok:

   ```bash
   ngrok http 8000
   ```

4. Copia la URL `https://...ngrok-free.app` que muestra ngrok. En Twilio, pestaña **Sandbox settings**, pon en **When a message comes in** la URL `https://TU-URL-NGROK/webhooks/whatsapp` con método `POST`.
5. Pon esa misma URL, exacta, en `TWILIO_WEBHOOK_URL`, deja `TWILIO_VALIDATE_SIGNATURE=true` y reinicia el backend (con Docker: `docker compose up -d backend`, para que relea el `.env`).
6. Escribe al número del Sandbox desde tu WhatsApp.

La URL de ngrok cambia cada vez que lo reinicias: actualízala en Twilio y en el `.env`. En producción `TWILIO_VALIDATE_SIGNATURE` debe quedar en `true`; con `false` cualquiera podría enviar mensajes falsos al webhook.

## Mensajes de WhatsApp que envía el sistema

Además de contestar lo que escribe el cliente (TwiML en el webhook), el backend le escribe por iniciativa propia con la API REST de Twilio (`app/whatsapp_saliente.py`):

| Qué | Cuándo |
|---|---|
| **Aviso de visita** | El panel crea una visita, cambia su fecha (Reagendar), la cancela o reactiva una cancelada. Cambiar solo notas, operador o avance (en curso, completada) no se avisa. Tampoco se avisan visitas que ya pasaron. |
| **Recordatorio** | El día anterior a cada visita agendada, desde `WHATSAPP_RECORDATORIO_HORA`. Un ciclo dentro del backend revisa cada 10 minutos; `visitas.recordatorio_enviado_at` evita duplicados; si Twilio falla por algo pasajero (caída, red, límite de envíos), la marca se quita y se reintenta en la siguiente pasada. Un error permanente (número inválido) no se reintenta. Si se reagenda, la visita vuelve a recibir recordatorio. En el panel, el botón **Enviar recordatorios de mañana** los envía en el momento (`POST /panel/whatsapp/recordatorios`). |
| **Respuesta de un operador** | Desde la pestaña **WhatsApp** del panel. Al escribir, la conversación queda **atendida por un operador** y la IA deja de responder en ella hasta que se pulse **Devolver a la IA**. Si el operador no escribe en `WHATSAPP_OPERADOR_MAX_HORAS` horas, el siguiente mensaje del cliente lo vuelve a contestar la IA. |

**Ventana de 24 h.** WhatsApp solo deja enviar texto libre hasta 24 h después del último mensaje del cliente. Fuera de esa ventana:

- los avisos y recordatorios usan la plantilla aprobada de `TWILIO_CONTENT_SID_AVISO` o `TWILIO_CONTENT_SID_RECORDATORIO`; si no hay plantilla, el mensaje queda guardado como **no enviado** y no se llama a Twilio;
- el panel no deja escribir (el backend responde `409`).

En el Sandbox, la plantilla de recordatorio puede ser la de citas que trae Twilio (*Your appointment is coming up on {{1}} at {{2}}*); su `ContentSid` aparece en **Messaging → Content Template Builder**.

**Estado de entrega.** Cada mensaje enviado guarda en `mensajes_whatsapp.estado_entrega` lo que informa Twilio en `POST /webhooks/whatsapp/estado` (`queued`, `sent`, `delivered`, `read`, `failed`, `undelivered`), con el código de error si falló (ej. `63016` = fuera de la ventana de 24 h). Esto también incluye las respuestas de la IA. El webhook valida la firma de Twilio igual que el de mensajes. Por defecto su URL es `TWILIO_WEBHOOK_URL` + `/estado`, y el backend se la indica a Twilio en cada mensaje, así que **no hay que configurarla en la consola**. Los estados que llegan en desorden (ej. `sent` después de `delivered`) no hacen retroceder el estado guardado.

Una base creada antes de este cambio necesita `../database/migracion_whatsapp_saliente.sql` (ver `../database/README.md`).

### Prueba con el Sandbox

Con el Sandbox y ngrok funcionando (sección anterior) y el teléfono que escribió al Sandbox en las últimas 24 h:

1. En el panel, **Clientes**: el cliente creado por WhatsApp tiene el número del teléfono de prueba.
2. **Agenda → Nueva visita** para ese cliente, mañana: llega el aviso "Agendamos tu visita…".
3. **Reagendar** esa visita: llega "tu visita… se cambió para…". Cambiar el estado a **Cancelada**: llega el aviso de cancelación.
4. Volver a dejarla **Agendada** y, en **WhatsApp**, pulsar **Enviar recordatorios de mañana**: llega el recordatorio.
5. En **WhatsApp**, abrir la conversación y escribir una respuesta: llega al teléfono y la conversación pasa a **Operador**. Escribir desde el teléfono: la IA no responde y el mensaje aparece en el panel. **Devolver a la IA** y escribir de nuevo: la IA vuelve a contestar.
6. Bajo cada mensaje enviado se ve su estado (✓ enviado, ✓✓ entregado, ✓✓ leído en azul, ⚠ no entregado).
