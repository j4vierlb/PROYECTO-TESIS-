# Regreso a la portada, sesión e inactividad — 3/11/2026

Trabajo exclusivamente en `juan`, sobre `95a2844`. Esta revisión sustituye la
decisión anterior de mostrar siempre la portada al abrir el sistema. Juan
solicitó preparar los commits, el push y la PR el 3/11/2026.

## Comportamiento vigente

- Al abrir o recargar con sesión guardada se entra directamente al panel.
  La API sigue comprobando autenticación y permisos; si rechaza una sesión
  vencida, se conserva el retorno al login con su aviso.
- Sin sesión se abre la portada. Ingresar abre el login. Si otra pestaña inició
  una sesión después de abrir esa portada, Ingresar la reconoce y abre el panel.
- El botón **Página principal** vuelve desde el panel a la portada sin borrar
  el token. Ingresar permite regresar al panel sin volver a identificar al usuario.
- El botón también está en el login para volver manualmente. En móvil, los
  botones de portada y salida son iconos con nombre accesible y título.
- El login regresa a la portada tras **5 minutos sin actividad** y sus campos
  se descartan al desmontarlo. La interacción por teclado, puntero, rueda,
  entrada y toque reinicia la espera. El tiempo fuera de la pestaña cuenta.
- Se comprueba el tiempo al volver a la ventana/pestaña para cubrir el retraso
  de temporizadores del navegador. La salida se pausa durante el ingreso.
- No es un cierre de sesiones del panel. Al salir del login se retiran sus
  listeners y su timer. No se interrumpe recuperación ni `#restablecer=...`.

## Verificación automatizada

**191/191 pruebas frontend aprobadas**, 13 archivos. El log actual es
[frontend.log](frontend.log). Los conteos anteriores son cortes distintos y no
se suman a este resultado.

Se agregan 17 casos de navegación/inactividad: regresar desde las cuatro vistas
del panel sin perder sesión, sesión creada en otra pestaña, umbral exacto de
cinco minutos con descarte del formulario, seis tipos de actividad, regreso a
ventana/pestaña tras un timer retrasado, retorno manual y reapertura del login,
recuperación fuera del temporizador e ingreso pendiente/sesión ya dentro del panel.
Se actualizan las expectativas anteriores de apertura y reapertura con sesión.

Los tiempos se verificaron con reloj simulado de Vitest: no se presentan como
una espera manual cronometrada de cinco minutos en el navegador. Se conserva
también el ajuste previo del test de respuesta atrasada para usar Día siguiente
en vez de una fecha fija coincidente con el día actual. No modifica el producto.

## Verificación manual y despliegue

Panel compilado y desplegado en `http://localhost:8080/`:

| Caso | Resultado observado |
|---|---|
| Abrir con sesión ya activa | Abre Agenda sin pasar por la portada ni pedir credenciales. |
| Página principal desde el panel | Muestra la portada. |
| Ingresar después de volver a la portada | Abre de nuevo el panel, conservando la sesión. |
| Recargar con sesión activa | Sigue abriendo directamente el panel. |
| Login sin sesión en origen local separado | Muestra Volver a la página principal y el aviso de cinco minutos. |
| Volver manualmente desde el login | Abre la portada. |
| Vista a 390 px | La casa de Página principal es visible y funciona en la cabecera móvil. |

Capturas: [botón en escritorio](panel_boton_inicio.png),
[cabecera móvil](panel_inicio_movil.png) y
[login con regreso y aviso de inactividad](login_regreso_inactividad.png).
La vista móvil corresponde a un viewport de escritorio de 390 × 844, no a una
prueba física en teléfono. Se restauró el tamaño original al terminar.

Para observar el login sin cerrar la sesión de localhost se utilizó
`127.0.0.1:8080`, un origen con almacenamiento independiente. No se intentó
autenticar desde ese origen ni se cambiaron las reglas CORS.

Se reconstruyó y recreó únicamente el servicio `web`, con `--no-deps` al iniciar.
La compilación de producción fue correcta; logs en [docker_build.log](docker_build.log)
y [docker_inicio.log](docker_inicio.log). El estado HTTP y las imágenes están en
[despliegue.json](despliegue.json).

No hay cambios de backend, base de datos, claves o `.env`. No se crearon ni
modificaron clientes, visitas o técnicos en esta verificación. La comprobación
manual usó la sesión de demostración existente; los tests simulan la API.

Las evidencias se recogieron en el despliegue local antes de publicar los cambios.
La PR se entrega para revisión; su publicación no implica fusionarla en `main`.
