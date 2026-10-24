# Fotos pendientes entre cuentas — segunda revisión de PR #21

Fecha: 24/10/2026. Rama: `juan`.

## Problema y solución

El almacenamiento conserva un único envío pendiente. Tras vencer la sesión del operador A, el operador B no veía ese envío por el aislamiento de cuentas, pero tampoco podía abrir cámara o galería: la comprobación global lo bloqueaba sin ofrecer una salida.

Se conserva ese aislamiento y el envío único; no se cambia el formato almacenado ni se reasigna la foto a otra cuenta. Al intentar capturar:

- Si el envío pertenece a la cuenta actual, sigue pidiendo reintentar o descartar desde su visita original.
- Si pertenece a otra cuenta, o es antiguo sin propietario conocido, se ofrece **Volver** o **Descartar y continuar**. El diálogo no muestra la foto, su ruta ni la identidad del propietario.
- Volver o cerrar el diálogo conserva el envío y no abre el selector.
- Confirmar elimina únicamente los metadatos del envío pendiente, no el archivo original. El aviso explica que la cuenta anterior ya no podrá reintentar ese envío desde la app.
- Después se permite abrir cámara o galería y se registra un destino nuevo asociado a la cuenta, visita y trampa actuales.
- Un `StateError` de conflicto de pendientes o de sesión informa su causa y deja de presentarse como un error de permisos de cámara.

El `photoStore` opcional de `CroquisScreen` permite probar el selector y el cambio de cuentas sin abrir una cámara real. En producción continúa usando `PendingPhotoStore.instance`.

## Pruebas y límites

**89/89 pruebas Flutter aprobadas**, antes y después del formato. El corte anterior tenía 82; estas siete regresiones nuevas no se suman otra vez al total:

| ID | Caso | Resultado |
| --- | --- | --- |
| FC-01 | Pendiente propia de otra visita | Se conserva y bloquea nueva captura, con mensaje de reintentar/descartar |
| FC-02 | Otra cuenta, elegir Volver | No abre cámara, no muestra datos ajenos y conserva el envío original |
| FC-03 | Descartar envío ajeno y abrir cámara | Registra cuenta/destino nuevos; cancelar el selector no restaura el envío descartado |
| FC-04 | Descartar envío ajeno y abrir galería | Mismo aislamiento y comportamiento que cámara |
| FC-05 | Envío antiguo sin dueño conocido | Ofrece confirmación; Volver lo conserva sin adjudicarlo a la cuenta nueva |
| FC-06 | Captura y subida tras descarte confirmado | Solo se envía la ruta nueva a la trampa actual; al terminar se limpia el nuevo pendiente |
| FC-07 | Aparece un pendiente mientras el selector está abierto | No lo sobreescribe y muestra conflicto de pendientes, no error de permisos |

Las pruebas son de widgets, almacenamiento y API simulados. FC-06 comprueba los argumentos de subida mediante un cliente de prueba; no representa una subida real al backend. No se repitió una ronda manual en emulador, teléfono físico, GPS, cámara real o iPhone para esta corrección. La compilación del APK se verifica por separado.

## Formato y evidencia

- Corrección funcional y siete pruebas: `b3a010f`.
- Formato de las pruebas separado: `8790970`; no se mezcla con el cambio funcional.
- `fotoUrlCompleta` ya estaba correctamente indentado en la versión actual, desde el commit de estilo `c4a56ff`. La comprobación de `dart format --output=none --set-exit-if-changed` de ese archivo, el croquis y las pruebas devuelve **0 cambios**. No se introduce un cambio artificial en la API.
- Análisis estático: sin incidencias.
- APK debug recompilado correctamente, con los avisos no bloqueantes existentes de Kotlin/`package_info_plus` y de XML del SDK conservados en el log.

Evidencias:

- [Suite antes del formato](logs/flutter_test_before_format.log).
- [Suite final](logs/flutter_test.log).
- [Análisis estático](logs/flutter_analyze.log).
- [Comprobación de formato](logs/dart_format.log).
- [Compilación APK debug](logs/flutter_build.log).

Reproducción desde `Fase 2/Evidencias Proyecto/app-movil`, con Flutter/Java/Android SDK configurados:

```powershell
flutter test --no-pub --reporter expanded
flutter analyze --no-pub
dart format --output=none --set-exit-if-changed lib/services/api_client.dart lib/screens/croquis_screen.dart test/field_review_widget_test.dart
flutter build apk --debug --no-pub --dart-define=API_BASE_URL=http://127.0.0.1:8000 --dart-define=MAPS_ENABLED=true
```

No se incluyen claves, archivos privados de configuración ni el APK.

## Separación visual pendiente

El usuario indicó expresamente conservar solo `juan` y dejar pendiente la separación en otra PR. Por eso no se crean ramas, no se revierten los tres commits visuales y no se reescribe ni fuerza el historial publicado. Esta actualización corrige el bloqueo entre cuentas; **no acredita que la PR #21 esté separada del trabajo visual ni resuelve posibles conflictos del panel con otra PR**.
