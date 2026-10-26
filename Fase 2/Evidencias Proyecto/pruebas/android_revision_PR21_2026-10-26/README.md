# Revisión vigente de PR #21 — 26/10/2026

Rama única: `juan`. No se modifica backend, panel web, secretos ni historial publicado. El diseño visual sigue pospuesto.

## Respuesta a la revisión

| Punto | Estado |
| --- | --- |
| Cuenta bloqueada por foto ajena | Ya corregido en `b3a010f`: el croquis ofrece Volver o Descartar y continuar. Conserva la foto si se cancela; nunca muestra ni sube la foto de otra cuenta. Las siete regresiones siguen aprobadas |
| Captura en caché temporal | Corregido en `2287c12`: copia privada en `getApplicationDocumentsDirectory()/pending_field_photos`, también para lostData, migración y reintento |
| Descripción extensa | Sustituir por el estado vigente; las entregas y contadores anteriores quedan en sus documentos históricos, no mezclados en el resumen de la PR |
| Ruido de formato | `45d4010` restaura 29 miembros sin cambios lógicos al estilo de `main`, en cuatro archivos. Reduce 331 líneas del diff agregado de esos archivos frente a `2287c12` |
| Bloqueo global de cierre | Decisión de alcance pendiente. No se implementa ni declara validación global del backend |

## Comportamiento de las fotos

- La ruta que entrega `image_picker` se registra antes de copiar para poder informar un fallo de almacenamiento sin perder el destino original.
- Una captura o selección normal solo se considera lista tras guardar la copia privada persistente. No necesita permisos de almacenamiento público.
- La recuperación de Android copia el archivo antes de publicar la ruta recuperada; también migra un pendiente antiguo que todavía existe en caché. No sustituye una foto ya conocida por otro lostData.
- Antes de reintentar la subida se comprueba la cuenta actual y se prepara la copia persistente. Una cuenta distinta no puede preparar ni reasignar ese archivo.
- Al subir, descartar o confirmar el logout se eliminan los metadatos y se intenta limpiar únicamente la copia dentro de nuestro directorio privado. No se borra el archivo original de caché/galería ni una carpeta homónima externa. Un fallo de limpieza no bloquea el logout.
- Si falta espacio o falla la copia, se mantiene la ruta recuperable y se muestra un aviso de almacenamiento, no uno de permisos de cámara. El operador puede reintentar o descartar. Esa ruta de contingencia sigue siendo temporal hasta que la copia tenga éxito.
- Una captura antigua cuya caché ya fue eliminada no se puede reconstruir: se informa el fallo y se conserva la opción de descarte explícito. Desinstalar la app o borrar sus datos también elimina el almacenamiento privado; no es un respaldo externo.

`path_provider 2.1.6` pasa de dependencia transitiva a directa. Se resolvió con `flutter pub get --offline`; no se actualiza su versión ni la de otros paquetes.

Referencias oficiales: [caché de image_picker](https://pub.dev/packages/image_picker#permanently-storing-images-and-videos) y [directorio de documentos privado de la app](https://pub.dev/documentation/path_provider/latest/path_provider/getApplicationDocumentsDirectory.html).

## Verificación vigente

**95/95 pruebas Flutter**, antes y después de la limpieza: 82 anteriores y 13 nuevas. No se suman los contadores de ejecuciones históricas.

- 12 pruebas usan archivos reales de prueba: borrado de caché y reapertura; PNG de galería; ausencia de copias duplicadas; lostData; migración; no sustitución por lostData ajeno; limpieza de copia; conservación del original; protección de rutas externas; aislamiento entre cuentas; fallo de disco y reintento; caché ya desaparecida.
- Un nuevo test de widgets verifica que un fallo de disco deje el pendiente visible, sin subir y sin presentarlo como fallo de cámara.
- Las pruebas de flujo anteriores usan un almacenamiento de archivos simulado; no se presentan como pruebas de persistencia real.
- Análisis estático: sin incidencias. Las versiones originales de los bloques restaurados no se reformatean globalmente otra vez.
- Compilación APK debug correcta. Las advertencias conocidas de Kotlin/SDK se mantienen visibles en el log.

Evidencias:

- [Suite antes de limpiar formato](logs/flutter_test_before_cleanup.log).
- [Suite final](logs/flutter_test.log).
- [Análisis estático](logs/flutter_analyze.log).
- [Equivalencia de los cuatro archivos](logs/format_equivalence.json).
- [Compilación APK](logs/flutter_build.log).

No se ejecutó una nueva ronda en emulador, teléfono físico, cámara real o iPhone. No se acredita borrado de caché por Android real: las pruebas borran deliberadamente los archivos temporales del entorno de pruebas y comprueban que la copia persiste. No se publican APK, claves ni tokens.

## Revisión del diff

`2287c12` contiene persistencia y pruebas; `45d4010`, limpieza de formato y dos pares de llaves requeridos por el linter. No se hace rebase ni force push.

Se comparó la salida completa de `dart_style` antes y después de restaurar los miembros de `main.dart`, `croquis_screen.dart`, `visita_detalle_screen.dart` y `api_client.dart`: es idéntica, incluidos los comentarios. El log guarda el resultado por archivo. Las nuevas implementaciones y pruebas sí se formatean; las llaves del linter no alteran el comportamiento.

Quedan cambios de formato dentro de algunos métodos que también cambiaron de lógica; no se afirma haber eliminado todo el formato del historial. GitHub permite ocultar diferencias de espacios para facilitar la revisión restante.

## Límite del cierre de visitas — pendiente de decidir

La comprobación local bloquea el PATCH de cierre cuando la cuenta/visita tiene una foto pendiente en ese teléfono. Otro celular o el panel pueden cerrar esa visita porque el servidor no conoce archivos locales aún no sincronizados. La copia persistente no cambia esa limitación y una visita cerrada puede impedir la subida posterior según el contrato existente del backend.

Para un bloqueo global se necesita acordar con backend el registro y resolución de pendientes, su alcance entre cuentas/dispositivos, tiempos de expiración, concurrencia y comportamiento sin conexión. Validar solo el estado de la visita al subir no evita que otro dispositivo la cierre. No se introduce una falsa garantía global ni se modifica código de backend sin esa decisión.
