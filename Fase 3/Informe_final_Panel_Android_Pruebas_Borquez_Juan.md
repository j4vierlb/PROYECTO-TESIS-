# Informe final del panel web Android documentación y pruebas

**Responsable del aporte** Juan Francisco Bórquez. **Corte** 8 de noviembre de 2026.

Este aporte describe el panel administrativo y el agendamiento, la preparación
y las mejoras de Android, la documentación y las comprobaciones de calidad de
Kill Bichos IA. Se incorpora al informe del equipo junto con las secciones de
arquitectura, datos, aplicación móvil y WhatsApp e IA de los demás integrantes.

La PR #38 quedó fusionada en `main` mediante `38a02a6`. El último corte de
pruebas registrado para este aporte es el 05/11/2026, con **251 pruebas de
backend, 191 de frontend y 204 de Flutter aprobadas**, y ocho comprobaciones de
navegador en una base aislada. El recorrido completo en el Redmi 15C y la
comprobación contra el servidor quedan sujetos a sus registros de ejecución.

## 1 Relevancia del proyecto

Kill Bichos necesita coordinar solicitudes de servicio, clientes, visitas y
trabajo de técnicos en terreno. El panel permite a los usuarios administrativos
consultar una agenda común, modificar asignaciones y fechas, y revisar el
registro de una visita. La aplicación móvil conecta ese trabajo con el croquis,
las trampas y las fotografías registradas por el técnico.

El aporte del panel fue convertir esa información en operaciones consultables
y verificables. Se abordaron casos que afectan directamente el trabajo diario,
como fechas interpretadas en UTC, visitas sin técnico asignado, clientes cuya
dirección todavía no tiene una ubicación confirmada y fallos de conexión.
La documentación y las pruebas permiten revisar cómo responde el sistema en
esos casos y repetir las comprobaciones durante una entrega.

Las áreas abordadas fueron desarrollo de aplicaciones web y móviles, integración
de servicios, aseguramiento de calidad y documentación técnica. El beneficio
operativo esperado es facilitar la coordinación y la consulta de información.
La reducción de tiempos o costos requiere una medición posterior con la empresa.

## 2 Objetivos del aporte

El objetivo fue implementar y verificar herramientas administrativas conectadas
con la operación en terreno y dejar evidencia suficiente para revisar la entrega.

Los objetivos específicos fueron gestionar clientes y visitas desde el panel,
presentar fechas en horario de Chile, consultar croquis y fotos con control de
acceso, habilitar la ejecución de la aplicación compartida en Android y registrar
las pruebas y limitaciones de cada incremento. También se preparó la documentación
de diseño, trazabilidad, operación y validación de la empresa.

## 3 Metodología y ajustes

Se trabajó con una planificación inicial de once sprints y entregas incrementales
revisadas mediante Git y pull requests. Para cada cambio se contrastó el
comportamiento con los contratos de la API, se ejecutaron las pruebas pertinentes
y se conservaron reportes o capturas con fecha.

La ejecución requirió ajustes respecto de la cadencia planificada. La integración
de ramas, la corrección de permisos, la preparación del entorno Android y la
configuración de servicios externos desplazaron actividades hacia el cierre.
El seguimiento se reconstruye mediante los commits, las revisiones y las
ejecuciones archivadas. Las fichas conservan los objetivos originales de los
sprints y los registros de resultados indican cuándo se verificó cada capacidad.

Este procedimiento permitió atender primero errores que podían afectar datos
o impedir la demostración, y después completar la integración y las evidencias.
Las reuniones y decisiones del cliente se documentan mediante sus propios
registros, mientras las pruebas técnicas describen el entorno que se utilizó.

## 4 Desarrollo y decisiones técnicas

### 4 1 Panel administrativo y agendamiento

El panel se implementó con React y Vite y consume la API FastAPI. Permite
consultar agenda por día y operador, administrar clientes, crear visitas,
reprogramarlas, modificar notas y cambiar asignaciones. La opción Sin asignar
se representa con `operador_id: null`, según el contrato de la API.

Las fechas se presentan e interpretan mediante `America/Santiago` y se envían
al backend en UTC. Las pruebas incluyen verano, invierno y cambios de día.
Las reglas de agendamiento utilizan los horarios configurados para la operación
y comprueban conflictos de un mismo técnico. Cancelar una visita conserva su
croquis y trampas. La eliminación de un cliente con visitas se rechaza para
conservar su historial.

Se incorporaron controles de cargas, reintentos, doble envío y respuestas
atrasadas, además de mensajes comprensibles ante pérdida de sesión o rechazo de
la API. La portada pública incluye información de la empresa y acceso al Sandbox
mediante botón y QR. La navegación permite volver a esa portada conservando la
sesión. Una sesión activa abre el panel y un login inactivo vuelve a la portada
tras cinco minutos. El enlace de restablecimiento mantiene su prioridad.

### 4 2 Direcciones croquis y fotografías

El formulario de clientes solicita una dirección en lugar de exigir coordenadas.
El backend intenta confirmar calle, número y comuna o ciudad de Chile. Si el
resultado es impreciso, el cliente queda con ubicación pendiente. Al corregir la
dirección se reintenta la búsqueda y se descarta un punto anterior que ya no
corresponde a la dirección editada.

El panel ofrece un visor de croquis por visita. Muestra trampas y fotografías
privadas y conserva las retiradas para consultar el historial. El visor utiliza
GET y el token viaja en el encabezado Authorization. La API comprueba la empresa
y el rol. El trabajo en terreno permanece a cargo del técnico.

### 4 3 Recuperación de contraseña y gestión de técnicos

La recuperación del panel solicita el correo vinculado y envía un enlace temporal
cuando el servicio SMTP está configurado. El formulario exige escribir dos veces
la nueva clave. El backend guarda el hash del token, comprueba su vencimiento y
consumo único, y revoca las sesiones anteriores después del cambio.

El equipo incorporó el rediseño y la sección Equipo. Se verificaron su integración,
disposición y operaciones con cuentas sintéticas. El administrador puede crear,
editar, desactivar y reactivar técnicos de su empresa. Las pruebas comprobaron
que desactivar rechaza el ingreso y el token anterior, y que reactivar permite
un nuevo ingreso. La implementación compartida conserva la autoría de sus
respectivos integrantes.

### 4 4 Preparación y mejoras de Android

Android utiliza los mismos archivos Flutter y Dart que iOS. Mi aporte incluyó
preparar Flutter, Java y el SDK Android, configurar los mapas y el acceso al
backend, compilar APK de prueba y verificar su firma y parámetros.

Se trabajó en recuperación de sesión, manejo de fotografías pendientes,
separación por cuenta, persistencia de las fotos fuera de la caché temporal,
tratamiento de URLs inválidas y alternativas de ubicación. También se incorporó
el pin rojo del cliente y el tratamiento de ubicaciones pendientes. Estas mejoras
se integraron con la aplicación móvil y el modo offline desarrollados por el equipo.

El modo offline guarda información previamente consultada en SQLite y encola
cambios y fotos para sincronizarlos. Los reintentos utilizan identificadores que
evitan duplicar trampas. La primera descarga y las sugerencias de IA requieren
conexión. El bloqueo de cierre por una foto pendiente tiene alcance local en el
teléfono, según la decisión de entrega registrada.

El APK `1.0.0+5` se compiló para `http://192.168.1.12:8000`, con Maps activo y
la misma firma que el anterior. La dirección del backend queda fijada al compilar.
La prueba contra el servidor requerirá su URL y una compilación destinada a ella.

### 4 5 Documentación

Se actualizaron los once Word de Fase 2 que cubren inicio, backlog, Definition of
Done, fichas, retrospectivas, diseño, pruebas, manual técnico, trazabilidad,
cierre y acta. Se incorporaron offline, WhatsApp saliente, portada, Equipo,
geocodificación en Chile y recuperación de contraseña.

Se corrigieron referencias que presentaban como futuras capacidades ya
implementadas y se conservaron los resultados históricos con sus fechas. Los
documentos se renderizaron para revisar tablas y paginación. El acta preparada
contiene nueve escenarios para completar durante la sesión de la empresa.

## 5 Evidencias y resultados

| Evidencia | Resultado y fecha | Alcance |
| --- | --- | --- |
| Backend | 251/251 el 05/11/2026 | Reglas, contratos e integración con bases PostGIS aisladas, incluidas pruebas de seguridad y gestión de técnicos. |
| Frontend | 191/191 el 05/11/2026 | Interacción, navegación, recuperación, croquis y casos con HTTP simulado. |
| Flutter | 204/204 el 05/11/2026 | Modelos, sesiones, fotos, ubicación, persistencia y cola offline. |
| Navegador | 8/8 el 05/11/2026 | Edge con API real y base aislada a 1440 y 390 px. Alta, edición, desactivación y reactivación de técnicos. |
| Redmi físico | Recorrido integral por registrar | Pin rojo observado por Juan en una compilación anterior. El recorrido de la versión 1.0.0+5 se completará con su bitácora. |
| Servidor | URL pendiente al 08/11/2026 | Comprobaciones de panel y app preparadas para ejecutar cuando el servidor esté disponible. |

Las suites evolucionaron y comparten casos. Los cortes históricos se consultan
por separado y los resultados de laboratorio se relacionan con el entorno y la
versión que los produjeron.

La primera repetición del backend del 05/11 detectó 19 errores por falta de Node
en el contenedor de pruebas. Después de preparar ese entorno, la ejecución
completó las 251 pruebas. Los cambios de red también requirieron recompilar el
APK para mantener su dirección de backend coherente con la del computador.

La validación del cliente se completará mediante la sesión con Rodrigo Quiroga,
los resultados por escenario y el acta correspondiente. La bitácora del Redmi y
la comprobación remota permitirán evaluar cámara, permisos, conectividad y
sincronización en esos entornos.

## 6 Aprendizajes y proyección profesional

El trabajo permitió relacionar el desarrollo de interfaces con contratos de API,
reglas operativas y protección de datos. Una pantalla que conserva su formulario
ante un error, una hora que corresponde al día de Chile o una foto que sobrevive
a una pérdida de sesión son decisiones que requieren comprobar el flujo completo.

La preparación de Android y la documentación reforzaron la importancia de
reproducir las instalaciones y de identificar la configuración de cada entrega.
También permitieron distinguir una prueba unitaria, una integración con base
real, una comprobación de dispositivo y una validación de usuario.

Como líneas de profundización se identifican el desarrollo de aplicaciones
integradas, la automatización de pruebas, la observación del comportamiento en
producción y la operación de aplicaciones móviles con conectividad limitada.
Estas conclusiones técnicas pueden complementarse con la reflexión personal
de Juan al integrar el informe grupal.

## Referencias internas

- [Bitácora del cierre y resultados](../Fase%202/Evidencias%20Proyecto/pruebas/cierre_fase2_2026-11-05/README.md).
- [Recorrido pendiente del Redmi](../Fase%202/Evidencias%20Proyecto/pruebas/cierre_fase2_2026-11-05/recorrido_redmi.md).
- [Plan de comprobación en servidor](../Fase%202/Evidencias%20Proyecto/pruebas/cierre_fase2_2026-11-05/validacion_servidor.md).
- [Documentación del panel](../Fase%202/Evidencias%20Proyecto/frontend/README.md).
- [Preparación y cortes de Android](../Fase%202/Evidencias%20Proyecto/app-movil/ANDROID.md).
- [Entregables Word de Fase 2](../Fase%202/Evidencias%20Proyecto/Evidencias%20de%20documentacion/).
- [PR #38](https://github.com/j4vierlb/PROYECTO-TESIS-/pull/38).
