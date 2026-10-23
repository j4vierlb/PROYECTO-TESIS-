# Kill Bichos IA

## Proyecto

Kill Bichos IA es una plataforma web y móvil para apoyar el contacto con clientes, el agendamiento de visitas y la generación asistida de croquis para una empresa de control de plagas.

## Estructura de Fase 2

- `Evidencias Proyecto/backend`: API FastAPI, autenticación, panel web, visitas y croquis.
- `Evidencias Proyecto/frontend`: panel administrativo React/Vite.
- `Evidencias Proyecto/app-movil`: aplicación Flutter para operadores.
- `Evidencias Proyecto/database`: PostgreSQL/PostGIS, esquema, datos de prueba y migraciones. Docker Compose está en la raíz del repositorio.
- `Evidencias Proyecto/Evidencias de documentacion`: entregables de gestión, diseño, pruebas, manual y cierre.
- `Evidencias Grupales`: guías del estudiante de la fase (2.4 Desarrollo del Proyecto APT y 2.6 Informe Final).
- `Evidencias Individuales`: diarios de reflexión de cada integrante (2.1).

## Inicio rápido

### Entorno completo con Docker

Desde la raíz del repositorio, preparar el `.env` sin sobrescribir uno existente
y completar las variables de desarrollo:

```powershell
if (-not (Test-Path -LiteralPath .env)) { Copy-Item -LiteralPath .env.example -Destination .env }
docker compose up -d --build
```

El Compose está en la raíz, no en `database`. Levanta la base en 5432, la API
en 8000 y el panel compilado en <http://localhost:8080>. Flutter se ejecuta fuera
de Docker. `docker compose down` conserva los datos; no usar `down -v` sobre la
base de trabajo sin autorización y respaldo.

El comando supone una instalación sin otra base ocupando 5432. Si ya existe
una base de un compose antiguo, identificar su contenedor, red y volumen antes
de continuar: conservar los datos y no levantar otro `db` encima.

### Backend fuera de Docker

Como alternativa, iniciar solo `docker compose up -d db` desde la raíz y después
trabajar en la carpeta backend. Preparar `backend/.env` desde su plantilla, sin
sobrescribir uno existente, con `DATABASE_URL` apuntando a la base local. Evitar
iniciar otro backend en 8000 si el servicio de Docker ya está activo.

```bash
cd "Fase 2/Evidencias Proyecto/backend"
python -m venv .venv
# Windows
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

API: <http://127.0.0.1:8000/docs>

### Panel web en desarrollo

```bash
cd "Fase 2/Evidencias Proyecto/frontend"
npm ci
npm run dev
```

Panel: <http://localhost:5173>. Vite lee el `.env` raíz. Configurar
`VITE_GOOGLE_MAPS_API_KEY` con la clave web restringida para consultar el mapa;
no reutilizar la del iPhone ni agregar `VITE_` a secretos del backend.

## Credenciales de demostración

| Rol | Usuario | Clave |
| --- | --- | --- |
| Administrador | `admin@killbichos.cl` | `demo1234` |
| Operador | `tecnico1@killbichos.cl` | `demo1234` |

Estas credenciales son únicamente para el ambiente local de demostración.

## Documentación de Fase 2

La carpeta `Evidencias Proyecto/Evidencias de documentacion` contiene:

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
11. Acta de validación para completar con Rodrigo Quiroga y obtener su firma.

Product Vision y Product Backlog se mantienen como artefactos de planificación del equipo y deben revisarse junto con estos documentos cuando cambie el alcance.

## Resultados y alcance al 20 de octubre de 2026

- [Script del 06/10/2026](../pruebas/resultados_2026-10-06_1614.md): 32 casos aprobados, con seguridad y rendimiento local.
- [Regresión del panel del 09/10/2026](Evidencias%20Proyecto/pruebas/Panel_regresion_2026-10-09.md): 51 pruebas aprobadas y verificaciones en navegador con PostGIS real.
- [Regresión tras PR #14](Evidencias%20Proyecto/pruebas/Verificacion_PR14_2026-10-20.md): **205 aprobadas**, 107 backend y 98 frontend, sin fallas ni omisiones. Incluye los 30 casos de aislamiento entre empresas, no se suman nuevamente.
- [Maps real](Evidencias%20Proyecto/pruebas/Croquis_maps_real_2026-10-20.md): mapa satelital, selección y foto privada verificados manualmente en localhost:5173 con datos sintéticos; no se suma al total automatizado.
- Las ejecuciones de 32, 51 y 169 son históricas y tienen comportamientos compartidos; no se suman como requisitos distintos a las 205 actuales.
- La generación automática de croquis, la geocodificación y la sincronización offline no están implementadas en `main`.
- El webhook y agente de WhatsApp están integrados, pero la conversación real de Sandbox no tiene resultado registrado en las evidencias revisadas.
- La aceptación de la empresa requiere una sesión y el acta firmada; no se deduce de las pruebas técnicas.

Docker lee el `.env` de raíz. `backend/.env` se usa al ejecutar uvicorn fuera de
Docker desde esa carpeta. Las claves reales de Twilio, OpenAI y mapas no se
incluyen en documentos ni en Git.

Los 11 Word se actualizaron con estas evidencias, conservando el historial de
errores y sin anticipar la aceptación del cliente. Su contenido y estructura
se comprobaron; la revisión visual sigue pendiente porque el renderizador
empaquetado no dispone de LibreOffice. El acta conserva sus resultados como
No evaluado por el cliente y sus campos de sesión y firma sin completar.

## Seguridad y datos

El sistema utiliza JWT, roles diferenciados, CORS restringido y aislamiento por empresa. No se deben subir secretos, tokens, contraseñas reales ni datos personales del cliente al repositorio.
