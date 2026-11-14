# Recorrido físico de cierre en Redmi

**5 de noviembre de 2026.** Redmi 15C de Juan, APK de pruebas `1.0.0+5` y
computador en la misma red. La comprobación física se registra por paso y queda
separada de las pruebas automatizadas y del viewport móvil emulado.

Usar la visita de prueba **Cliente QA Cierre Android**, asignada al técnico de
prueba. Abrir la agenda y el croquis con conexión antes del ensayo offline.
Registrar cambios y fotos de prueba, sin datos de clientes reales.

| ID | Comprobación | Resultado físico |
| --- | --- | --- |
| AND-01 | Abrir `/docs` desde el teléfono e iniciar sesión en el APK con el técnico de prueba. | Por registrar |
| AND-02 | Abrir agenda, seleccionar la visita QA y revisar estado y hora. | Por registrar |
| AND-03 | Abrir croquis, verificar mapa y pin del cliente, y agregar una trampa. | Por registrar |
| AND-04 | Tomar una foto de prueba, guardarla y comprobarla al reabrir el croquis. | Por registrar |
| AND-05 | Cortar la conexión, comprobar «Sin conexión» y guardar una trampa o nota pendiente. | Por registrar |
| AND-06 | Reconectar, comprobar que baja el contador de pendientes y que el cambio aparece una sola vez. | Por registrar |
| WEB-FIS-01 | En Chrome del Redmi, entrar a la vista de pruebas, revisar Agenda, Clientes, WhatsApp y Equipo, y comprobar que se pueden operar los controles. | Por registrar |
| WEB-FIS-02 | Crear o editar un técnico de prueba en Equipo y revisar el formulario y la confirmación. | Por registrar |

Para cada fallo, anotar hora, versión, pantalla, acción, mensaje observado,
pasos de reproducción y si se repitió. Una captura puede acompañar el resultado
si muestra solo los datos sintéticos del ensayo. El acta de la empresa es un
registro separado de la prueba técnica de Juan.

## Seguimiento del 8 de noviembre de 2026

Juan indicó que realizará el recorrido posteriormente. Los resultados físicos
de AND-01 a AND-06 y WEB-FIS-01/02 siguen por registrar. La IP del computador
comprobada en esta fecha es `192.168.1.12`, que coincide con la compilación
`1.0.0+5`. La visita QA del 05/11 corresponde a esa fecha. Antes de la nueva
prueba, preparar una visita de prueba para el día elegido y confirmar el técnico
asignado. Comprobar la agenda con señal antes de cortar la conexión.

Para cada fila, registrar quién ejecutó, fecha/hora de Chile, versión del APK o
navegador, resultado observado y referencia a la captura. Utilizar Aprobado,
Falló o Bloqueado según lo observado. Mantener Por registrar hasta ejecutar.

| Evidencia | Dato por completar |
| --- | --- |
| APK instalado | Versión y hash del archivo utilizado |
| Agenda y croquis | Cliente/visita sintéticos y técnico de prueba |
| Foto | Confirmación de subida y de consulta tras reabrir |
| Offline | Pendientes antes/después y cantidad de registros tras sincronizar |
| Chrome del Redmi | URL, versión del navegador y captura de Agenda/Equipo |
| Fallos | Acción, mensaje, pasos y si se pudo repetir |

La comprobación contra el servidor tiene su
[plan y registro propios](validacion_servidor.md).

## Prueba con el servidor del 14 de noviembre de 2026

Juan usó el Redmi 15C con el APK `1.0.0+6` y la cuenta de prueba
`tecnico1@killbichos.cl`. La aplicación apuntaba a la API HTTPS de Kill Bichos.
El inicio de sesión y la agenda del 13/11 quedaron corroborados por Javier.
El 14/11, Juan creó una visita de prueba y abrió su croquis.

| Hora de Chile | Qué se observó | Evidencia |
| --- | --- | --- |
| 01:06 | El mapa muestra el pin rojo del cliente y dos marcadores de trampa. La franja dice «Sin conexión · 2 cambios por enviar». | Captura original del mapa, conservada localmente. |
| 01:07 | T-01 (cebadero) y T-02 (trampa de pegamento) aparecen confirmadas y con una foto de prueba cada una. Juan reportó haber recuperado la conexión. | [Trampas confirmadas con fotos](redmi_2026-11-14/01_trampas_confirmadas_con_fotos.jpeg). |
| 01:13 | Las dos trampas aparecen retiradas, conservan sus fotos y se ve el aviso «T-02 retirada». | [Trampas retiradas con fotos](redmi_2026-11-14/02_trampas_retiradas_con_fotos.jpeg). |
| 01:14 | El mapa muestra el pin rojo del cliente y los dos marcadores morados de las trampas retiradas. | Captura original del mapa, conservada localmente. |

El croquis del panel desplegado mostró T-01 y T-02 en estado **Retirada**.
Se abrió y cargó la foto de cada una desde el servidor. Javier corroboró en la
base y en los archivos las altas, las fotos y el estado retirado de ambas
trampas. [UUID y horas del servidor](validacion_servidor.md#registros-corroborados-por-javier-el-14-de-noviembre).

Juan declaró que agregó una trampa sin conexión y después se reconectó. La
captura de la 01:06 acredita los dos cambios pendientes en el Redmi. Tras el
reinicio del backend se perdieron los logs de peticiones de esa ventana. Quedó
sin verificar cuáles fueron las dos operaciones de la cola y si se aplicaron
una sola vez.

Las dos capturas del mapa muestran una ubicación precisa y se conservan
fuera del repositorio. Estas huellas identifican los originales recibidos.

| Captura | SHA-256 |
| --- | --- |
| 01:06 · Mapa y cola offline | `b581bbc995ead90f273d97dec0876677d031ef5e18951577763760f3129ad67f` |
| 01:14 · Mapa y trampas retiradas | `b1b9b37a49755ec22d3bbd393aa1438d71ed201fe8197a3341864075aaff42ff` |
