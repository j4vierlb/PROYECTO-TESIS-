# Informe de aportes y evidencias de Fase 2 — Juan Bórquez

Proyecto: Kill Bichos IA. Corte de las evidencias: 21 de octubre de 2026.
Recopilación preparada para publicación: 22 de octubre de 2026.

Este índice reúne desarrollo, correcciones, pruebas y documentación del panel
web, y la preparación de la aplicación existente para Android. Complementa los
entregables Word; no sustituye los formatos exigidos por la asignatura ni una
validación firmada del cliente. Distingue resultados comprobados, resultados
históricos y condiciones todavía pendientes.

## 1. Resumen del aporte individual

El trabajo se concentró en el panel administrativo y el agendamiento: gestión
de clientes, agenda en horario chileno, asignación de técnicos, edición y
cancelación de visitas, y manejo de errores. Después se incorporó la consulta
del croquis de cada visita con mapa, trampas y fotografías privadas, sin permitir
modificar las trampas desde el panel.

Se añadieron pruebas del panel y de aislamiento entre empresas, y se organizaron
reportes, resultados JSON y capturas. También se prepararon y actualizaron los
documentos de Fase 2 con el estado técnico y los límites de la evidencia.

La extensión a Android consistió en preparar el entorno, configurar la conexión
local de desarrollo, compilar e instalar un APK debug y comprobar flujos de la
app Flutter compartida. No fue una reimplementación de la aplicación móvil.

La aplicación móvil original, los endpoints compartidos, la corrección general
de permisos y otros módulos son aportes del equipo. En particular, la solución
del control de empresa del PR #14 corresponde a Javier; el aporte aquí descrito
es la detección mediante pruebas, integración y verificación del arreglo. Los
módulos de WhatsApp e IA no se atribuyen a Juan.

## 2. Desarrollo y trazabilidad en Git

Los enlaces apuntan a commits y PR concretos. Un commit puede incluir varias
funcionalidades o documentos; no se cuenta cada archivo como un commit ni se
usa el número de commits como medida de esfuerzo o de autoría exclusiva.

| Fecha del commit | Aporte registrado | Evidencia de código / integración |
| --- | --- | --- |
| 28/09 | Implementación inicial del panel y agendamiento | [049ea06](https://github.com/j4vierlb/PROYECTO-TESIS-/commit/049ea06); [PR #4](https://github.com/j4vierlb/PROYECTO-TESIS-/pull/4) |
| 28/09 | Integración y protección de eliminaciones: cliente con visitas devuelve 409; visita se cancela en lugar de borrarse | [9039d70](https://github.com/j4vierlb/PROYECTO-TESIS-/commit/9039d70), incluido en PR #4; los archivos traídos del equipo por el merge no se consideran desarrollo propio |
| 30/09 | Fecha de hoy y navegación de agenda en día de Chile, evitando el recorte UTC de toISOString | [7c9dc17](https://github.com/j4vierlb/PROYECTO-TESIS-/commit/7c9dc17); [PR #9](https://github.com/j4vierlb/PROYECTO-TESIS-/pull/9) |
| 04/10 | Incorporación de los documentos 01 al 10 de Fase 2 y su índice | [8a4e4bd](https://github.com/j4vierlb/PROYECTO-TESIS-/commit/8a4e4bd), también incluido en PR #9 |
| 10/10 | Correcciones de hora chilena, clientes sin coordenadas y Sin asignar, con pruebas y capturas | [1d8fdbd](https://github.com/j4vierlb/PROYECTO-TESIS-/commit/1d8fdbd); [PR #11](https://github.com/j4vierlb/PROYECTO-TESIS-/pull/11) |
| 20/10 | Edición y validaciones del panel; visor del croquis y fotos; pruebas de aislamiento; actualización documental y acta para firma | [676a885](https://github.com/j4vierlb/PROYECTO-TESIS-/commit/676a885); [PR #16](https://github.com/j4vierlb/PROYECTO-TESIS-/pull/16) |
| 21/10 | Actualización de la autoevaluación individual 2.2 | [4338c22](https://github.com/j4vierlb/PROYECTO-TESIS-/commit/4338c22) |
| Publicación de Android | Configuración HTTP limitada a desarrollo, guía y evidencias de la ejecución del 21/10 | [4a8a868](https://github.com/j4vierlb/PROYECTO-TESIS-/commit/4a8a868), [17b9634](https://github.com/j4vierlb/PROYECTO-TESIS-/commit/17b9634) y [32900ac](https://github.com/j4vierlb/PROYECTO-TESIS-/commit/32900ac) |

Las PR #4, #9, #11 y #16 están integradas. PR #16 se integró el 21/10 a las
22:56, hora de Chile. El registro de GitHub lo expresa como 22/10 en UTC;
esa diferencia no representa dos integraciones distintas.

## 3. Funcionalidades del panel y verificaciones

| Área | Cambio o comprobación | Evidencia |
| --- | --- | --- |
| Fechas | Mostrar America/Santiago, enviar UTC con zona y conservar el día local, incluidos verano, invierno y medianoche | [Regresión inicial](../Evidencias%20Proyecto/pruebas/Panel_regresion_2026-10-09.md) |
| Clientes | Listado y edición sin coordenadas; null se conserva; coordenadas incompletas se rechazan; duplicados generan conflicto | [Cierre del panel](../Evidencias%20Proyecto/pruebas/Panel_cierre_2026-10-19.md) |
| Operadores | Sin asignar se envía como null; asignación y reasignación restringidas a operadores activos de la empresa | [Cierre del panel](../Evidencias%20Proyecto/pruebas/Panel_cierre_2026-10-19.md) |
| Agenda | Edición y reprogramación persistentes; horario de atención configurado para WhatsApp; separación de una hora para el mismo operador | [Cierre del panel](../Evidencias%20Proyecto/pruebas/Panel_cierre_2026-10-19.md) |
| Conservación | Impedir eliminar clientes con visitas y cancelar visitas conservando croquis y trampas | Caso VIS-002 del [cierre del panel](../Evidencias%20Proyecto/pruebas/Panel_cierre_2026-10-19.md) |
| Interfaz y errores | Permisos, expiración de acceso, formularios conservados ante rechazo, reintentos, doble envío y respuestas antiguas de navegación | [Pruebas del panel](../Evidencias%20Proyecto/frontend/tests/panel.test.jsx) y [API](../Evidencias%20Proyecto/frontend/tests/api.test.js) |
| Diseño adaptable | Agenda y clientes en escritorio y anchos móviles de 320 y 390 px, en el navegador probado | [Capturas del panel](../Evidencias%20Proyecto/pruebas/capturas/panel_2026-10-19/) |
| Croquis web | Acceso de solo consulta desde la visita; selección mapa/listado; trampas confirmadas, sugeridas y retiradas diferenciadas | [Informe del visor](../Evidencias%20Proyecto/pruebas/Croquis_web_2026-10-19.md) |
| Fotografías | Descarga con Authorization, sin token en URL; control de destinos y errores; fotos privadas de las trampas | [Informe del visor](../Evidencias%20Proyecto/pruebas/Croquis_web_2026-10-19.md) y [código del visor](../Evidencias%20Proyecto/frontend/src/CroquisViewer.jsx) |
| Maps real | Mapa satelital, selección y foto privada comprobados en localhost:5173 tras corregir el referente autorizado | [Prueba manual de Maps](../Evidencias%20Proyecto/pruebas/Croquis_maps_real_2026-10-20.md) |
| Acceso por empresa | Admin y coordinador de A y B, visitas, croquis y fotos, con y sin token | [Verificación del PR #14](../Evidencias%20Proyecto/pruebas/Verificacion_PR14_2026-10-20.md) |

La comprobación manual de concurrencia del panel obtuvo una creación 201 y un
conflicto 409 para dos solicitudes simultáneas al mismo operador. No prueba
por sí sola concurrencia conjunta entre panel y WhatsApp, ni sustituye una
prueba de carga. La separación horaria tampoco calcula distancias o rutas.

## 4. Resultados de pruebas: cortes separados, no acumulables

| Fecha / alcance | Resultado registrado | Interpretación |
| --- | --- | --- |
| 09/10, tres correcciones del panel | 51 aprobadas: 29 frontend y 22 backend | Ejecución histórica; el backend incluyó 6 de contrato, 5 de fecha y 11 PostGIS |
| 19/10, mejoras del panel antes del visor y aislamiento | 110 aprobadas: 59 frontend y 51 backend | Corte histórico explicado en el reporte de cierre |
| 20/10, conjunto verificado tras PR #14 | 205 aprobadas: 98 frontend y 107 backend; 0 fallas, errores u omisiones | Resultado completo de esa ejecución, no afirmación sobre cualquier versión posterior |
| Incluidas en las 107 backend | 30/30 de aislamiento | 12 respuestas propias 200, 12 ajenas 403 y 6 sin token 401; no se agregan nuevamente a 205 |
| 21/10, preparación Flutter/Android | 16 pruebas Flutter existentes aprobadas, según la guía | Registro de preparación; no todas son pruebas de dispositivo y no se adjunta log primario en el paquete Android |

Las suites evolucionaron y comparten casos. **No corresponde sumar
51 + 110 + 205 como pruebas distintas**, ni agregar las 30 de aislamiento de
nuevo. Los conteos completos también incluyen pruebas del equipo; se informa
qué se ejecutó, no que Juan escribió por sí solo todos sus casos.

Fuentes primarias conservadas para el corte de 205:

- [JSON backend: 107 aprobadas](../Evidencias%20Proyecto/pruebas/resultados_backend_pr14_2026-10-20.json).
- [JSON frontend: 98 aprobadas](../Evidencias%20Proyecto/pruebas/resultados_frontend_pr14_2026-10-20.json).
- [JSON de los 30 casos de aislamiento](../Evidencias%20Proyecto/pruebas/resultados_aislamiento_empresas_pr14_2026-10-20.json).
- [Entorno, comandos y límites de la ejecución](../Evidencias%20Proyecto/pruebas/Verificacion_PR14_2026-10-20.md).

Las pruebas PostGIS utilizaron bases aisladas y rollback por caso. Las pruebas
React simulan HTTP y algunas de contrato simulan SQL: no se presentan todas
como extremo a extremo. La comprobación manual de navegador sí utilizó API
y base reales con datos sintéticos, separada del conteo automatizado.

Se conserva el [resultado inicial de aislamiento](../Evidencias%20Proyecto/pruebas/Aislamiento_empresas_2026-10-20.md),
con ocho fallos, junto con la verificación posterior 30/30. También se conserva
el rechazo inicial del referente de Maps. No se borran los fallos históricos
ni se cambian expectativas para presentarlos como aprobados desde el principio.

Como evidencia compartida adicional, el script del equipo tiene
[32 resultados aprobados el 21/10 a las 23:04](https://github.com/j4vierlb/PROYECTO-TESIS-/blob/1ece7939f35c71a502bf6f3151d888b6f45fe235/pruebas/resultados_2026-10-21_2304.md),
publicados con el [PR #18 de Javier](https://github.com/j4vierlb/PROYECTO-TESIS-/pull/18).
Se citan como ejecución del equipo, no como 32 pruebas propias ni parte de una
nueva ejecución conjunta con las suites anteriores.

Al elaborar este índice también se observó integrado el PR #17 de IA y
WhatsApp. Las pruebas históricas aquí enlazadas no validan automáticamente esa
integración ni certifican el estado completo del `main` más reciente. En esta
publicación documental no se repitieron las suites funcionales.

## 5. Android: preparación y evidencia propia

El aporte de Juan fue habilitar la compilación y ejecución local del código
Flutter existente, mantener sus dependencias, configurar la excepción HTTP
solo para debug y documentar el procedimiento y los pendientes.

- [Guía de herramientas, comandos y matriz de pruebas](../Evidencias%20Proyecto/app-movil/ANDROID.md).
- [Registro con siete capturas originales y sus límites](../Evidencias%20Proyecto/pruebas/android_2026-10-21/README.md).
- [Hashes de las capturas](../Evidencias%20Proyecto/pruebas/android_2026-10-21/SHA256SUMS.txt).

En el emulador Android 16 / API 36 se comprobó login válido, agenda vacía,
historial, visita completada, croquis existente en modo consulta, restauración
de sesión vigente al relanzar y regreso al login después de cerrar sesión y
relanzar. No se modificaron clientes, visitas ni trampas durante esas consultas.

El APK debug `1.0.0+1` se compiló con `MAPS_ENABLED=false` y backend local.
El listado de tres trampas no acredita un mapa activo ni una invocación IA.
Se conservó su SHA-256 en el registro, pero el binario, las herramientas y las
claves no se incorporan al repositorio.

Pendientes: clave Android autorizada, mapa real, GPS, cámara, galería,
fotografías privadas, flujos de escritura, recuperación sin red, renovación
de token vencido, teléfono físico y equivalencia con el iPhone usando el mismo
commit, configuración y datos. No se declara una versión release ni equivalencia
funcional completa por el solo hecho de compartir código Flutter.

Actualización posterior al corte inicial: el
[registro Android del 22/10](../Evidencias%20Proyecto/pruebas/android_2026-10-22/README.md)
documenta una nueva compilación con clave Android y Maps activo, mapa satelital
real con tres marcadores y selección T-01, 18 pruebas Flutter y 12 comprobaciones
HTTP separadas. Resuelve el pendiente de configuración y consulta del mapa
Android, no los flujos de GPS, cámara/fotos, escritura ni comparación con iPhone.

El [corte de terreno del 23/10](../Evidencias%20Proyecto/pruebas/android_campo_2026-10-23/README.md)
añade robustez de permisos GPS, recuperación/reintento de fotos y sesión al
código Flutter compartido; no atribuye como nuevas las funciones originales
de cámara/mapa/edición. Registra **50 pruebas Flutter** (18 existentes y 32 nuevas),
16 comprobaciones HTTP aisladas y verificaciones manuales de GPS simulado,
cámara emulada, galería, caída de conexión/reinicio, notas, edición y cierre.
Estos resultados sustituyen los pendientes de esos flujos en emulador, no los
de teléfono físico, comparación con iPhone ni sincronización offline completa.
El código funcional de este corte se identifica con el commit `2df57a5`;
la documentación y las evidencias se publican en su entrega asociada.

## 6. Documentación de Fase 2

Los documentos 01 al 10 se incorporaron juntos en `8a4e4bd`. En `676a885`
se actualizaron y se añadió el acta 11 para firma. Es trabajo de preparación
y mantenimiento de documentación técnica y de gestión, apoyado en los aportes
del equipo; no implica autoría exclusiva de todos los requisitos, modelos o
componentes del proyecto ni representa once commits separados.

| Documento | Contenido preparado o actualizado y límite |
| --- | --- |
| [01 Inicio](../Evidencias%20Proyecto/Evidencias%20de%20documentacion/01_Documento_Inicio_Fase2.docx) | Alcance, estado técnico, restricciones y pendientes |
| [02 Sprint Backlog](../Evidencias%20Proyecto/Evidencias%20de%20documentacion/02_Sprint_Backlog_y_Tablero.docx) | Trabajo del panel/visor y relación con evidencias, sin reemplazar el Product Backlog del equipo |
| [03 Definition of Done](../Evidencias%20Proyecto/Evidencias%20de%20documentacion/03_Definition_of_Done.docx) | Criterios de terminación y comprobación de acceso por empresa |
| [04 Fichas de Sprint](../Evidencias%20Proyecto/Evidencias%20de%20documentacion/04_Fichas_de_Sprint.docx) | Planificación y referencias de avance; no acredita ceremonias no realizadas |
| [05 Retrospectivas](../Evidencias%20Proyecto/Evidencias%20de%20documentacion/05_Retrospectivas.docx) | Observaciones técnicas y aprendizaje, sin inventar actas de reuniones |
| [06 Diseño](../Evidencias%20Proyecto/Evidencias%20de%20documentacion/06_Documento_de_Diseno.docx) | Visor, fotos privadas, configuración de Maps y permisos |
| [07 Pruebas](../Evidencias%20Proyecto/Evidencias%20de%20documentacion/07_Plan_de_Pruebas_y_Evidencias.docx) | Casos, resultados reales por corte y límites de su evidencia |
| [08 Manual técnico](../Evidencias%20Proyecto/Evidencias%20de%20documentacion/08_Manual_Tecnico.docx) | Ejecución local, configuración, migración y precauciones con la base |
| [09 Trazabilidad](../Evidencias%20Proyecto/Evidencias%20de%20documentacion/09_Matriz_de_Trazabilidad.docx) | Relación de requisitos, componentes y verificaciones del visor |
| [10 Innovación y cierre](../Evidencias%20Proyecto/Evidencias%20de%20documentacion/10_Informe_de_Innovacion_y_Cierre.docx) | Resultados y condiciones técnicas/formales aún abiertas |
| [11 Acta para firma](../Evidencias%20Proyecto/Evidencias%20de%20documentacion/11_Acta_Validacion_Cliente_para_Firma.docx) | Instrumento preparado, sin resultados de aceptación ni firmas inventadas |

El [registro de actualización del 20/10](../Evidencias%20Proyecto/Evidencias%20de%20documentacion/Registro_actualizacion_2026-10-20.md)
detalla los cambios y la verificación de contenido y estructura. La revisión
visual de paginación y tablas de esos Word sigue pendiente: no había un
renderizador disponible. Esta publicación no modifica esos once archivos ni
los considera visualmente aprobados.

La [solicitud de validación](../Evidencias%20Proyecto/Evidencias%20de%20documentacion/Solicitud_validacion_Rodrigo_Quiroga.md)
y el acta son preparación para una sesión con Rodrigo Quiroga, no constancia
de que ocurrió. La [autoevaluación 2.2](https://github.com/j4vierlb/PROYECTO-TESIS-/blob/4338c22/Fase%202/Evidencias%20Individuales/Borquez_Juan_2.2_APT122_AutoevaluacionAvance_Fase2.docx)
actualizada está publicada en `main` mediante `4338c22` y se incorporó a `juan`
al integrar `origin/main` el 22/10. La copia local anterior era idéntica; no se
generó una segunda versión ni se atribuyó como una nueva actualización.

La integración del 22/10 también incorpora la reorganización del PR #19:
los once Word y sus registros pasan de `Fase 2/Documentos` a
`Fase 2/Evidencias Proyecto/Evidencias de documentacion`. Se ajustaron los
enlaces de este índice sin modificar los documentos ni sus resultados.

## 7. Atrasos, seguimiento y condiciones de cierre

La evidencia muestra avances concentrados y correcciones de integración, no
una ejecución regular demostrada de todos los sprints planificados. Los
documentos deben distinguir el plan de las actividades realmente registradas.
Los commits y pruebas permiten reconstruir entregas técnicas, pero no probar
reuniones, acuerdos o validaciones que no tienen registro.

Como dificultades verificables figuran las incompatibilidades del panel con
UTC y valores nulos, los permisos entre empresas, las restricciones de Maps y
la preparación del entorno Android. Explican trabajo correctivo e integración;
no bastan por sí solas para atribuirles todo el retraso del calendario.

Para el informe académico final corresponde contrastar fechas planificadas con
las efectivas, reconocer el seguimiento parcial de Scrum y acordar con el
equipo la explicación de las desviaciones. No se deben completar retrospectivas
o actas retroactivamente como si fueran sesiones efectivamente celebradas.

Permanecen abiertos la aceptación formal del cliente, la comparación completa
Android/iPhone y la validación de los flujos que no cubren estas pruebas. El
informe grupal final debe incorporar el estado actualizado y sus apartados en
inglés; no se afirma que esta recopilación los haya completado. La prueba web
de Maps se limita a localhost:5173; no acredita un despliegue remoto, localhost:8080
en la misma repetición, auditoría integral de seguridad ni capacidad productiva.

## 8. Integridad y publicación de esta recopilación

Esta entrega añade configuración Android, guía, capturas originales con hashes
y este índice. Se reutilizan por enlace las evidencias del panel ya publicadas;
no se duplican sus resultados ni se cambian sus fechas. No se incluyen archivos
`.env`, tokens, claves de proveedores, keystores, APK ni respaldos de bases.

Antes de publicar se comprueban enlaces locales, hashes de las capturas,
separación debug/release y archivos seleccionados por commit. El enlace a la
autoevaluación apunta a su commit original publicado en `main`, preservando
la trazabilidad de esa actualización tras integrarla en `juan`.
