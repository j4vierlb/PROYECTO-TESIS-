# Actualización documental de Fase 2

Se actualizaron en la rama `juan` los 11 Word existentes, conservando su
estructura y formato base. Los originales anteriores a esta actualización
se respaldaron fuera del repositorio. No se hicieron cambios en el código
de la aplicación, el `.env`, staging, commits ni push durante esta tarea.

## Evidencias incorporadas

- E4: `Verificacion_PR14_2026-10-20.md` y sus JSON originales: **205 aprobadas**, 107 backend y 98 frontend; 0 fallas y 0 omisiones.
- Aislamiento incluido en E4: **30/30**; 12 accesos propios 200, 12 ajenos 403 y 6 sin token 401. Los 30 no se suman otra vez a 205.
- E5: `Croquis_maps_real_2026-10-20.md`; mapa satelital real, selección y foto privada verificados en localhost:5173. No se acredita esa misma comprobación en localhost:8080 ni en un despliegue remoto.
- Base 7f635f9 tras PR #14, más los cambios locales del panel en `juan`. No se afirma que estos cambios de Juan estén publicados en una PR.
- Historial conservado: ejecuciones de 32, 51 y 169; los ocho fallos de aislamiento antes de PR #14 y el rechazo de referente de Maps antes de corregirlo.

Las evidencias están en `Fase 2/Evidencias Proyecto/pruebas`. No se ejecutó
una prueba de carga nueva para esta edición: el rendimiento sigue sustentado
en la ejecución histórica del script, sin garantía de capacidad productiva.

## Cambios por documento

| Documento | Actualización |
| --- | --- |
| 01 Inicio | Estado técnico, alcance del panel/croquis, permisos y evidencia actual |
| 02 Backlog | Visor y aislamiento verificados; 205 pruebas; aceptación del cliente separada |
| 03 Definition of Done | Comprobación por empresa y referencias actuales; sin extender aprobación a IA/offline |
| 04 Fichas | Evidencias de agenda, edición, cancelación, visor y calidad; no se inventan reuniones de sprint |
| 05 Retrospectivas | Observaciones técnicas de correcciones y conservación de pruebas; no se presentan como acuerdos de reunión |
| 06 Diseño | Control de empresa del PR #14, consulta de solo lectura, Maps real y límites |
| 07 Pruebas | Matriz actualizada, E4/E5, detalle de 205 y 30 incluidos, reproducción y fallos históricos |
| 08 Manual | .env raíz para Vite/Docker, localhost y referentes Maps, migración, base antigua y suites aisladas |
| 09 Trazabilidad | CR-EXT-01/02 aprobados para el entorno probado y relación con componentes/evidencias |
| 10 Cierre | Resultado actual, VIS-002 resuelto y condiciones formales que siguen abiertas |
| 11 Acta | Antecedentes técnicos actualizados y consulta del croquis propuesta para la sesión; sin completar resultados, cargo, fecha ni firmas |

## Condiciones que permanecen abiertas

La aceptación de Rodrigo Quiroga y la demostración móvil con la empresa no se
dan por realizadas. Tampoco se acredita conversación real de WhatsApp,
generación IA de croquis, geocodificación ni sincronización offline por tener
pruebas del panel. La validación de tiempos de traslado con Routes API sigue
como propuesta, no como funcionalidad implementada.

## Verificación y límite de formato

Se contrastaron los totales con los JSON de ejecución y se comprobó la
integridad ZIP/OOXML, la apertura con python-docx, las fechas de actualización
y la ausencia de referencias obsoletas que dejaban Maps y PR #14 pendientes.
El acta conserva cinco escenarios como No evaluado por el cliente y los
campos de sesión, cargo y firmas sin rellenar.

Se intentó renderizar cada uno de los 11 Word con el renderizador empaquetado.
Todos quedaron bloqueados por el mismo error: LibreOffice soffice.exe no
está disponible. Por lo tanto, **el contenido está actualizado pero la
maquetación no está aprobada**. No se generaron PNG de páginas ni se afirma
haber comprobado cortes de tabla, solapamientos o paginación visualmente.
