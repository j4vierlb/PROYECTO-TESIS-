# Base de datos Kill Bichos IA

PostgreSQL 16 con PostGIS (para las coordenadas de clientes y trampas).

## Cómo se levanta

La base **ya no tiene un `docker-compose.yml` propio**: se levanta con el `docker-compose.yml` de la **raíz del repositorio**, junto con el backend y el panel web.

```bash
# desde la raíz del repo
cp .env.example .env
docker compose up --build        # todo: base + backend + panel
docker compose up -d db          # solo la base
```

La primera vez que se crea la base (volumen vacío), PostgreSQL ejecuta estos scripts en orden:

| Orden | Archivo | Qué hace |
|---|---|---|
| 1 | `schema.sql` | Crea las tablas, índices y extensiones (PostGIS) |
| 2 | `seed.sql` | Datos de prueba: empresa, admin, técnico, clientes, visita de hoy, croquis y trampas |
| 3 | `demo_historial.sql` | 2 visitas pasadas completadas, para el historial de la app |
| 4 | `migracion_message_sid.sql` | Columna `message_sid` para el agente de WhatsApp (en una base nueva ya viene en `schema.sql`; aquí no hace nada y es seguro) |

Los scripts **solo corren al crear la base**. Si la base ya existe, no se vuelven a ejecutar.

## Tareas frecuentes

Todos desde la raíz del repo:

```bash
# Volver los datos de la demo a su estado inicial (visita de hoy agendada, trampas sin confirmar)
docker compose exec -T db psql -U killbichos -d killbichos < "Fase 2/Evidencias Proyecto/database/reset_demo.sql"

# Aplicar la migración de WhatsApp a una base creada antes de ese cambio
docker compose exec -T db psql -U killbichos -d killbichos < "Fase 2/Evidencias Proyecto/database/migracion_message_sid.sql"

# Abrir una consola SQL
docker compose exec db psql -U killbichos -d killbichos

# Borrar la base y empezar de cero (se pierden los datos)
docker compose down -v
```

(Si cambiaste `POSTGRES_USER` o `POSTGRES_DB` en `.env`, usa esos valores en vez de `killbichos`.)

## Credenciales de prueba (seed.sql)

- Técnico (app móvil): `tecnico1@killbichos.cl` / `demo1234`
- Administrador (panel web): `admin@killbichos.cl` / `demo1234`
