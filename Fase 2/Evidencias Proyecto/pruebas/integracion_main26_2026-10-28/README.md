# Integración de main después de la PR #26 — 28/10/2026

Trabajo exclusivamente en `juan`. Se incorporó `origin/main` en `c4ce814`
(PR #26 de Javier), mediante el merge `707ecd5`, sin conflictos ni reescritura
de historial. La búsqueda de direcciones para todo Chile y la presentación
del agente son cambios de Javier integrados desde main.

La portada pública en preparación se guardó temporalmente con Git stash,
incluidos sus archivos nuevos. Se restaura localmente después de publicar
esta integración; no forma parte de la PR #25 ni de los contadores de este corte.

## Ajustes de compatibilidad

- El formulario de clientes pide calle, número y comuna o ciudad de Chile.
  Explica que la localidad encontrada debe coincidir con la dirección escrita.
- README de backend/frontend y diseño reflejan el alcance nacional, sin mantener
  el límite anterior a Región Metropolitana ni describir campos manuales que
  ya no aparecen en el formulario.
- Dos pruebas nuevas del panel crean clientes de Viña del Mar y Concepción,
  envían solo nombre, teléfono y dirección y muestran el punto devuelto por
  la API simulada. No son geocodificaciones reales de esas direcciones.
- Se conservan los filtros de precisión y país, los permisos por empresa,
  la ubicación pendiente, el pin rojo y la integración offline existente.

## Resultados del conjunto publicado

| Comprobación | Resultado | Registro |
|---|---|---|
| Backend completo, incluidos SQL/PostGIS y geocodificación nacional | **231/231, sin omisiones** | [backend.log](backend.log) |
| Panel React/Vitest | **132/132** | [frontend.log](frontend.log) |
| Compilación de producción frontend | Correcta | [frontend_build.log](frontend_build.log) |
| Flutter con Maps activo y configuración Wi-Fi | **164/164** | [flutter_test.log](flutter_test.log) |
| Flutter analyze | Sin incidencias | [flutter_analyze.log](flutter_analyze.log) |
| Instalación reproducible frontend | Correcta | [npm_ci.log](npm_ci.log) |

No se suman estos resultados a los contadores de cortes anteriores. Se conserva
el [intento inicial de npm ci](npm_ci_inicial_archivo_en_uso.log): Windows
tenía ocupado el módulo nativo de Rolldown por la vista previa local. Se detuvo
esa vista y `npm ci`, tests y compilación terminaron correctamente. npm informó
dos avisos de seguridad de dependencias ya presentes en el lock anterior;
esta integración no actualiza esas dependencias ni ejecuta `audit fix --force`.

## Aislamiento y límites

Las pruebas SQL utilizaron únicamente el contenedor temporal
`killbichos-main26-qa-20261028`, sin red externa ni puertos publicados, con las
bases sintéticas `panel_regression` y `croquis_regression`. El código local y
Node Linux se montaron en solo lectura. Se reutilizaron las dependencias de la
imagen backend anterior; el código ejecutado fue el de este merge, no el de
la imagen. El contenedor temporal se elimina al terminar.

Google, OpenAI, Twilio y SMTP se simulan/desactivan en la suite. Se comprobaron
direcciones chilenas fuera de Santiago, país extranjero, localidad ausente o
distinta, precisión, coincidencias parciales y errores del proveedor sin enviar
mensajes reales. No se realizaron consultas reales nuevas a Google.

No se modificaron la base de trabajo, sus volúmenes, archivos `.env` ni claves.
Esta sincronización de Git no reconstruye los contenedores de trabajo ni el APK.
El nuevo alcance se aplica en los entornos al desplegar el backend actualizado;
no requiere cambios en el contrato móvil ni una migración nueva. El APK ya
entregado conserva sus propias evidencias: no es una compilación de este merge.

Sigue pendiente registrar la prueba física del modo offline y de la pantalla
nueva sin ubicación en el Redmi. No se declara comparación comprobada con iPhone.
