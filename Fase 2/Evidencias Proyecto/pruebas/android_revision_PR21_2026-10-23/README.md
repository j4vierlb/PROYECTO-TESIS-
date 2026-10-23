# Correcciones de revisión de PR #21 — 23/10/2026

Rama: `juan`. Correcciones funcionales en `f55659a`; estilo/formato separado
en `c4a56ff`. Se conserva el historial publicado, sin rebase ni force push.
La PR sigue siendo [juan → main](https://github.com/j4vierlb/PROYECTO-TESIS-/pull/21).

## Resultado vigente

- **75/75 pruebas Flutter**, 25 más que las 50 del corte previo.
- Análisis estático sin observaciones.
- APK debug recompilado con Maps habilitado y firma debug verificada.
- Sin cambios de backend, dependencias, base de trabajo ni archivos privados.

Las pruebas nuevas usan almacenamiento, HTTP y servicios de ubicación simulados,
además de pruebas de widgets. No se ejecutó una nueva ronda en emulador o teléfono
físico. Las 16 comprobaciones HTTP y capturas del corte anterior siguen siendo
históricas; no se declaran repetidas ni se suman a estas 75.

## Respuesta a las observaciones

| Observación | Corrección y verificación |
| --- | --- |
| Al vencer la sesión se borraba la foto | `AuthStorage.clear()` invalida solo tokens y conserva el envío. Foto asociada al `sub` original, sin guardar el JWT en sus metadatos. Reingresar con la misma cuenta permite recuperarla; otra cuenta no puede verla/reasignarla |
| Logout manual | Solo `clear(manualLogout: true)` descarta el envío. El botón advierte si hay foto: Volver conserva tokens y foto; Salir y descartar elimina el envío, no la imagen original |
| URL inválida rompe el listado | `fotoUrlCompleta(String?)` devuelve null para URL nula, vacía, externa, malformada o fuera de la ruta autorizada. La tarjeta conserva la trampa y muestra Sacar foto, sin iniciar una descarga |
| Completar con foto pendiente | Antes del PATCH de cierre, vuelve a consultar el envío de esa cuenta/visita. Si existe lo bloquea y pide reintentar o descartar desde el croquis. Después de resolverlo sí permite completar |
| GPS y respaldo | Intento nativo de hasta 20 s. Si falla, ofrece acción **Por red**, no la ejecuta automáticamente. La alternativa usa el proveedor fusionado de Google, precisión media y hasta 10 s; si falla, propone mapa manual |
| Formato dificulta revisar | `f55659a` contiene cambios funcionales y pruebas, sin ejecutar dart format. `c4a56ff` contiene solo dart format y dos pares de llaves exigidos por el linter. Los 75 casos pasan antes y después |

La identidad del token se usa únicamente para separar trabajo local entre cuentas;
no sustituye la verificación de firma, permisos o empresa que realiza el backend.
Las fotos antiguas sin propietario se vinculan al token anterior disponible antes
de invalidarlo, al arrancar o antes de sustituir tokens. Si no queda identidad
anterior, no se adjudican a la cuenta nueva: se conservan sin ofrecer su reenvío.

## Por qué 20 s y forceLocationManager

En la prueba previa, el proveedor de Google solicitó activar Google Location
Accuracy. Se eligió el proveedor nativo de Android para no exigir esa activación.
Esto **no garantiza GPS satelital exclusivo**: la implementación local de
`geolocator_android 5.2.1` puede elegir el proveedor fusionado del sistema, GPS
o red según lo habilitado. Tampoco garantiza obtener señal dentro de un edificio.

Los 20 segundos son un límite de espera de la app para no dejar al técnico
esperando indefinidamente; no representan una precisión medida ni un valor
óptimo probado en terreno. Tras un fallo puede elegir Por red. Esa segunda
petición usa el proveedor fusionado de Google y puede mostrar su propio diálogo
de configuración; el usuario decide, la app no activa ajustes por su cuenta.

La petición alternativa tiene un límite de 10 segundos (no incluye el tiempo
que el usuario tarde en resolver diálogos del sistema). El resultado se presenta
como aproximado, con su precisión estimada, antes de elegir el tipo de trampa.
No es un posicionamiento interior ni un plano interior: se debe revisar/mover
el marcador o marcar la posición manualmente.

## Casos y evidencia

| Grupo | Nuevos | Evidencia |
| --- | --- | --- |
| HTTP y URLs | 8 | 401 al renovar conserva el archivo; siete rutas adicionales nulas/malformadas/fuera de contrato devuelven null |
| Fotos/sesión | 6 | Vencimiento, reingreso, otra cuenta, migración antigua, identidad desconocida, captura sin sesión y arranque con refresh vencido (el primer caso reúne vencimiento y reingreso) |
| Ubicación | 4 | Configuración 10 s, opt-in de respaldo, permisos antes de consultar y ausencia de bucle tras error |
| Widgets | 7 | Tres URLs inválidas sin caída; cierre bloqueado y permitido tras descarte; otra visita; aislamiento de cuentas; confirmación/cancelación del logout |

El total actual es 75: 50 anteriores y 25 añadidas. El caso existente de logout
también se ajustó al nuevo argumento explícito; no se cuenta como prueba nueva.

- [Suite completa](logs/flutter_test.log), ejecutada después del commit de estilo.
- [Suite antes del formato](logs/flutter_test_before_format.log), también 75.
- [Análisis estático](logs/flutter_analyze.log).
- [Compilación APK](logs/flutter_build.log), conservando avisos SDK/Kotlin.
- [Firma](logs/apk_signature.txt), [inspección de claves](logs/apk_secret_check.json)
  y [resumen de ejecución](logs/results.json), sin valores secretos.
- [Integridad de evidencias](SHA256SUMS.txt).

Reproducción desde `app-movil`:

```powershell
flutter analyze --no-pub
flutter test --no-pub --concurrency=1 --reporter expanded
flutter build apk --debug --no-pub --dart-define=API_BASE_URL=http://127.0.0.1:8000 --dart-define=MAPS_ENABLED=true
```

APK local `build/app/outputs/flutter-apk/app-debug.apk`, no incluido en Git.
SHA-256: `4615ae8a2c7750ef841153def9b2efe791460aba1b6e6d804b96cd2f0ed31823`.
No se instaló ni se probó esta nueva compilación en dispositivo durante esta
revisión. Para usar este APK contra el backend local desde un dispositivo ADB:
`adb reverse tcp:8000 tcp:8000`. En un teléfono sin ese túnel requiere otra URL.

## Límites

El bloqueo de cierre protege **esta app y su cola local**. El backend no conoce
una foto que aún no se subió, por lo que no impide que otra app/dispositivo
complete esa visita. El archivo pendiente está en caché y puede perderse si el
sistema limpia esa caché: no es almacenamiento offline completo ni respaldo.
Siguen pendientes teléfono físico, respaldo por red en terreno y comparación
con la versión instalada del iPhone; sin equivalencia certificada ni release.
Las evidencias originales del [corte previo](../android_campo_2026-10-23/README.md)
se conservan sin alterar sus resultados.
