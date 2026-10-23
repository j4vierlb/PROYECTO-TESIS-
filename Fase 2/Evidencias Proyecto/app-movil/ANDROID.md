# Android: misma aplicación Flutter que iOS

Android utiliza los mismos archivos `lib/`, recursos, `pubspec.yaml` y
`pubspec.lock` que iOS. No hay una segunda implementación de las pantallas.
La versión declarada es `1.0.0+1`. Para comparar con el iPhone de Javier,
registrar también el commit y los valores de `API_BASE_URL` y `MAPS_ENABLED`
utilizados en ambos dispositivos: el número de versión por sí solo no garantiza
que sean la misma compilación.

La base sincronizada para esta preparación incluye `origin/main` en
`76aae166f2b2a7ddad848dbfdd6513cb1abb7dff`, con croquis en terreno y sesión
persistente. No incluye cambios de IA de ramas aún no integradas.

## 1. Herramientas

- Flutter **3.47.5 / Dart 3.13.4**, correspondiente al hash de SDK registrado en
  `.metadata` (`6a19cca56475dbfba1478ee68d7bd0c2ef891da1`). El lockfile requiere
  Flutter >=3.47.0 y Dart >=3.13.4 <4.0.0. Confirmar además el SDK de la
  compilación instalada en el iPhone; no ejecutar
  `flutter pub upgrade` para preparar Android.
- JDK 17. El proyecto ya declara AGP 9.1.0 y Gradle 9.3.1.
- Android SDK, command-line tools y platform-tools. Instalar las plataformas,
  build-tools y NDK que solicite la compilación de este proyecto.
- Teléfono con depuración USB autorizada o emulador con Google Play Services
  para probar Google Maps.

Consultar la [instalación oficial de Flutter para Android](https://docs.flutter.dev/platform-integration/android/setup).
Revisar y aceptar personalmente las licencias del SDK cuando corresponda.

Desde esta carpeta:

```powershell
flutter --version
flutter doctor -v
flutter devices
flutter pub get --enforce-lockfile
flutter analyze
flutter test
```

Si la resolución con el lockfile falla, revisar primero el SDK instalado. No
bajar versiones ni regenerar plataformas para ocultar el error.

En este computador Windows, Flutter está en `C:\Users\user\develop\flutter`,
Java en `C:\Users\user\develop\java\jdk-17.0.20.1+1` y el SDK Android en
`C:\Users\user\AppData\Local\Android\Sdk`. Las rutas se agregaron al PATH del
usuario sin borrar las anteriores; abrir una terminal nueva o reiniciar VS Code
si todavía no reconoce los comandos.

La configuración local de Flutter desactiva los destinos Windows y Linux para
evitar generar enlaces de plugins de escritorio (que requieren permisos
adicionales en Windows). Esto no elimina carpetas ni cambia el proyecto iOS:

```powershell
flutter config --no-enable-windows-desktop --no-enable-linux-desktop
```

Si en el futuro se necesita compilar para escritorio, volver a habilitar su
destino y preparar los requisitos propios de esa plataforma.

## 2. Google Maps

Crear localmente `android/secrets.properties` a partir de
`android/secrets.example.properties` y completar `MAPS_API_KEY`. Está ignorado
por Git; no pegar la clave en Dart, documentos, capturas o commits.

En Google Cloud, habilitar **Maps SDK for Android** y restringir la clave a:

- Paquete: `com.killbichosia.app_movil`.
- SHA-1 del certificado con que se firma el APK instalado.

Obtener el SHA-1 después de configurar Flutter y Java:

```powershell
Push-Location android
try { .\gradlew.bat signingReport } finally { Pop-Location }
```

Enviar a Javier el paquete y el SHA-1, no el archivo de claves de firma. La
autorización del mapa de iPhone o de `localhost:5173` no sustituye esta
autorización. [Configuración oficial](https://developers.google.com/maps/flutter-package/config).

Para el **APK debug de este computador**, el certificado generado tiene SHA-1
`6F:DB:6F:0A:46:B7:49:35:D7:7A:68:62:1F:7A:D5:44:81:2A:50:25`.
No reutilizar este dato para una firma de release o el computador de otro
integrante: cada certificado puede tener una huella diferente.

## 3. Backend local y ejecución

No cambiar la IP por defecto del código compartido: pasar siempre
`API_BASE_URL` al compilar. El backend debe estar accesible en el computador
en el puerto 8000 y tener los cambios de sesión persistente y croquis.

### Teléfono por USB (opción recomendada para la primera prueba)

Autorizar la depuración en el teléfono. Si hay varios dispositivos, usar
`adb -s ID ...` y `flutter run -d ID ...`.

```powershell
adb devices
adb reverse tcp:8000 tcp:8000
flutter run --debug --dart-define=API_BASE_URL=http://127.0.0.1:8000 --dart-define=MAPS_ENABLED=true
```

El túnel se pierde al desconectar el dispositivo o reiniciar `adb`; volver a
ejecutar `adb reverse` cuando haga falta. No es una dirección de producción.

### Emulador

El dispositivo local `KillBichos_API36` utiliza Android 16 / API 36, imagen
Google APIs x86_64 y perfil Pixel 7. La comprobación `emulator -accel-check`
confirmó que WHPX está instalado y disponible. Se configuró la zona horaria del
emulador como `America/Santiago`. Para iniciarlo con recursos
acotados:

```powershell
emulator -avd KillBichos_API36 -memory 1536 -cores 2 -gpu auto -no-audio
```

En otra terminal, desde esta carpeta:

```powershell
flutter run -d emulator-5554 --debug --dart-define=API_BASE_URL=http://10.0.2.2:8000 --dart-define=MAPS_ENABLED=true
```

Mientras no exista una clave Android autorizada, usar `MAPS_ENABLED=false`.
Permite revisar los flujos y la lista de trampas, pero **no valida el mapa**.

Solo la variante **debug** incorpora una excepción HTTP para `localhost`,
`127.0.0.1` y `10.0.2.2`. No se permite HTTP general ni se agregan certificados
de confianza. Para conexión directa por WiFi o una distribución release,
utilizar un backend HTTPS válido; no copiar la excepción debug al manifiesto
principal. [Política de red Android](https://developer.android.com/privacy-and-security/security-config).

## 4. APK de prueba

```powershell
flutter build apk --debug --dart-define=API_BASE_URL=http://127.0.0.1:8000 --dart-define=MAPS_ENABLED=true
adb install -r build/app/outputs/flutter-apk/app-debug.apk
adb reverse tcp:8000 tcp:8000
```

Este APK es de desarrollo y requiere el túnel para el backend local. No sirve
como entrega de producción. La configuración release existente usa la firma
debug: antes de distribuir hay que definir y custodiar una firma de release,
autorizar su SHA-1 en Maps y usar backend HTTPS. No publicar el keystore en Git.

En este equipo de 16 GB, si hay poca RAM libre, cerrar el emulador antes de la
compilación y volver a iniciarlo después. Para limitar Gradle solo en la terminal
actual, sin modificar las propiedades versionadas del proyecto:

```powershell
$env:GRADLE_OPTS = '-Dorg.gradle.jvmargs="-Xmx2G -XX:MaxMetaspaceSize=1G -XX:ReservedCodeCacheSize=256m" -Dorg.gradle.workers.max=2 -Dorg.gradle.parallel=false'
```

## 5. Comprobación de equivalencia con iPhone

Registrar resultados reales, sin dar por aprobada una prueba porque el código
sea compartido. Usar cuentas y visitas de prueba; estos pasos modifican datos.

| ID | Verificación en ambos dispositivos | Resultado / evidencia |
|---|---|---|
| AND-01 | Login válido, inválido y cierre de sesión | Android 22/10: login válido y cierre aprobados; inválido verificado por HTTP, no desde la UI. Comparación iOS pendiente |
| AND-02 | Cerrar y abrir la app conserva la sesión; renovar token y cerrar sesión eliminan/actualizan los tokens correctamente | Android 22/10: conserva sesión vigente al relanzar; logout vuelve al login. Refresh HTTP aprobado; renovación automática de token vencido desde UI y comparación iOS pendientes |
| AND-03 | Agenda, detalle, notas e iniciar/completar una visita | Android: agenda vacía y detalle completado aprobados. Edición/cambios de estado y comparación iOS pendientes |
| AND-04 | Historial y visita completada en modo de solo consulta | Android aprobado con visita de prueba existente; comparación iOS pendiente |
| AND-05 | Abrir croquis existente y crear el de una visita sin croquis | Android: croquis existente de 3 trampas en consulta aprobado. Creación y comparación iOS pendientes |
| AND-06 | Mapa satelital, posición inicial y marcadores por estado | Android 22/10: mapa híbrido/satelital real, centrado en trampas, tres marcadores sin confirmar y selección T-01 aprobados. GPS, otros estados y comparación iOS pendientes |
| AND-07 | Agregar trampa por GPS; denegar ubicación y volver a intentar | Sin ejecutar |
| AND-08 | Agregar tocando el mapa, mover, confirmar y retirar | Sin ejecutar |
| AND-09 | Sacar foto, elegir de galería, cancelar y consultar la foto privada | Sin ejecutar |
| AND-10 | Backend sin conexión: error visible y recuperación sin perder sesión | Sin ejecutar |
| AND-11 | Reiniciar teléfono y comprobar sesión; cerrar sesión y volver a abrir | Sin ejecutar |
| AND-12 | Comparar pantallas y flujos con el mismo commit/datos del iPhone | Sin ejecutar |

Anotar fecha, commit, SDK, modelo/versión Android, versión iOS de referencia,
comando de compilación sin secretos, resultado de análisis/tests y capturas.
La cámara, GPS, Maps, almacenamiento seguro y permisos requieren pruebas en
dispositivo; los tests de Dart no reemplazan esa validación.

## Estado de esta preparación

Preparación verificada el **21 de octubre de 2026**, en la rama `juan`:

- Flutter 3.47.5 / Dart 3.13.4, Temurin JDK 17.0.20.1 y herramientas Android
  instalados desde sus fuentes oficiales; checksums de descargas verificados.
- SDK Platform 36, Build-Tools 36.0.0, Platform-Tools 37.0.1, NDK
  28.2.13676358, Emulator 37.2.12 e imagen Google APIs API 36 instalados.
  La compilación instaló además las plataformas 34 y 35 y CMake 3.22.1,
  requeridos por dependencias de la app.
- Emulador creado, arranque completo confirmado por `sys.boot_completed=1` y
  reconocido por `flutter devices` como Android 16 / API 36.
- `flutter pub get --enforce-lockfile`: correcto, sin actualizar el lockfile.
- `flutter analyze`: sin observaciones.
- `flutter test`: **16 pruebas aprobadas**. Son las pruebas existentes de
  modelos, sesión y widgets; no son 16 pruebas funcionales en Android.
- `flutter build apk --debug --no-pub
  --dart-define=API_BASE_URL=http://10.0.2.2:8000
  --dart-define=MAPS_ENABLED=false`: correcto. APK en
  `build/app/outputs/flutter-apk/app-debug.apk`, versión `1.0.0+1`, paquete
  `com.killbichosia.app_movil`, mínimo API 24 y destino API 36; incluye
  `arm64-v8a`, `armeabi-v7a` y `x86_64`.
- SHA-256 del APK de esta compilación:
  `1c3e0b860ae60bc59c5ab895bc447158b8f8a2a934d2f0efb876907c951db92c`.
- Firma del APK verificada con `apksigner`; coincide con el certificado debug
  indicado en la sección de Maps.
- APK instalado en el emulador: login correcto contra el backend local, agenda
  sin visitas para el día y consulta de historial, visita completada y croquis
  existente con 3 trampas. No se modificaron clientes, visitas ni trampas.
- Sesión persistente comprobada cerrando forzosamente la app y abriéndola de
  nuevo: entra a la agenda sin pedir credenciales. Después de cerrar sesión y
  repetir el proceso, vuelve al login. No se probó aún renovar un token vencido.
- Sin errores de Flutter o `AndroidRuntime` en los registros consultados durante
  esta comprobación. El primer arranque agotó la espera de `am start -W`, pero
  terminó mostrando el login; los siguientes arranques devolvieron `Status: ok`.
- El código `lib/`, iOS, recursos y dependencias se mantienen iguales a la base
  sincronizada de `main`.

Las siete capturas originales de esta ejecución se conservan en el
[registro de evidencias Android](../pruebas/android_2026-10-21/README.md),
con descripción del caso, sus límites y hashes SHA-256 para comprobar la
integridad de las imágenes. Corresponden a la ejecución del 21/10, no a una
nueva ejecución al publicar esta guía. El APK y las herramientas instaladas
no se incorporan al repositorio.

`flutter doctor` conserva un aviso de licencias adicionales no aceptadas. La
licencia utilizada por los paquetes instalados fue revisada y aceptada por el
usuario y la compilación terminó correctamente. No aceptar otras licencias
automáticamente para ocultar ese aviso.

La compilación también muestra advertencias de APIs obsoletas y de futura
compatibilidad de Kotlin en dependencias. No son fallas de esta compilación y no
se actualizaron paquetes para eliminarlas, para conservar el lockfile de iOS.

En el corte original del 21/10 seguían pendientes la clave Android de Maps,
GPS/cámara/fotos, escritura y comparación con el iPhone. La verificación
posterior siguiente resuelve solamente la configuración y consulta del mapa
Android y repite los controles indicados; no declara equivalencia completa ni
una entrega firmada para producción.

## Verificación posterior del 22/10/2026: Maps real

Se integró `origin/main` hasta `fa86264` en la rama `juan`, se respaldó la base,
se aplicó la migración de `message_sid` y se reconstruyó solo el backend,
conservando la base antigua y sus volúmenes. Sus 18 archivos Python coinciden
con el código local; health, refresh y la ruta de sugerencia están disponibles.

Las claves móviles están en los archivos privados indicados en esta guía,
no en el `.env` raíz. Se comprobó su formato sin imprimir los valores y se
compiló el APK con `MAPS_ENABLED=true` y backend `http://10.0.2.2:8000`.

- `flutter pub get --enforce-lockfile`: correcto, sin actualizar dependencias.
- `flutter analyze --no-pub`: sin observaciones.
- `flutter test --no-pub --reporter expanded`: **18 aprobadas**, con log.
- Comprobación HTTP separada: **12/12 aprobadas**, sin modificar clientes,
  visitas o trampas y sin invocar OpenAI ni Twilio.
- Mapa real aprobado en el emulador: imágenes satelitales, tres marcadores y
  ventana informativa de T-01, en una visita completada de demostración.
- Login, logout y sesión vigente al relanzar comprobados desde la app.

El APK sigue siendo debug `1.0.0+1`, firmado con el mismo certificado de la
preparación original. Su nuevo SHA-256 es
`718aee538d50f2ed36a60ce3d236d901e339eba79cd873d621bf744a4a18b26d`.
Los resultados, logs originales, capturas y las incidencias de arranque del
emulador se conservan en el
[registro del 22/10](../pruebas/android_2026-10-22/README.md).

No se aprobaron aún GPS, cámara/galería/fotos, escritura, funcionamiento sin
red, renovación automática de token vencido desde UI ni equivalencia con el
iPhone. El aviso inicial de System UI por recursos y el primer mapa gris
durante la carga se mantienen documentados; no se confunden con una prueba
exitosa. El emulador se dejó abierto en el mapa para la revisión local.

## Actualización del 23/10/2026: trabajo en terreno

El corte del 22/10 anterior es histórico. La nueva versión fortalece el código
Flutter compartido sin actualizar dependencias: permisos y espera GPS, proveedor
nativo Android, recuperación de fotos interrumpidas, envío pendiente con reintento
manual, renovación de sesión y validación de rutas de fotos privadas.

Se aprobaron **50 pruebas Flutter** (18 existentes y 32 nuevas), análisis sin
observaciones y **16 comprobaciones HTTP** en PostGIS aislado. Desde el emulador
se verificaron GPS simulado, alta en mapa, mover/confirmar/retirar, cámara emulada,
galería, foto pendiente tras caída de conexión y reinicio, reintento, fotos
privadas, notas y cierre con croquis de solo lectura. No se modificó la base
de trabajo. Detalles y límites en el
[registro de terreno del 23/10](../pruebas/android_campo_2026-10-23/README.md).

El APK debug actual reemplaza el archivo de compilación anterior y usa
`API_BASE_URL=http://127.0.0.1:8000`, con Maps activo. Para ejecutarlo en el
emulador contra el backend local es necesario, después de cada reinicio:

```powershell
adb -s emulator-5554 reverse tcp:8000 tcp:8000
```

SHA-256 actual:
`9b5e52529e9a990e06cd42c4f8f811e7bcf9ccb89d9b9baf44f9f2515ba73142`.
Las claves siguen en los archivos privados Android/iOS; no se incorporó `.env`
al APK. No es una versión release: siguen pendientes teléfono físico,
comparación exacta con iPhone y sincronización offline completa. Conservar
una foto en caché para reintentar no equivale a tener modo offline.
