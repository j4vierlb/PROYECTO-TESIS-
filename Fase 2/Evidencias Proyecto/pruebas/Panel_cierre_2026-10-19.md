# Verificación del panel web del 19 de octubre de 2026

**Informe histórico del panel, previo al visor y a la suite de aislamiento.**
La ejecución vigente del conjunto está en
[Verificacion_PR14_2026-10-20.md](Verificacion_PR14_2026-10-20.md):
205 aprobadas (107 backend y 98 frontend), incluidas las 30 de aislamiento.
Los resultados, comandos y límites siguientes corresponden al corte del
19/10, no a pendientes ni a conteos actuales.

Responsable: Juan. Rama: `juan`, sobre `04a9ca8`, con cambios locales sin commit.

## Resultado

Se aprobaron **110 pruebas automatizadas**: 59 del frontend y 51 del backend,
sin fallas ni omisiones. La compilación de producción fue exitosa. La consulta
`npm audit --omit=dev` no reportó vulnerabilidades en esa ejecución; no es una
garantía de ausencia de defectos ni una auditoría de seguridad completa.

| Suite | Pruebas aprobadas | Alcance |
| --- | ---: | --- |
| `frontend/tests/panel-utils.test.js` | 26 | Fecha chilena, conversión UTC, horario de verano/invierno, datos opcionales |
| `frontend/tests/api.test.js` | 9 | Errores HTTP y de red, validación, sesión vencida, timeout y respuestas sin contenido |
| `frontend/tests/panel.test.jsx` | 24 | Interacción React con HTTP simulado, edición, asignación, permisos, errores, filtros y doble envío |
| `backend/tests/test_panel_contract.py` | 20 | Contrato HTTP con SQL simulado y validaciones administrativas |
| `backend/tests/test_zona_horaria.py` | 5 | Día de Chile |
| `backend/tests/test_panel_postgis.py` | 26 | API, JWT, SQL y PostgreSQL/PostGIS reales con rollback por caso |

Los conteos corresponden a esta ejecución. No se suman a las suites históricas
de 32 y 51 como si fueran requisitos diferentes. Las comprobaciones manuales
y capturas siguientes tampoco se agregan al total automatizado.

## Funcionalidades verificadas

| ID | Verificación | Resultado |
| --- | --- | --- |
| PANEL-EDIT-01 | Cambiar fecha y hora de una visita existente | Guarda UTC, conserva hora de Chile, cambia a `reagendada` y aparece en la nueva fecha |
| PANEL-ASIG-02 | Asignar y quitar operador después de crear | Guarda UUID o null; permite solo operadores activos de la empresa |
| PANEL-HOR-02 | Días y horas configurados para WhatsApp | El panel reutiliza la comprobación del backend; domingo, antes de abrir y al cierre se rechazan, incluso sin operador |
| PANEL-COL-01 | Choque de un operador | Responde 409 a menos de una hora; permite separación exacta de una hora y excluye la propia visita al editar |
| PANEL-EST-01 | Edición de visitas cerradas | Impide cambiar fecha u operador sin reactivar; permite corregir notas |
| PANEL-CLI-02 | Cliente manual sin GPS | Se crea con ubicación null; una coordenada incompleta se rechaza |
| PANEL-CLI-03 | Teléfono duplicado | Creación y edición responden 409, sin dejar la conexión inutilizable |
| PANEL-CLI-04 | Eliminación de clientes | Interfaz pide confirmación; API impide eliminar clientes con visitas |
| PANEL-AUTH-02 | Acceso y expiración | Login comprueba acceso administrativo; HTTP 401 vuelve al login; técnicos no pueden editar por el endpoint del panel |
| PANEL-TENANT-01 | Aislamiento del panel | Rechaza visitas, clientes y operadores de otra empresa |
| PANEL-UX-01 | Errores y navegación | Conserva formulario ante rechazo; permite reintentar; descarta cargas antiguas al cambiar el día |
| PANEL-UX-02 | Envío repetido | Una segunda acción mientras guarda no genera otra solicitud |
| VIS-002 | Cancelación con croquis y trampa asociados | PostGIS confirma que conserva visita, croquis y trampa; solo cambia el estado |

## Comprobación en navegador real

Se levantó FastAPI en `http://127.0.0.1:8787` y Vite en
`http://127.0.0.1:5174`, conectados exclusivamente a la base sintética
`panel_regression` del contenedor `killbichos-panel-qa-20261019`.
No se usaron datos reales ni se enviaron mensajes por WhatsApp.

Se comprobó crear una visita para el 20/10/2026 a las 10:00 con operador,
rechazar su cambio a las 18:00, reprogramarla al 21/10/2026 a las 11:00 y
quitarle el operador. Después de recargar y seleccionar ese día, seguía como
`reagendada` y sin asignar. La consulta SQL confirmó la fecha local, estado,
operador null y notas persistidos.

También se creó un cliente manual sin coordenadas. La revisión responsiva
incluyó anchos de 320 y 390 px y escritorio de 1366 px, sin desborde horizontal
en las pantallas verificadas. No equivale a una certificación de todos los
navegadores ni a una prueba en un teléfono físico.

Capturas, con información sintética, en `capturas/panel_2026-10-19/`:

- `01_edicion_persistida.png`: formulario con fecha y asignación recuperadas.
- `02_horario_rechazado.png`: rechazo con formulario y notas conservados.
- `03_clientes_responsive.png`: cliente recién creado sin GPS.
- `04_clientes_movil_390.png`: clientes en vista móvil.
- `05_agenda_escritorio.png`: visita reprogramada en escritorio.
- `06_agenda_movil_320.png`: agenda en ancho mínimo verificado.

## Comprobación adicional de concurrencia

Se enviaron dos solicitudes HTTP simultáneas de creación al mismo operador
para el 22/10/2026 a las 10:00, contra el servidor aislado. Se obtuvieron
**201 y 409**: solo una fue creada. La visita sintética creada quedó luego
cancelada mediante la API. Esta comprobación no se suma a las 110 pruebas.

El bloqueo de fila del operador serializa las solicitudes del panel. No se
modificó la transacción de WhatsApp; la concurrencia entre ambos canales queda
fuera de esta comprobación y requiere revisión conjunta de ese módulo.

## Reproducción del entorno histórico

Frontend, desde `frontend`:

```powershell
npm ci
npm test
npm run build
npm audit --omit=dev
```

Backend, desde `backend`, con una base PostGIS separada llamada exactamente
`panel_regression`, creada con `database/schema.sql`:

```powershell
$env:PANEL_TEST_DATABASE_URL = '<URL de la base aislada panel_regression>'
python -B -m unittest discover -s tests -v
```

Sin esa variable, los casos PostGIS se omiten. La base de las pruebas
automatizadas se mantuvo separada de la demostración del navegador y de la
base de trabajo. Los casos de medianoche configuran atención nocturna solo
dentro de su prueba para verificar UTC sin saltarse la nueva política.

## Alcance y límites

Los cambios funcionales del backend se limitan al router del panel y a sus
esquemas. `VisitUpdate` del móvil no se amplió; no se cambiaron tablas,
migraciones, autenticación del backend, WhatsApp, croquis ni app móvil.

El panel ahora exige días y horas de atención, según la decisión del usuario.
No se agregó una prohibición de registrar fechas pasadas ni el límite de
60 días de WhatsApp: esas políticas administrativas no se cambiaron.

Los resultados no certifican despliegue productivo, generación de croquis por
IA, funcionamiento offline, Twilio real ni aceptación del cliente. En esta
ejecución del 19/10 no se editaron los documentos preexistentes ni el acta;
la actualización documental posterior está registrada por separado.
