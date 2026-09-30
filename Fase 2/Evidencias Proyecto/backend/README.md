# Backend Kill Bichos IA

API FastAPI conectada a PostgreSQL + PostGIS (carpeta `../database/`).

## Instalación y ejecución

1. Levanta la base de datos (Docker):
   ```bash
   cd "Fase 2/Evidencias Proyecto/database"
   docker compose up -d
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

## Credenciales de prueba (seed.sql)

- Operador: `tecnico1@killbichos.cl` / `demo1234`
- Administrador: `admin@killbichos.cl` / `demo1234`

El login recibe JSON con `usuario` y `clave`, y entrega un `access_token` de 8 horas y un `refresh_token` de 30 días.

## Fechas y zona horaria

Las fechas se guardan y se envían en **UTC** (ISO 8601), pero **"hoy" es el día de Chile** (`America/Santiago`): la agenda del técnico y la del panel comparan cada visita convertida a la hora de Chile. Si se calculara en UTC, desde las 21:00 hora de Chile (20:00 en invierno) la agenda mostraría las visitas del día siguiente. El cálculo está en `app/zona_horaria.py`. El paquete `tzdata` (en `requirements.txt`) asegura los datos de zonas horarias aunque el sistema no los traiga, como en Windows o en imágenes de Docker mínimas.

## Pruebas

Desde esta carpeta (no necesitan base de datos):

```bash
python -m unittest discover tests
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
├── ai/
│   └── agent.py          # agente conversacional (OpenAI) para WhatsApp
└── routers/
    ├── auth.py
    ├── panel.py       # CRUD de clientes, agenda y operadores del panel web
    ├── visitas.py
    ├── croquis.py
    ├── dispositivos.py
    └── whatsapp.py       # webhook de Twilio: POST /webhooks/whatsapp
```

## Panel web

El frontend está en `../frontend/` y consume los endpoints protegidos del panel:

- `GET /panel/stats`, `GET /panel/operadores`
- `GET/POST /clientes`, `PATCH/DELETE /clientes/{id}`
- `GET/POST /panel/visitas`, `PATCH/DELETE /panel/visitas/{id}`

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
| `KILLBICHOS_EMPRESA_ID` | Empresa que recibe las visitas (por defecto la del `seed.sql`) |
| `KILLBICHOS_OPERADOR_ID` | Opcional: operador fijo para las visitas de WhatsApp |
| `KILLBICHOS_OPEN_TIME`, `KILLBICHOS_CLOSE_TIME` | Horario de atención, por defecto `08:00` a `18:00` |
| `KILLBICHOS_OPERATING_DAYS` | Días de atención, `0`=lunes … `6`=domingo; por defecto `0,1,2,3,4,5` |

### Base de datos existente: migración de `message_sid`

Si tu base se creó antes de este cambio, agrega la columna nueva (una base creada desde cero con `schema.sql` ya la trae):

```bash
docker exec -i killbichos_db psql -U killbichos -d killbichos < "Fase 2/Evidencias Proyecto/database/migracion_message_sid.sql"
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

1. Crea una cuenta gratuita en <https://www.twilio.com> y copia el Account SID y el Auth Token al `.env`.
2. En la consola de Twilio entra a **Messaging → Try it out → Send a WhatsApp message**. Desde tu WhatsApp envía el mensaje `join <código>` que aparece ahí al número del Sandbox, para unir tu teléfono.
3. Levanta el backend (`uvicorn app.main:app --reload`) y, en otra terminal, expónlo a internet con ngrok:

   ```bash
   ngrok http 8000
   ```

4. Copia la URL `https://...ngrok-free.app` que muestra ngrok. En Twilio, pestaña **Sandbox settings**, pon en **When a message comes in** la URL `https://TU-URL-NGROK/webhooks/whatsapp` con método `POST`.
5. Pon esa misma URL, exacta, en `TWILIO_WEBHOOK_URL`, deja `TWILIO_VALIDATE_SIGNATURE=true` y reinicia el backend.
6. Escribe al número del Sandbox desde tu WhatsApp.

La URL de ngrok cambia cada vez que lo reinicias: actualízala en Twilio y en el `.env`. En producción `TWILIO_VALIDATE_SIGNATURE` debe quedar en `true`; con `false` cualquiera podría enviar mensajes falsos al webhook.
