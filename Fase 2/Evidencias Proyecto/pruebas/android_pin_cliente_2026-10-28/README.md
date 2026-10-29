# Android: pin rojo del cliente — 28/10/2026

Registro del corte local previo a la publicación, desarrollado en `juan` sin
crear ramas. Al ejecutar estas pruebas aún no se había hecho commit ni push. Se conservan los
cambios pendientes de Wi-Fi y geocodificación del panel. No se modifican el
backend, la base, la clave de Maps ni la política de red para esta mejora.

## Funcionalidad

- Un marcador rojo fijo representa el punto del cliente que ya entrega la API.
  No utiliza el GPS del teléfono ni el centro de respaldo como ubicación real.
- Al tocarlo, la ventana de Google Maps muestra nombre y dirección disponibles.
  Si no se proporcionan, no inventa una dirección; usa «Ubicación del cliente».
- Se agrega al conjunto de marcadores sin crear una trampa. No se arrastra,
  confirma, retira ni guarda nada por tocarlo; mantiene identidad independiente
  (`client-location`) y prioridad visual sobre los marcadores de trampas.
- Conserva colores y operaciones de las trampas y el centrado previo: promedio
  de las trampas si existen, ubicación del cliente si no, respaldo si falta todo.
- No agrega marcador si falta una coordenada, no es finita o está fuera del
  rango geográfico. El valor cero sí se acepta como coordenada real.
- Nombre/dirección se pasan del detalle al croquis también en visitas completadas.
  El código Dart es compartido con iOS, pero aquí solo se compila Android.

## Verificación

- **113/113 pruebas Flutter**: [flutter_test.log](flutter_test.log). Son las
  105 anteriores más 6 del marcador y 2 de navegación detalle/croquis, no 218.
- **Análisis sin incidencias**: [flutter_analyze.log](flutter_analyze.log).
- **APK debug compilado**: [flutter_build.log](flutter_build.log). Continúan
  las advertencias previas sobre Kotlin de `package_info_plus` y XML del SDK;
  no impiden la compilación. No se actualizan dependencias en esta tarea.
- **Firma y contenido del APK**: [verificacion_apk.log](verificacion_apk.log).
  La firma coincide con la compilación Wi-Fi anterior; el paquete conserva
  `com.killbichosia.app_movil`, versión `1.0.0+1`.
- Se inspeccionó el recurso de red compilado (HTTP solo a destinos debug
  explícitos, incluida `192.168.1.12`). También se comprobó que el código dentro
  del APK contiene el marcador y la URL Wi-Fi esperados, sin volcar el binario.
- Solo se formatearon los dos archivos nuevos; no se reformateó globalmente Dart.

Los tests verifican coordenadas, color, etiqueta, marcador no arrastrable,
ausencia de pin ficticio y datos enviados del detalle al croquis. No sustituyen
una captura del mapa nativo de Google en un teléfono. Juan confirmó la ubicación
con el APK anterior; **el pin nuevo está pendiente de comprobar en su Redmi**.
No se declara validación en iPhone ni se envían direcciones reales adicionales
a Google para estas pruebas automatizadas.

## APK entregable local

Archivo ignorado por Git:
`app-movil/build/app/outputs/flutter-apk/kill-bichos-wifi-pin-rojo-debug.apk`.

- Tamaño: **186.238.055 bytes**.
- SHA-256: `4BC71FDB06963B27572A2EA0E09B4F83A24B4BB46210C56E63A5AAD55E5D2AA4`.
- Backend compilado: `http://192.168.1.12:8000`; `MAPS_ENABLED=true`.
- Misma firma debug, SHA-1:
  `6F:DB:6F:0A:46:B7:49:35:D7:7A:68:62:1F:7A:D5:44:81:2A:50:25`.
- El APK Wi-Fi anterior con otro nombre se conserva para referencia.

Instalar como **actualización**, sin desinstalar ni borrar datos, para conservar
sesión y posibles fotos pendientes. Mantener PC/backend encendidos y teléfono
en la misma Wi-Fi de confianza; este APK debug usa HTTP local, no es una entrega
de producción. No subir APK, `.env`, claves o archivos de firma al repositorio.

Prueba manual pendiente: actualizar el APK, abrir una visita cuyo cliente tenga
ubicación, entrar a **Ver croquis → Mapa**, localizar el pin rojo, tocarlo y
comprobar nombre/dirección. Revisar que sigan funcionando los pines de trampas.
