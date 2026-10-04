# Kill Bichos IA

## Proyecto

Kill Bichos IA es una plataforma web y móvil para apoyar el contacto con clientes, el agendamiento de visitas y la generación asistida de croquis para una empresa de control de plagas.

## Estructura de Fase 2

- `Evidencias Proyecto/backend`: API FastAPI, autenticación, panel web, visitas y croquis.
- `Evidencias Proyecto/frontend`: panel administrativo React/Vite.
- `Evidencias Proyecto/app-movil`: aplicación Flutter para operadores.
- `Evidencias Proyecto/database`: PostgreSQL/PostGIS, esquema, datos de prueba y Docker Compose.
- `Documentos`: entregables de gestión, diseño, pruebas, manual y cierre.

## Inicio rápido

### Base de datos

```bash
cd "Fase 2/Evidencias Proyecto/database"
docker compose up -d
```

### Backend

```bash
cd "Fase 2/Evidencias Proyecto/backend"
python -m venv .venv
# Windows
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

API: <http://127.0.0.1:8000/docs>

### Panel web

```bash
cd "Fase 2/Evidencias Proyecto/frontend"
npm install
npm run dev
```

Panel: <http://127.0.0.1:5173>

## Credenciales de demostración

| Rol | Usuario | Clave |
| --- | --- | --- |
| Administrador | `admin@killbichos.cl` | `demo1234` |
| Operador | `tecnico1@killbichos.cl` | `demo1234` |

Estas credenciales son únicamente para el ambiente local de demostración.

## Documentación de Fase 2

La carpeta `Documentos` contiene:

1. Documento de inicio y alcance del MVP.
2. Sprint Backlog y tablero de trabajo.
3. Definition of Done.
4. Fichas de sprint.
5. Retrospectivas.
6. Documento de diseño.
7. Plan de pruebas y evidencias.
8. Manual técnico.
9. Matriz de trazabilidad.
10. Informe de innovación y cierre.

Product Vision y Product Backlog se mantienen como artefactos de planificación del equipo y deben revisarse junto con estos documentos cuando cambie el alcance.

## Seguridad y datos

El sistema utiliza JWT, roles diferenciados, CORS restringido y aislamiento por empresa. No se deben subir secretos, tokens, contraseñas reales ni datos personales del cliente al repositorio.
