# Identidad visual de Kill Bichos — 24/10/2026

## Alcance

Cambio exclusivamente visual para la app Flutter y el panel web. Se reutiliza el logo original de `app-movil/assets/images/logo.png` y la paleta de `app-movil/lib/theme/app_theme.dart`, compartida por Android e iOS: amarillo `#F5C518`, negro `#1A1A1A` y fondo `#F7F7F4`.

- App: componente accesible de marca, logo en Agenda, Historial, Detalle de visita y Croquis; reutilización del mismo componente en login y arranque. Nombre visible de Android: «Kill Bichos».
- Panel: logo en login, navegación y favicon; botones amarillos, navegación negra y colores de estado de visita alineados con el tema móvil.
- No se modifican endpoints, backend, permisos, agenda, recuperación de fotos, claves ni dependencias. Los colores semánticos de las trampas se conservan.
- No se aplicó un reformateo global. Los cambios de diseño están separados de las correcciones funcionales anteriores de la PR #21.

No se dispone del commit exacto instalado en el iPhone ni de una comparación visual en ese dispositivo. La referencia comprobada es el código y el recurso gráfico compartidos del repositorio; no se afirma equivalencia píxel a píxel con la app instalada.

## Resultados automatizados

| ID | Comprobación | Resultado | Evidencia |
| --- | --- | --- | --- |
| IV-01 | Análisis estático Flutter | Sin incidencias | [flutter_analyze.log](logs/flutter_analyze.log) |
| IV-02 | Suite completa Flutter | 82/82 aprobadas; incluye 7 nuevas de identidad visual | [flutter_test.log](logs/flutter_test.log) |
| IV-03 | Suite completa del panel | 107/107 aprobadas; incluye 9 nuevas de identidad visual | [web_test.log](logs/web_test.log) |
| IV-04 | Compilación web de producción | Correcta | [web_build.log](logs/web_build.log) |
| IV-05 | Compilación APK debug Android | Correcta | [flutter_build.log](logs/flutter_build.log) |

Los totales son cortes completos de cada suite, no pruebas adicionales a los totales anteriores. Las nuevas pruebas cubren logo accesible, conservación del título y las acciones, cabecera a 320 px con texto ampliado 1,8 veces, equivalencia binaria del logo entre web y móvil, colores compartidos y los cinco estados de visita. Se ajustó la regresión de URL de foto inválida para comprobar la ausencia de imágenes de red, permitiendo el nuevo logo local de la cabecera.

La compilación Android conserva advertencias no bloqueantes del plugin `package_info_plus`/Kotlin y de la versión de XML del SDK. No son fallas de compilación ni se modificó el entorno para ocultarlas.

## Verificación visual manual

| ID | Escenario | Resultado | Evidencia |
| --- | --- | --- | --- |
| IV-06 | Login del panel | Logo original cargado; formulario conservado | [Login](capturas/web_login.png) |
| IV-07 | Agenda web, 1440 × 1000 | Logo cargado, barra negra y botón amarillo; sin desbordamiento horizontal | [Escritorio](capturas/web_agenda_desktop.png) |
| IV-08 | Agenda web, 390 × 844 | Navegación adaptable y acciones visibles; sin desbordamiento horizontal | [Agenda móvil](capturas/web_agenda_mobile.png) |
| IV-09 | Clientes web, 390 × 844 | Listado adaptable sin desbordamiento horizontal; formulario abierto y cerrado sin guardar | [Clientes móvil](capturas/web_clientes_mobile.png) |
| IV-10 | APK instalado en emulador Android, API 36 | Agenda e Historial muestran logo y título; navegación funcional | [Agenda Android](capturas/android_agenda.png), [Historial Android](capturas/android_historial.png) |

Se utilizó el entorno local y los datos de demostración existentes. Estas comprobaciones visuales no crearon ni modificaron clientes, visitas o trampas. La agenda del día estaba vacía; el historial sí contenía una visita de demostración. No se repitieron pruebas de GPS, cámara o funcionamiento en iPhone dentro de este cambio de diseño.

## Reproducción

Desde `Fase 2/Evidencias Proyecto/frontend`:

```powershell
npm.cmd test
npm.cmd run build
```

Desde `Fase 2/Evidencias Proyecto/app-movil`, con Flutter, Java y Android SDK configurados:

```powershell
flutter analyze --no-pub
flutter test --no-pub --reporter expanded
flutter build apk --debug --no-pub --dart-define=API_BASE_URL=http://127.0.0.1:8000 --dart-define=MAPS_ENABLED=true
```

Para el emulador se utilizó `adb reverse tcp:8000 tcp:8000`. El APK, los archivos `.env` y los archivos privados de claves no se incluyen como evidencias ni se incorporan al repositorio.
