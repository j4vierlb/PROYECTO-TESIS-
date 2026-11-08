# Guion de demostración para Rodrigo Quiroga

**Preparación del 8 de noviembre de 2026.** Responsable de coordinación Juan
Bórquez. Duración propuesta 30 minutos, por acordar con Rodrigo.

La sesión busca revisar el flujo de Kill Bichos IA con datos de prueba y recoger
las observaciones de la empresa. El
[acta preparada](11_Acta_Validacion_Cliente_para_Firma.docx) contiene los nueve
escenarios VAL-01 a VAL-09. Al 08/11 todos mantienen el estado por evaluar.

## Preparación antes de la sesión

1. Acordar con Rodrigo fecha, horario y modalidad utilizando la
   [solicitud preparada](Solicitud_validacion_Rodrigo_Quiroga.md).
2. Definir si la demostración se realizará contra el servidor o en la red local.
   Anotar URL de panel y API, commit y versión del APK. La URL remota está
   pendiente de recibir al 08/11.
3. Ejecutar el recorrido de la app y de Chrome en el Redmi, y preparar una visita
   de prueba para el día de la sesión. La visita del 05/11 pertenece al historial
   de esa fecha. Utilizar una fecha admitida para probar el agendamiento.
4. Tener el acta abierta o impresa, capturas de las comprobaciones técnicas y un
   lugar para registrar observaciones por escenario.
5. Verificar acceso a Maps, conexión para sugerencias IA, unión vigente al
   Sandbox y estado de SMTP. Una función que dependa de un servicio sin configurar
   debe figurar con esa condición al presentar su resultado.

## Cuentas y datos de prueba

| Rol | Cuenta del seed local | Uso |
| --- | --- | --- |
| Administrador | `admin@killbichos.cl` | Agenda, clientes, visor y administración de Equipo. |
| Técnico | `tecnico1@killbichos.cl` | Agenda asignada, visita, croquis, foto y cola offline. |
| Técnico creado en la sesión | Correo sintético nuevo en la base de pruebas | Demostrar alta, edición, desactivación y reactivación. |
| Cliente | Registro sintético preparado para la sesión | Dirección, visita y consulta de historial. |

Comprobar qué cuentas existen en el servidor antes de utilizarlo. Las claves
de prueba se consultan en el manual del entorno y se entregan a los participantes
por el canal acordado. La demostración de recuperación debe usar una cuenta
de prueba con un correo accesible para quien la ejecuta.

## Recorrido propuesto

| Tiempo | Acta | Acción de demostración | Comportamiento esperado |
| --- | --- | --- | --- |
| 0–3 min | VAL-01 | Abrir portada, ingresar y filtrar agenda por día y técnico. | Sesión correcta y visitas del filtro elegido. |
| 3–6 min | VAL-02 | Guardar una dirección completa y otra que quede pendiente. Corregir esta última. | Punto confiable o estado pendiente, y reintento al corregir. |
| 6–9 min | VAL-03 | Crear visita con técnico o Sin asignar y recargar. | Fecha chilena y asignación persistidas. |
| 9–15 min | VAL-04 | Consultar mapa y fotos en el panel. En la app, revisar sugerencias exteriores y registrar trampa y foto. | Consulta web y registro técnico con revisión humana. |
| 15–17 min | VAL-05 | Revisar historial y cancelar una visita sintética preparada. | Estado actualizado y croquis/trampas conservados. |
| 17–20 min | VAL-06 | Abrir QR, enviar unión al Sandbox y conversar. Revisar avisos y respuesta humana cuando corresponda. | Mensajes y visita visibles según la configuración. Registrar el estado de entrega. |
| 20–23 min | VAL-07 | Crear, editar, desactivar y reactivar al técnico sintético. | Datos persistidos y acceso acorde con el estado. |
| 23–27 min | VAL-08 | Con agenda/croquis precargados, registrar un cambio sin red y reconectar. | Franja y pendientes visibles, envío y ausencia de duplicados. |
| 27–30 min | VAL-09 | Solicitar recuperación en una cuenta de prueba y confirmar nueva clave. | Recepción por SMTP, enlace válido de un uso y acceso con la nueva clave. |

Los tiempos se ajustan a las observaciones del cliente. Si la demostración
necesita más tiempo, registrar qué escenarios se alcanzaron y acordar la
continuación. La lectura de un caso en el guion se distingue de su ejecución.

## Qué registrar durante la sesión

Para cada escenario, anotar resultado, observación del cliente y evidencia
correspondiente. Usar los estados del acta y registrar cualquier dependencia
externa o error reproducible. Identificar la versión y los datos utilizados
para poder repetir un caso observado.

Al finalizar, repasar con Rodrigo las observaciones y las acciones pendientes.
La decisión y los campos de identificación del acta se completan con el cliente
en la sesión. Juan gestiona el envío de la solicitud y la coordinación por su
canal habitual.
