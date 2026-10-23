# Verificación del visor web de croquis

Prueba inicial: 19 de octubre de 2026. Actualización: 20 de octubre de 2026.
Responsable: Juan. Rama `juan`, base integrada `7f635f9` (PR #14), más cambios
locales sin commit ni push. Historia local `PANEL-CROQ-01`.

## Resultado

**205 pruebas automatizadas aprobadas: 107 backend y 98 frontend, sin fallas,
errores ni omisiones.** Las 30 pruebas de aislamiento entre empresas están
incluidas en las 107 del backend; no se agregan de nuevo al total. La
compilación de producción fue correcta. El detalle de la ejecución está en
[Verificacion_PR14_2026-10-20.md](Verificacion_PR14_2026-10-20.md).

El mapa real, la selección de trampas y la foto privada se verificaron en
`http://localhost:5173/`; véase
[Croquis_maps_real_2026-10-20.md](Croquis_maps_real_2026-10-20.md). Es una
comprobación manual separada y no incrementa el conteo automatizado.

Resultados originales de la ejecución actual:

- [Backend: 107 aprobadas](resultados_backend_pr14_2026-10-20.json).
- [Frontend: 98 aprobadas](resultados_frontend_pr14_2026-10-20.json).
- [Aislamiento: 30/30, incluidos en backend](resultados_aislamiento_empresas_pr14_2026-10-20.json).

Las ejecuciones anteriores de 32, 51, 110, 125 y 169 se conservan como
historial, no como pruebas adicionales ni como el resultado vigente.

| Suite | Aprobadas | Alcance |
| --- | ---: | --- |
| panel-utils.test.js | 26 | Fechas y datos opcionales |
| api.test.js | 18 | HTTP general (9) y fotos privadas CRP01–04 (9) |
| panel.test.jsx | 24 | Flujos existentes del panel |
| croquis.test.jsx | 16 | CRW01–15, incluyendo dos variantes CRW09 |
| croquis-map.test.js | 14 | CRM01–06; adaptador Maps con SDK simulado |
| test_panel_contract.py | 20 | Contrato y validación |
| test_zona_horaria.py | 5 | Día local de Chile |
| test_panel_postgis.py | 26 | Panel, JWT y persistencia real |
| test_croquis_terreno.py | 15 | Regresión del croquis en terreno de main |
| test_panel_croquis_readonly.py | 5 | CRB01–05; JWT y PostGIS, ambos roles en subcasos |
| test_company_access_postgis.py | 30 | Visitas, croquis y fotos; admin y coordinador de dos empresas, en ambas direcciones, y acceso sin token |
| test_acceso_empresa.py | 6 | Regresión de Javier del PR #14, con subcasos de roles, PATCH ajeno, operadores y recursos inexistentes |

## Casos del visor

| ID | Verificación | Resultado |
| --- | --- | --- |
| CRW01 | Croquis de solo lectura | Solo GET; sin controles de alta, edición o carga |
| CRW02 | Retiradas y sugerencias IA | Retiradas visibles en gris; IA sin confirmar en amarillo |
| CRW03 | Croquis inexistente | Mensaje 404; no se llama a POST |
| CRW04 | Acceso rechazado por la API | Mensaje 403 y sin datos de trampas; HTTP simulado |
| CRW05 | Croquis sin trampas | Mensaje de croquis vacío |
| CRW06 | Fallo o falta de Maps | Listado y fotos disponibles |
| CRW07 | Sin coordenadas | No inventa posiciones ni carga SDK |
| CRW08 | Foto autenticada | Bearer en header; URL blob y liberación al cerrar |
| CRW09 | Foto 403 o 404 | Mensaje y reintento, sin imagen inválida |
| CRW10 | Selección | Lista y mapa sincronizados con SDK simulado |
| CRW11 | Actualizar | Repite GET, sin escrituras |
| CRW12 | Cambio de visita | Aborta petición anterior |
| CRW13 | Respuesta incoherente | Rechaza croquis de otra visita |
| CRW14 | Foto con 401 | Expira sesión del panel |
| CRW15 | Visita completada | Abre visor; Escape cierra y restaura foco |
| CRP01–04 | Descarga privada | Rechaza rutas externas y query no permitida, SVG, vacío y más de 5 MB; GET sin redirección ni caché persistente |
| CRM01–06 | Modelo y mapa | Coordenadas, colores, puntos no editables, selección y limpieza; Google SDK simulado |
| CRB01 | Croquis completado con retiradas | Admin y coordinador leen sin cambiar cantidad de trampas |
| CRB02 | Foto propia | Ambos roles reciben foto privada de su empresa |
| CRB03 | GET sin croquis | 404 y cantidad de croquis sin cambios |
| CRB04 | Ausencia de token | Croquis y foto responden 401 |
| CRB05 | Foto de otra empresa | Admin y coordinador reciben 403 |

## Verificación inicial en navegador del 19 de octubre

FastAPI en `http://127.0.0.1:8787`, Vite en `http://127.0.0.1:5174`, base
aislada `panel_regression` del contenedor QA. No se enviaron WhatsApp ni
solicitudes a OpenAI. No se alteraron clientes o visitas de la base de trabajo.

Se abrió el croquis de la visita sintética del 21/10/2026 y se mostraron tres
trampas: confirmada, IA sin confirmar y retirada. La imagen de prueba generada
se descargó con autenticación y el navegador comprobó ancho natural de 500 px.
No es una fotografía real ni una prueba de posición sobre Google Maps.

Se seleccionó la retirada y se comprobó su detalle sin foto. En la visita
cancelada del 22/10/2026 se mostró la ausencia de croquis; la consulta no creó
uno. Sin clave, el aviso de Maps no bloqueó estos flujos.

No hubo desborde horizontal del documento o diálogo en las vistas comprobadas
de 1366, 390 y 320 px. No equivale a prueba en un teléfono físico.

Capturas en `capturas/panel_2026-10-19/`:

- `07_croquis_escritorio.png`: tres estados, detalle y foto sintética.
- `08_croquis_movil_390.png`: selección de retirada en móvil.
- `09_croquis_inexistente_320.png`: consulta de visita cancelada sin croquis.

## Mapa real y aislamiento verificados al 20 de octubre

| ID | Condición | Resultado y evidencia |
| --- | --- | --- |
| CR-EXT-01 | Google Maps real | Aprobado en la repetición del 20/10 desde localhost:5173; ver Croquis_maps_real_2026-10-20.md. El rechazo original se conserva como historial |
| CR-EXT-02 | Empresa de croquis y visita | Aprobado tras integrar PR #14 en 7f635f9: 30/30 casos; accesos ajenos 403, propios 200 y sin token 401. Ver Verificacion_PR14_2026-10-20.md; se conserva el fallo anterior como historial |

La aprobación del mapa se basa en la comprobación manual con Google Maps real,
no solo en las pruebas del adaptador con SDK simulado. La del aislamiento se
basa en la suite específica repetida tras integrar la corrección de Javier:
12 accesos propios con 200, 12 accesos ajenos con 403 y 6 sin token con 401.
Las pruebas de fotos por sí solas no se usan para acreditar visitas y croquis.

Se comprobó el mapa satelital y la selección de T-02 desde el mapa, la
selección de T-03 desde el listado y la foto privada de T-01. No reapareció
el rechazo de referente en la repetición. Evidencia:
`capturas/panel_2026-10-19/11_maps_real_2026-10-20.png`.

## Entorno y límites de la comprobación

Las pruebas automatizadas usan bases PostgreSQL/PostGIS aisladas,
`panel_regression` y `croquis_regression`, con datos sintéticos y rollback por
caso. No se usó la base de trabajo para sembrar datos. La prueba manual del
mapa empleó Vite en `localhost:5173` y la API QA en `127.0.0.1:8787`.

El mapa real no se volvió a comprobar en `localhost:8080` ni en un despliegue
remoto. Las fotos de prueba son sintéticas. Los resultados no acreditan
generación de croquis por IA, conversación real por WhatsApp, funcionamiento
offline ni aceptación del cliente, ni equivalen a una auditoría completa.

## Reproducción

Frontend, desde su carpeta:

```powershell
npm ci
npm test
npm run build
npm audit --omit=dev
```

Backend, desde su carpeta, contra dos bases **aisladas** inicializadas con
`schema.sql` y `migracion_croquis_terreno.sql`:

```powershell
$env:PANEL_TEST_DATABASE_URL = '<URL aislada a panel_regression>'
$env:CROQUIS_TEST_DATABASE_URL = '<URL aislada a croquis_regression>'
python -B -m unittest discover -s tests -v
```

La ejecución registrada utilizó un contenedor temporal distinto del QA de
navegador y de la base de trabajo. Cada caso PostGIS se revierte por rollback.
Sin las variables correspondientes se omiten pruebas; no declarar aprobación
completa si el ejecutor informa omisiones.

## Documentación

El backlog 02, diseño 06, pruebas 07 y trazabilidad 09 reflejan los resultados
actuales de Maps y PR #14. La actualización de los 11 Word y sus límites se
registró en
[Registro_actualizacion_2026-10-20.md](../Evidencias%20de%20documentacion/Registro_actualizacion_2026-10-20.md).
Su contenido y estructura se comprobaron; la revisión visual de páginas
sigue pendiente porque el renderizador empaquetado no dispone de LibreOffice.

## Historial de incidencias resueltas

- **Mapa antes del ajuste de referentes:** el intento anterior devolvió
  `RefererNotAllowedMapError`; el listado y la foto siguieron disponibles.
  Se conserva `capturas/panel_2026-10-19/10_maps_referer_rechazado.png` como
  evidencia del fallo original. La repetición del 20/10 aprobó el mapa real;
  este error no constituye un bloqueo vigente en el origen probado.
- **Permisos antes del PR #14:** con base `78fe755`, la suite de aislamiento
  obtuvo 22/30 y detectó ocho accesos ajenos a visitas y croquis. Se conservan
  [el hallazgo original](Aislamiento_empresas_2026-10-20.md) y
  [su JSON](resultados_aislamiento_empresas_2026-10-20.json).
  Tras integrar el arreglo de Javier en `7f635f9`, la repetición aprobó 30/30.
- **Regresión previa a esos 36 casos adicionales:** la ejecución del 19/10
  aprobó 169 pruebas (71 backend y 98 frontend). Sus resultados originales
  son [backend](resultados_croquis_backend_2026-10-19.json) y
  [frontend](resultados_croquis_frontend_2026-10-19.json). La ejecución actual
  incorpora 30 pruebas de aislamiento y 6 de Javier y obtiene 205 en total;
  no se suman las ejecuciones completas entre sí.

Las comprobaciones de configuración no detectaron los valores de
OPENAI_API_KEY, TWILIO_AUTH_TOKEN o JWT_SECRET en el JavaScript servido.
La clave web de Maps se incluye en el bundle para usar el SDK; el `.env`
continúa ignorado por Git. Las notas de la PR siguen siendo un borrador local:
no se hizo staging, commit, push ni apertura de PR con estos cambios.
