# Notas para la pull request del panel

Rama de origen: `juan`. Destino: `main`. Base integrada: `7f635f9` (PR #14).
Este archivo es una propuesta local; no se creó ni publicó una PR.

## Título propuesto

Mejorar agenda y clientes y agregar consulta de croquis con fotos privadas

## Descripción para copiar

### Resumen

- Mejora la edición y reprogramación de visitas, la asignación de operador y el filtro Sin asignar.
- Aplica al panel los días y horas de atención configurados para WhatsApp y valida la separación de una hora entre visitas del mismo operador.
- Permite clientes manuales sin GPS, valida coordenadas completas y devuelve conflictos de teléfono duplicado.
- Agrega un visor de solo lectura del croquis desde Agenda, disponible también para visitas cerradas.
- Conserva las trampas retiradas en gris y distingue propuestas IA sin confirmar.
- Descarga fotos privadas con el token en Authorization, sin incluirlo en la URL; rechaza direcciones externas y redirecciones.
- Agrega configuración web de Google Maps mediante variables del .env, sin subir credenciales.
- Actualiza documentación y evidencias de pruebas.

### Alcance del backend

Los cambios funcionales locales del backend corresponden al panel en
`routers/panel.py` y sus esquemas en `schemas.py`. Se mantiene el contrato
móvil VisitUpdate. No se modifica ensure_visit_access ni los routers de
croquis, fotos o WhatsApp por cuenta propia; el arreglo de acceso por empresa
de Javier ya se integró desde main mediante el PR #14.

### Verificación

- Ejecución completa histórica previa a la suite de aislamiento: 169 pruebas aprobadas, 98 frontend y 71 backend. No incluye los 30 casos nuevos indicados a continuación.
- Verificación actual tras PR #14: 205 pruebas aprobadas, 107 backend y 98 frontend, sin fallas ni omisiones. Incluye los 30 casos de aislamiento, ahora todos aprobados. Ver Verificacion_PR14_2026-10-20.md y sus JSON. Los ocho fallos anteriores se conservan solo como historial.
- Repetición del frontend al revisar pendientes: 98 aprobadas.
- Imagen web Docker reconstruida con la clave Maps configurada; HTTP 200 en localhost:8080 y health de API correcto.
- Google Maps real aprobado desde localhost:5173 el 20/10/2026: imágenes satelitales, selección de T-02 desde el mapa, selección desde el listado y foto privada cargada. El rechazo de referente previo queda registrado como historial.
- La clave web está incluida en el bundle como requiere el SDK. Se comprobó que no se incluyeron los valores configurados de OPENAI_API_KEY, TWILIO_AUTH_TOKEN o JWT_SECRET.
- Pruebas manuales de croquis realizadas con datos y una imagen sintéticos.

### Condiciones pendientes de integración

- [x] Repetir la prueba real de mapa y selección tras corregir los referentes: aprobada en localhost:5173 el 20/10/2026; localhost:8080 no se comprobó en esta repetición.
- [x] Integrar el PR #14 de Javier y repetir test_company_access_postgis.py: 30 aprobadas, 0 fallidas y 0 omitidas, con ambos roles y ambas direcciones.
- [x] Actualizar el contenido de los 11 Word al 20/10 con Maps real, PR #14, 205 pruebas y 30/30 de aislamiento, conservando las fallas anteriores como historial y el acta sin aprobación ni firma.
- [ ] Revisar visualmente los Word. El renderizador empaquetado no tiene LibreOffice disponible; contenido y estructura comprobados, maquetación no aprobada.

El control de empresa del visor quedó verificado por la suite específica de
visitas, croquis y fotos. No se deduce de las pruebas de fotos por sí solas.
La revisión de los Word sigue pendiente y el mapa se comprobó en localhost:5173,
no en un despliegue remoto.

## Revisión de archivos antes de hacer commit

El directorio tiene cambios anteriores y cambios del visor mezclados. Revisar
el diff antes de seleccionar archivos; no ejecutar `git add .` sin esa revisión.

- Código del panel y sus pruebas: `frontend/src`, `frontend/tests`, configuración Vite, dependencias, Dockerfile e index.html.
- Contratos administrativos: `backend/app/routers/panel.py`, `backend/app/schemas.py` y pruebas del panel, incluida la lectura web del croquis.
- Configuración sin secretos: `.env.example` y `docker-compose.yml`.
- Documentación del visor: documentos 02, 06, 07 y 09; README frontend y reporte Croquis_web_2026-10-19.md con sus resultados JSON y capturas sintéticas.
- Revisiones anteriores de los otros Word, el acta sin firma, los reportes históricos y Fase 2/README.md: revisar separadamente para decidir su inclusión. No se descartan ni se revierten.
- Excluir `.env`, credenciales, respaldos SQL, node_modules, dist y archivos temporales.

## Mensaje técnico para Javier

Probé de nuevo desde http://localhost:5173/ y el mapa satelital ya carga.
La selección desde el mapa y el listado funciona, y la foto privada también.
El rechazo de referente anterior no reapareció. Gracias por el ajuste.
Integré tu PR #14 en juan y repetí el aislamiento: ahora pasan los 30 casos.
Visitas, croquis y fotos ajenos responden 403; los accesos propios siguen en
200 y sin token en 401. La regresión completa también pasó: 107 backend y
98 frontend. Conservé el reporte anterior como historial y registré el cierre
en Verificacion_PR14_2026-10-20.md. No reescribí tu corrección. Gracias.
