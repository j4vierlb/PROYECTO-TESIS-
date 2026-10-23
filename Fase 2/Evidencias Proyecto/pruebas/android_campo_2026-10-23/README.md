# Android: flujos de terreno y recuperación — 23/10/2026

Responsable: Juan Bórquez. Trabajo local en `juan`, sobre `61cfa00`, con
`origin/main` integrado hasta `fa86264`. Código funcional en el commit
`2df57a5`. No se creó otra app ni se cambiaron backend o dependencias.

## Resultado

- **50/50 pruebas Flutter aprobadas**: 18 existentes y 32 nuevas
  (15 API, 8 ubicación y 9 recuperación de fotos). No son 50 pruebas de UI.
- `flutter analyze --no-pub`: sin observaciones.
- Compilación e instalación del APK debug: correctas.
- **16/16 comprobaciones HTTP** contra una API y base de datos desechables.
- Pruebas manuales en emulador: GPS simulado, mapa real, cámara emulada,
  galería, foto pendiente tras fallo de red y reinicio, reintento, fotos
  privadas, notas, confirmar/retirar/mover trampas y cierre de visita.

Los grupos anteriores se informan por separado; no se suman a suites históricas
como si fueran requisitos o pruebas diferentes. No se certifica precisión GPS
en terreno, cámara física ni equivalencia con el iPhone.

## Cambios implementados

1. Ubicación: comprueba servicio y permisos, informa denegación y ofrece Ajustes
   cuando corresponde. Espera máxima de 20 segundos y alternativa de marcar en
   el mapa. Android usa `LocationManager` nativo para no exigir activar Google
   Location Accuracy; iOS mantiene el proveedor habitual. En interiores o con
   mala señal puede tardar o fallar: no se inventa una ubicación.
2. Fotos: registra la visita/trampa antes de abrir cámara o galería; recupera
   archivos interrumpidos mediante `retrieveLostData`. Una subida fallida
   conserva el destino y la ruta del archivo en almacenamiento seguro, con
   reintento o descarte explícitos. No reasigna ni envía automáticamente fotos.
   Cerrar sesión elimina el envío pendiente, no la imagen original de galería.
3. Sesión y HTTP: límites de espera que incluyen la respuesta completa, una sola
   renovación ante 401 y cierre si vuelve a ser rechazado. La caída de red no
   elimina la sesión. No hay reintentos automáticos de escrituras por timeout.
4. Fotos privadas: token en `Authorization`, nunca en URL; renovación antes de
   abrir una foto con token vencido. Se rechazan rutas externas y se permite el
   parámetro de versión `v` del backend. Multipart distingue PNG de JPEG.
5. Errores de validación: mensajes legibles de FastAPI 422 y control de errores
   asíncronos al consultar permisos/autorización del croquis.

La captura, mapa y edición de trampas ya existían en la app compartida. Este
trabajo las robustece y verifica en Android; no atribuye su autoría original.

## Evidencia automatizada

| Registro | Resultado |
| --- | --- |
| [Flutter](logs/flutter_test.log) | 50 aprobadas |
| [Análisis](logs/flutter_analyze.log) | Sin observaciones |
| [Compilación](logs/flutter_build.log) | APK construido; advertencias de SDK/Kotlin conservadas |
| [HTTP](logs/field_api.json) | FIELD-API-01 a 16 aprobadas |
| [Estado final QA](logs/qa_final_state.json) | Dos visitas de prueba completadas; coordenadas, estados y existencia de fotos |
| [Controles de solo lectura](logs/readonly_ui.txt) | Sin acciones de escritura en la visita completada |
| [Inspección de secretos del APK](logs/apk_secret_check.json) | Sin valores locales de OpenAI, JWT, Maps web o Maps iOS; no había un token Twilio no vacío que comparar |
| [Firma](logs/apk_signature.txt) y [metadatos](logs/apk_metadata.json) | Certificado debug verificado, Maps Android presente, túnel habitual restaurado |
| [API QA](logs/qa_api.log) | Registro de solicitudes del entorno desechable, sin tokens |

El script [field_api.py](field_api.py) prueba login, inicio y notas, creación y
reutilización de croquis, alta, movimiento, confirmación, PNG y descarga privada,
401 anónimo, 403 de otra empresa, retiro, cierre y rechazo 409 de escritura en
visita cerrada. No invoca OpenAI ni Twilio. Las trampas sugeridas iniciales son
datos del seed, no una generación IA ejecutada en esta prueba.

## Comprobaciones desde la app

| Caso | Resultado observado y evidencia |
| --- | --- |
| FIELD-UI-01 Inicio y notas | Visita pasa a en curso, guarda notas y las conserva tras reiniciar; [detalle final](capturas/13_notas_persistidas_y_cierre.png) y JSON QA |
| FIELD-UI-02 Permiso GPS rechazado | Informa falta de permiso y no agrega una trampa. Denegación permanente y servicio apagado se cubren con mocks, no con UI |
| FIELD-UI-03 GPS autorizado | Coordenada simulada `-33.4869, -70.5989`, registrada como T-04; [confirmación](capturas/03_gps_trampa_agregada.png). Diferencia de latitud de aproximadamente 0,0000017 grados por emulación |
| FIELD-UI-04 Galería y fallo de conexión | Selecciona captura sintética del emulador para T-01; al retirar el túnel ADB informa fallo y conserva [foto pendiente](capturas/04_foto_pendiente_sin_conexion.png) |
| FIELD-UI-05 Reinicio y reintento | Cierre forzado y reapertura, conserva sesión y envío pendiente; al restaurar túnel y pulsar Reintentar desaparece el aviso, T-01 tiene foto en QA y se [abre privadamente](capturas/06_foto_privada_abierta.png) |
| FIELD-UI-06 Cámara | Captura [escena sintética](capturas/07_camara_emulada.png), confirma Done, sube para T-02 y [la abre](capturas/08_foto_camara_privada.png) |
| FIELD-UI-07 Confirmar y retirar | T-01 confirmada y después retirada con diálogo; ambos estados persistidos en JSON y [vista final](capturas/12_visita_completada_solo_lectura.png) |
| FIELD-UI-08 Alta desde mapa | [Modo de alta](capturas/09_mapa_modo_agregar.png), toque y tipo pegamento generan [T-05](capturas/10_mapa_trampa_manual.png) |
| FIELD-UI-09 Movimiento | Arrastre mantenido abre [confirmación](capturas/11_mover_confirmacion.png); Guardar cambia coordenadas de T-05 y las persiste en JSON |
| FIELD-UI-10 Cierre | Completa la visita con confirmación; croquis [solo lectura](capturas/12_visita_completada_solo_lectura.png), sin alta/confirmar/retirar/foto; API también rechaza cambios en visita cerrada |

Las capturas son originales, sin edición. Se eligieron después de inspección
visual; las tomas durante animación/carga no se usan como prueba de éxito.
La persistencia del envío tras reinicio se observó por su control Reintentar
y el posterior archivo subido; no se dispone de una captura nítida de ese
instante específico. Los nombres/contactos visibles proceden del seed demo.

## Entorno aislado y reproducción

Se levantaron `killbichos-android-field-db-86adb87f` y
`killbichos-android-field-api-86adb87f` sin credenciales del entorno habitual.
PostGIS 16, base `android_regression`, usuario `android_qa`; API únicamente en
`127.0.0.1:18787`, con fotos efímeras dentro de su contenedor. Se cargaron
`database/schema.sql`, `seed.sql`, `migracion_croquis_terreno.sql` y el
[fixture adicional](fixture.sql). Contraseñas y JWT de QA fueron aleatorios,
no se publican. No se modificaron clientes, visitas ni fotos de `killbichos`.

Para repetir: preparar contenedores nuevos con esos esquemas, nombre de base
y puerto; ejecutar el fixture solo en esa base (contiene una protección), y
`python field_api.py`. El script es destructivo sobre sus propios datos QA y
requiere un fixture fresco, no una visita ya completada. Nunca redirigirlo a la
API de trabajo. Para la UI, fijar la visita seed `7777...` al día de la prueba,
usar el operador público demo y conectar el APK por ADB al puerto QA.

Incidencias: al principio el script esperaba 200 para crear un croquis nuevo;
se corrigió a **201**, según el endpoint, y se repitió con fixture fresco.
La primera ruta GPS solicitó activar Google Location Accuracy; se rechazó esa
activación y se implementó/probó el proveedor nativo. El emulador arrancó lento
y hubo un intento de instalación antes de completar el arranque; se repitió
correctamente cuando Android estuvo listo. Su zona UTC inicial se corrigió a
`America/Santiago`; no fue una corrección de fechas del código.

## APK y ejecución local

Flutter 3.47.5 / Dart 3.13.4, Java 17; Android 16 API 36, AVD KillBichos_API36.
Paquete `com.killbichosia.app_movil`, debug `1.0.0+1`. Compilado con:

```powershell
flutter build apk --debug --no-pub --dart-define=API_BASE_URL=http://127.0.0.1:8000 --dart-define=MAPS_ENABLED=true
```

SHA-256:
`9b5e52529e9a990e06cd42c4f8f811e7bcf9ccb89d9b9baf44f9f2515ba73142`.
APK local en `app-movil/build/app/outputs/flutter-apk/app-debug.apk`, no en Git.
Misma firma debug y clave Maps privada que el corte anterior. La clave Android
debe estar en el APK para usar Maps; no es un secreto de servidor y requiere
restricciones por paquete/certificado/API. No se cambiaron los archivos privados.

El APK usa un túnel ADB: durante QA, `adb reverse tcp:8000 tcp:18787`; para
el backend habitual, **`adb reverse tcp:8000 tcp:8000`**. Repetirlo al reiniciar
el emulador o desconectar ADB. No sirve tal cual para un teléfono sin túnel:
hay que configurar una URL alcanzable al compilar y revisar HTTPS/release.

Al terminar se cerró sesión QA, se restauró el túnel al puerto 8000 habitual y
se inició sesión con el operador demo de la base de trabajo: agenda accesible,
sin nuevas visitas para hoy. Se eliminaron automáticamente al detenerlos solo
los dos contenedores QA y sus datos sintéticos efímeros. Sus resultados se
conservan arriba; los servicios y volúmenes habituales permanecen intactos.

## Límites pendientes

- Prueba en teléfono físico y precisión/cámara reales; comparación iPhone con
  commit y datos equivalentes. Juan confirmó continuar Android sin ese commit.
- Renovación de token cubierta con mocks y HTTP, no con token expirado en UI.
- Recuperación ante destrucción de actividad cubierta con mocks; en UI se
  verificó reinicio después del fallo de subida, no destrucción durante cámara.
- No existe sincronización offline completa: una foto pendiente no reemplaza
  agenda/croquis locales. El archivo está en caché del dispositivo y puede
  perderse si Android limpia esa caché; no es un respaldo permanente.
  Reintentar antes de completar la visita: una vez cerrada, el servidor ya no
  acepta subir fotos y la app solo permite descartar ese envío pendiente.
- Firma release, distribución, HTTPS y pruebas de producción fuera de alcance.
- Sin cambios en Word/backlog del equipo ni aceptación del cliente inventada.

Referencias del comportamiento de plugins: [image_picker](https://pub.dev/packages/image_picker)
y [geolocator](https://pub.dev/packages/geolocator). Las versiones del lockfile
se conservaron. Integridad de las evidencias en [SHA256SUMS.txt](SHA256SUMS.txt);
se preservan sus bytes originales con `.gitattributes`. El código se identifica
por el commit anterior: Git normaliza sus saltos de línea, por lo que no se
mezclan hashes de copias Windows con los de archivos originales de evidencia.
