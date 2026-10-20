# Prueba del croquis con Google Maps real

Fecha: 20 de octubre de 2026. Rama: `juan`. Prueba manual de navegador con
datos sintéticos, API QA y el SDK real de Google. No se modificó código,
credenciales ni configuración de Google Cloud durante esta repetición.

## Resultado

CR-EXT-01 aprobado desde `http://localhost:5173/` después del ajuste de
referentes informado por Javier. Se recargó la página para cargar nuevamente
el SDK. El error RefererNotAllowedMapError de la prueba anterior no reapareció.
No se verificó en esta repetición el croquis sobre localhost:8080.

| Comprobación | Resultado observado |
| --- | --- |
| Mapa real | Se mostraron imágenes satelitales y controles de Google Maps |
| Trampas | El mapa presentó controles para T-01 confirmada, T-02 sugerida por IA sin confirmar y T-03 retirada |
| Selección desde mapa | Seleccionar T-02 actualizó el detalle y la selección del listado |
| Selección desde listado | Seleccionar T-03 mostró su estado retirada y seleccionar T-01 recuperó su detalle y foto |
| Foto privada | La imagen sintética de T-01 cargó con ancho natural de 500 px |
| Consola | Sin mensajes de error o advertencia en la consulta realizada después de la recarga y selección |

La visita consultada es del 21/10/2026 en la base `panel_regression`, API en
`127.0.0.1:8787`. No se usaron datos de clientes reales ni se enviaron mensajes
de WhatsApp o solicitudes a OpenAI.

Captura: `capturas/panel_2026-10-19/11_maps_real_2026-10-20.png`. Se conserva
la captura 10 y el reporte del 19/10 como historial del rechazo anterior.

Esta comprobación manual no incrementa el total automatizado de 169 pruebas
registradas anteriormente. No demuestra el aislamiento de empresas del backend
ni sustituye CR-EXT-02, cuya verificación posterior se registra en el reporte
PR14. Los Word ya incorporan este resultado; su revisión visual sigue
pendiente. No se hizo staging, commit ni push.
