# Comprobación del panel y Android contra el servidor

**Plan preparado el 8 de noviembre de 2026.** La URL del servidor está pendiente
de recibir de Javier. Los casos siguientes se ejecutarán después de confirmar
el despliegue y registrar su versión.

## Datos de la ejecución

| Dato | Valor al preparar el plan |
| --- | --- |
| URL pública del panel | Pendiente |
| URL pública de la API | Pendiente |
| Commit desplegado | Pendiente de confirmar |
| Versión y hash del APK remoto | Pendiente de compilar para la URL remota |
| Dispositivo | Redmi 15C |
| Navegadores | Chrome del Redmi y navegador de escritorio |
| Cuentas | Administrador y técnico de prueba del entorno, por confirmar |
| Fecha y persona que ejecuta | Por registrar al ejecutar |

El APK local `1.0.0+5` utiliza `http://192.168.1.12:8000`. Para comprobar el
servidor se debe compilar con su URL de API. Registrar firma y versión para
instalarlo como actualización y revisar los pendientes de sincronización antes
de cambiar de entorno. Usar las cuentas y los registros de prueba del servidor.

## Casos del plan original

| ID | Acción | Resultado esperado | Estado al preparar el plan |
| --- | --- | --- | --- |
| SRV-01 | Abrir portada y `/health` en las URL confirmadas. | Servicios accesibles y versión identificada. | Pendiente de URL |
| SRV-02 | Iniciar sesión en el panel, recargar, volver a portada y entrar de nuevo. | Acceso correcto y sesión conservada. | Pendiente de URL |
| SRV-03 | Filtrar agenda y crear una visita sintética con técnico y otra Sin asignar. | Día/hora de Chile, validaciones y persistencia correctos. | Pendiente de URL |
| SRV-04 | Crear un cliente con dirección completa y comprobar recuperación de una ubicación pendiente. | Punto confirmado o aviso pendiente; reintento al corregir. | Pendiente de URL |
| SRV-05 | Consultar croquis y una foto desde el panel. | Mapa o aviso comprensible, lista de trampas y foto autorizada. | Pendiente de URL |
| SRV-06 | Crear y editar un técnico sintético; desactivar y reactivar. | Acceso y datos acordes con las reglas de Equipo. | Pendiente de URL |
| SRV-07 | Abrir el panel en Chrome del Redmi y operar los mismos formularios. | Controles accesibles y resultado persistente. Guardar captura. | Pendiente de URL |
| SRV-08 | Instalar APK remoto e ingresar con un técnico de prueba. | Agenda del servidor para esa cuenta. | Pendiente de URL |
| SRV-09 | Abrir croquis, agregar trampa y tomar foto en la app. | Registro y foto visibles al volver a consultar. | Pendiente de URL |
| SRV-10 | Precargar agenda/croquis, cortar red, registrar cambio y reconectar. | Cola visible y sincronización de una sola operación por cambio. | Pendiente de URL |
| SRV-11 | Recuperar contraseña de una cuenta de prueba con correo accesible. | Enlace al panel público y nueva clave confirmada, si SMTP está habilitado. | Pendiente de URL |
| SRV-12 | Abrir QR y revisar conversación y avisos aplicables de WhatsApp. | Webhook del servidor, conversación y estado de entrega registrados. | Pendiente de URL |

## Validación en Redmi 15C del 13 y 14 de noviembre de 2026

Juan Francisco Bórquez usó un Redmi 15C y confirmó la cuenta de prueba
`tecnico1@killbichos.cl`. Se verificó que el APK de desarrollo `1.0.0+6`
se compiló con Google Maps y la API `https://killbichos-api.duckdns.org`.
El SHA-256 del APK entregado es
`5cb5af8e8effd88ccb60dc5be16e390f81aebdf10776b01d0301970fc50a6b8b`.

| Caso | Fecha | Resultado y evidencia |
| --- | --- | --- |
| SRV-08 | 13/11 | Juan confirmó que pudo iniciar sesión. Javier corroboró el login y la agenda en su revisión del servidor. |
| SRV-09 | 13/11 | Juan confirmó que cargaron el mapa y el pin rojo del cliente. El croquis volvió a mostrar ambos en la prueba del 14/11. |
| SRV-09 | 14/11 | Juan creó una visita de prueba y registró un cebadero (T-01) y una trampa de pegamento (T-02). A la 01:07, el Redmi mostraba ambas confirmadas y con foto. [Captura del Redmi](redmi_2026-11-14/01_trampas_confirmadas_con_fotos.jpeg). |
| SRV-09 | 14/11 | A la 01:13, el Redmi mostraba ambas trampas retiradas y con sus fotos. Se abrió el croquis de esa visita en el panel desplegado y se corroboró que ambas seguían registradas como retiradas. Las dos fotos cargaron desde el servidor. [Captura del Redmi](redmi_2026-11-14/02_trampas_retiradas_con_fotos.jpeg). |
| SRV-10 | 14/11 | Juan reportó que agregó una de las trampas sin conexión y luego se reconectó. A la 01:06, el Redmi mostraba «Sin conexión · 2 cambios por enviar». A la 01:07, ambas trampas aparecían confirmadas con foto y la franja de pendientes ya no se mostraba. El estado final se corroboró en el panel. Queda pendiente identificar qué operaciones llegaron desde la cola y comprobar su ejecución única en los registros del servidor. |

Las horas son las que muestra el teléfono, en hora de Chile. El detalle del
recorrido y las referencias a las capturas del mapa se conservan en la
[bitácora del Redmi](recorrido_redmi.md#prueba-con-el-servidor-del-14-de-noviembre-de-2026).

## Comparación con el entorno local

Registrar diferencias de CORS, URL de API, HTTPS, referentes de Maps, permisos
de fotos, horarios, cuentas, datos y entrega de mensajes. Abrir la portada desde
el teléfono debe permitir que sus peticiones de API lleguen al servidor.

| Caso | Versión local de referencia | Resultado local | Resultado remoto | Diferencia y acción |
| --- | --- | --- | --- | --- |
| Por registrar | PR #38 integrada; evidencias del 05/11 | Consultar el caso y su entorno en la bitácora | Por ejecutar | Por registrar |

## Registro de incidencias

Por cada fallo, guardar fecha y hora de Chile, ID del caso, dispositivo/navegador,
versión, pasos, mensaje o código HTTP, efecto sobre los datos y repetición del
problema. Adjuntar captura con datos de prueba cuando corresponda. Los resultados
remotos se incorporan como una ejecución nueva y conservan el registro local.
