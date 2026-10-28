# Verificación integrada antes de publicar — 28/10/2026

Rama de trabajo exclusiva: `juan`. Base remota incorporada: `origin/main`
en `d870ddf` (incluye las PR #23 y #24). Se conservaron geocodificación,
Wi-Fi debug y pin rojo; el merge `e1f619e` no tuvo conflictos. No se crean ramas,
no se reescribe historial y esta publicación no mezcla la PR en main.

## Alcance propio de la entrega

- Panel: alta/edición por dirección, coordenadas automáticas, estado pendiente,
  reintento y descarte del punto anterior al cambiar de dirección.
- Android: excepción HTTP debug solo para la IP Wi-Fi local explícita, más
  un pin rojo fijo con nombre/dirección del cliente, independiente de trampas.
- Pruebas y documentación de ambos flujos. Se adjuntan las capturas y logs
  anteriores como cortes históricos, sin sumar sus contadores al corte actual.
- Ajuste posterior de portabilidad de las pruebas SQLite: cerrar las conexiones
  antes de borrar sus directorios temporales en Windows y comprobar que la ruta
  de limpieza pertenece al directorio temporal de la prueba. La prueba de
  persistencia ahora cierra la conexión antes de abrir otra.

El modo offline y los IDs idempotentes de trampas ya pertenecen a main: no se
presentan como funcionalidad nueva propia. Sus archivos se conservan y la
corrección de Windows afecta solo el código de pruebas, no el flujo offline.

## Resultado del código combinado

| Comprobación | Resultado | Evidencia |
| --- | --- | --- |
| Backend, autenticación y PostgreSQL/PostGIS aislado | **222/222** | [backend.log](backend.log) |
| Panel React/Vitest | **125/125** | [frontend.log](frontend.log) |
| Compilación de producción del panel | Correcta | [frontend_build.log](frontend_build.log) |
| Flutter, incluidas las pruebas offline de main | **157/157** | [flutter_test.log](flutter_test.log) |
| Análisis Flutter | Sin incidencias | [flutter_analyze.log](flutter_analyze.log) |
| Resolución de dependencias según el lock de main | Correcta | [flutter_pub_get.log](flutter_pub_get.log) |

Los 220/125/113 de los cortes previos a la integración son históricos. El corte
actual incluye dos pruebas backend y las pruebas offline añadidas en main.
Se conserva [la primera ejecución Flutter](flutter_test_cierre_sqlite_inicial.log),
que tuvo cinco errores de limpieza por archivos SQLite abiertos en Windows;
después del cierre explícito, todas las pruebas pasan sin omitir esos casos.

Entorno SQL: contenedor dedicado `killbichos-publication-qa-20261028`, sin
puertos publicados ni red externa, con bases `panel_regression` y
`croquis_regression`. Se usa el código local en montaje de solo lectura y Node
Linux para las utilidades JS invocadas por tests backend. OpenAI, Maps, Twilio y
SMTP están desactivados/simulados en la suite; no se contactan clientes reales.
Al terminar se elimina únicamente el contenedor de QA y sus datos sintéticos.

## Despliegue, APK y límites

Esta tarea de publicación no modifica la base de trabajo, no despliega el
backend combinado ni reconstruye el APK después de incorporar el modo offline.
El APK con pin rojo entregado antes tiene su propio hash y pruebas en
[su registro](../android_pin_cliente_2026-10-28/README.md): no debe confundirse
con una compilación de esta integración posterior.

La geocodificación del panel ya tuvo una prueba real navegador/API/Google
documentada en [el registro del panel](../geocodificacion_panel_2026-10-28/README.md).
Juan confirmó el mapa centrado en su teléfono con la versión anterior; la nueva
marca roja todavía no tiene una confirmación visual registrada en el Redmi.
No se declara equivalencia física con iPhone ni una nueva prueba del mapa
nativo con el modo offline integrado.

No se incluyen `.env`, claves, APK/AAB, `android/build`, archivos de firma ni
respaldos de base de datos. Las credenciales permanecen locales. El servidor
requiere `GOOGLE_MAPS_API_KEY` autorizada para Geocoding API; no usar la clave
`VITE_` ni publicarla en el frontend. Las migraciones de entregas previas siguen
siendo necesarias en entornos que aún no las aplicaron; esta mejora no agrega
una migración nueva. La excepción HTTP Wi-Fi es solo debug, no producción.
