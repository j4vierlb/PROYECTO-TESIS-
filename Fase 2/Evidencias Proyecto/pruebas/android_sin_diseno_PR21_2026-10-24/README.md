# PR #21: Android sin cambios de identidad visual

Fecha: 24/10/2026. Rama única de trabajo: `juan`.

## Separación realizada

Se retiran temporalmente los tres commits visuales mediante reversiones normales, sin rebase, force push, ramas nuevas ni modificaciones a `pedro` o `main`:

| Trabajo pospuesto | Commit original | Reversión |
| --- | --- | --- |
| Logo y cabeceras de la app | `6b65239` | `5d7ddbf` |
| Logo, paleta y pruebas visuales del panel | `a2a365a` | `60c4308` |
| Capturas y documentación del diseño | `ea7b25e` | `b230beb` |

Los archivos visuales añadidos y sus evidencias se retiran del árbol actual, pero siguen recuperables en esos commits. No se borra el logo original de la app ni se modifica la configuración privada.

La reversión del logo de la app tuvo un único conflicto en una aserción de prueba. Se restauró la comprobación original de ausencia de imágenes cuando una URL de foto es inválida, conservando los siete casos nuevos de fotos entre cuentas. Las correcciones funcionales de sesión, GPS, captura, subida, URL de foto y cierre de visitas permanecen.

El contenido completo de `Fase 2/Evidencias Proyecto/frontend` coincide con `origin/main` en `fa86264fd808f82424ea8e4612471ad56bbd3c1c`. Por tanto, la PR #21 no propone diferencias de contenido en el panel, incluidos `main.jsx`, `panel-utils.js` y `styles.css`. Esto retira el solapamiento del panel con la PR #22; no integra ni modifica esa PR.

Los commits visuales originales y las reversiones siguen visibles en el historial. Se separó el **contenido final del diff**, no se reescribió la lista de commits publicada.

## Resultado vigente

- **82/82 pruebas Flutter aprobadas**: 75 funcionales previas y las siete regresiones de fotos entre cuentas.
- **98/98 pruebas del panel aprobadas** como verificación de regresión de su contenido original; no son nuevas funcionalidades de esta PR.
- Build web de producción correcto.
- Análisis estático sin incidencias y formato de los archivos revisados sin cambios pendientes.
- Compilación del APK debug correcta, con las advertencias no bloqueantes existentes de Kotlin/`package_info_plus` y XML del SDK conservadas en el log.

Los cortes anteriores de 89 Flutter y 107 web incluían siete y nueve pruebas de identidad visual, respectivamente. Esas pruebas se posponen junto con el diseño; no se eliminaron pruebas funcionales para obtener estos resultados. Los logs de 89 se conservan como evidencia histórica, no como resultado de este estado sin diseño.

Evidencias de esta ejecución:

- [Pruebas Flutter](logs/flutter_test.log).
- [Análisis Flutter](logs/flutter_analyze.log).
- [Formato](logs/dart_format.log).
- [Compilación APK](logs/flutter_build.log).
- [Pruebas del panel](logs/web_test.log).
- [Build web](logs/web_build.log).

No se repitieron pruebas manuales en emulador, cámara real, GPS, teléfono físico o iPhone para esta separación. Las regresiones automatizadas utilizan servicios simulados. No se incluyen APK, tokens ni claves.

## Trabajo visual recuperable: siguiente paso

No se abre otra PR mientras #21 siga abierta y se mantenga la condición de usar solo `juan`. Cuando Javier integre Android (#21) y WhatsApp (#22) en `main`:

1. Verificar que `juan` esté limpia y actualizar sus referencias de `origin`.
2. Integrar el `main` actualizado en `juan`, sin cambiar de rama ni sobrescribir trabajo.
3. Recuperar y adaptar el diseño de los commits originales, preservando la nueva bandeja de WhatsApp, el helper de fecha de Pedro y sus estilos/pruebas. No reemplazar archivos completos por sus versiones antiguas.
4. Repetir las pruebas y generar evidencias nuevas. Las capturas anteriores no acreditan el diseño integrado con WhatsApp.
5. Abrir una nueva PR visual desde la misma `juan` una vez cerrada la #21.

No debe ejecutarse una reaplicación ciega de los tres commits originales: pueden necesitar resolución de conflictos y actualización de pruebas sobre el panel integrado. Su recuperación no requiere crear otra rama.
