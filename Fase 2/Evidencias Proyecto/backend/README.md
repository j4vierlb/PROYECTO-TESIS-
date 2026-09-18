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
└── routers/
    ├── auth.py
    ├── visitas.py
    ├── croquis.py
    └── dispositivos.py
```

Las coordenadas se guardan en PostgreSQL como `GEOGRAPHY(Point, 4326)` (PostGIS) y se convierten a `lat`/`lng` sueltos en las respuestas de la API con `ST_Y`/`ST_X`.
