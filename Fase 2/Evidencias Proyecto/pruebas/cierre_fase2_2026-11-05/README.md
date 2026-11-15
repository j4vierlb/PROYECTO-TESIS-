# Bitácora de pruebas de cierre de Fase 2

**5 de noviembre de 2026, hora de Chile.** Corte de software `c90c58a` en
`juan`, que contiene `origin/main` en `95a2844` y la navegación de la PR #38.
Se separan resultados automatizados, comprobaciones con navegador y aceptación
de la empresa. Los conteos de cortes previos quedan como historial.

## Ejecuciones automatizadas

| Suite | Resultado | Entorno y evidencia |
| --- | --- | --- |
| Backend | **251/251**, 0 fallos y 0 omisiones | `python -B -m unittest discover -s tests -v`, con Python y Node. PostgreSQL/PostGIS aislado, `panel_regression` y `croquis_regression`, esquema y migraciones aplicados. [Resultados](backend.log). |
| Panel | **191/191**, 13 archivos | `npm test -- --reporter=dot`. Vitest simula HTTP. [Resultados](frontend.log). |
| Flutter | **204/204** | `flutter test --no-pub --reporter expanded --dart-define=API_BASE_URL=http://192.168.1.12:8000 --dart-define=MAPS_ENABLED=true`. [Resultados](flutter.log). |

La primera ejecución del backend detectó 19 errores por falta de Node en el
contenedor de pruebas, todos en casos que ejecutan JavaScript. La repetición con
Node y las fuentes requeridas completó las 251 pruebas. Se conserva el resultado
del intento inicial en el resumen de incidencias de abajo.

| ID | Función | Evidencia automatizada |
| --- | --- | --- |
| OFF-01 | Agenda precargada, cola offline, reintento y separación de cuentas | `offline_sync_test.dart`, `offline_ui_test.dart`, `sqlite_local_store_test.dart` |
| WA-OUT-01 | Avisos, recordatorios, respuesta humana y estado de entrega | `test_whatsapp_saliente.py`, `test_whatsapp_postgis.py`. Los casos externos usan respuestas simuladas de Twilio. |
| WA-QR-01 | Portada, navegación y contenido del QR al Sandbox | `public-home.test.jsx`, `public-home-motion.test.jsx`. Juan reportó que el QR abrió la conversación y pudo conversar con el agente en octubre. |
| EQ-01 | Alta, edición, permisos y revocación de sesión de técnicos | `equipo.test.jsx`, `test_operadores_panel.py`, más comprobaciones con navegador descritas abajo. |
| GEO-CL-01 | Direcciones en Chile, ubicación pendiente, reintento y pin del cliente | `test_geocoding.py`, `test_panel_postgis.py`, `panel.test.jsx`, `client_map_marker_test.dart`. |
| AUTH-RESET-01 | Enlace de un uso, confirmación de nueva clave y revocación de sesiones | `test_password_reset.py`, `password-recovery.test.jsx`. La entrega de correo real requiere SMTP. |
| IA-CROQ-01 | Propuestas exteriores, conversión a coordenadas y respaldo por reglas | `test_croquis_agent.py`, `test_croquis_sugerencia.py`. No se certifica precisión en terreno a partir de estas pruebas. |
| WEB-NAV-01 | Sesión activa, botón de portada y retorno por inactividad | `navigation-idle.test.jsx`, `merge-integration.test.jsx`. La inactividad se mide con reloj simulado. |

## Panel administrativo y Equipo

Edge con Playwright contra el frontend Vite y FastAPI/PostGIS de una base
`cierre_demo` aislada. Se inició sesión con la cuenta administrativa de prueba.
Se crearon dos operadores sintéticos en esa base para comprobar el alta real.
La vista móvil es un navegador con tamaño y entrada táctil emulados.

| Caso | PC 1440 × 900 | Vista móvil 390 × 844 | Resultado observado |
| --- | --- | --- | --- |
| Portada, ingreso y agenda del rediseño | WEB-PC-01 | WEB-movil-01 | Ingreso correcto y agenda con la visita precargada de demo. |
| Alta y edición de técnico | WEB-PC-02 | WEB-movil-02 | Se crea la cuenta, inicia sesión por API y el nombre editado se muestra en Equipo. |
| Desactivar y reactivar | WEB-PC-03 | WEB-movil-03 | Login y token anterior rechazados con HTTP 401 tras desactivar. Nuevo ingreso HTTP 200 tras reactivar. |
| Navegación y disposición | WEB-PC-04 | WEB-movil-04 | Se abren Clientes, WhatsApp y Equipo. Regresar a portada conserva sesión. Equipo cabe en el ancho disponible. |

**8/8 comprobaciones de navegador aprobadas.** [Resultados por caso](panel_ui.json).
Capturas con datos sintéticos y contactos de demo ocultos en la captura:
[Agenda PC](agenda_PC.png), [Equipo PC](equipo_PC.png),
[Agenda móvil](agenda_movil.png) y [Equipo móvil](equipo_movil.png).

La prueba física del panel en Chrome del Redmi se coordina en una vista temporal
con proxy a la base aislada. Se registrará el resultado en
[recorrido en el Redmi](recorrido_redmi.md).

## Android

APK de prueba `1.0.0+5`, paquete `com.killbichosia.app_movil`, compilado para
`http://192.168.1.12:8000` y con Maps habilitado. Se verificó la misma firma del
APK anterior, el dominio autorizado por la política HTTP debug y la respuesta
de `/health` desde el PC. SHA-256:
`5fab279ff7e55e38ecda2696e2a1a130829a93138c1bd82dd8ed3fede4d85577`.

Se preparó una visita con cliente sintético **Cliente QA Cierre Android** en la
base local, asignada al técnico de prueba habitual, a las 10:00 del 05/11. El login
y la agenda de ese técnico respondieron HTTP 200 en la comprobación por API.
La compilación y los resultados automatizados se registran aparte de los pasos
que Juan observe físicamente en el [Redmi](recorrido_redmi.md).

## Incidencias y aceptación

| Incidencia | Resultado |
| --- | --- |
| QA-ENV-01 | Primera suite backend, 19 errores `node` no encontrado. Se preparó un entorno con Node. Repetición 251/251 aprobada. |
| QA-ENV-02 | El APK anterior apuntaba a `10.84.89.236`, mientras la IP del PC pasó a `192.168.1.12`. El APK 1.0.0+5 quedó compilado para la IP actual. |
| QA-ENV-03 | Advertencias de Kotlin y versión XML del SDK durante el ensamblado. APK debug generado y firma válida. |

La conformidad de la empresa, los escenarios aceptados y las firmas se completan
en el acta 11 durante la sesión con Rodrigo Quiroga. Los resultados de laboratorio
no completan los campos de aprobación del cliente.

## Seguimiento del 8 de noviembre de 2026

La PR #38 quedó integrada en `main` en `38a02a6`. El registro de las pruebas
anteriores conserva su fecha del 05/11 y el corte `c90c58a` que las produjo.

Juan realizará más adelante la prueba completa en el Redmi y el panel en Chrome.
La URL del servidor aún está pendiente de recibir. Los registros preparados son
el [recorrido físico](recorrido_redmi.md) y la
[comprobación remota](validacion_servidor.md).

La sesión con Rodrigo dispone de un
[guion de nueve escenarios y cuentas de prueba](../../Evidencias%20de%20documentacion/Guion_sesion_Rodrigo_Quiroga.md)
y del acta preparada. La solicitud se gestiona por Juan. Su aporte al informe
final cubre panel, Android, documentación y pruebas en su
[aporte al informe 2.6](../../../Evidencias%20Individuales/Informe_final_Panel_Android_Pruebas_Borquez_Juan.md).
