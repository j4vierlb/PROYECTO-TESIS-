# Panel: ubicación automática por dirección — 28/10/2026

Registro del corte implementado y probado localmente en `juan`, sobre `8689387`,
sin cambiar de rama ni crear ramas. Durante ese corte aún no se había hecho
commit, push ni modificado una PR; la publicación posterior se verifica aparte.
Los cambios Wi-Fi de Android que ya estaban pendientes se preservaron.

## Comportamiento

- El alta y edición solo piden nombre, teléfono y dirección. El navegador no
  recibe la clave del backend ni envía coordenadas antiguas al editar.
- El backend reutiliza `geocodificar` y almacena su punto en PostGIS. Conserva
  el alcance de Región Metropolitana y sus filtros de precisión/ambigüedad.
- Sin resultado confiable o ante un fallo de Google, el cliente se guarda con
  ubicación pendiente. El panel lo informa y permite corregir y reintentar.
- Cambiar o quitar la dirección invalida el punto anterior; la misma dirección
  ya ubicada no vuelve a consultar Google. Las ediciones del cliente se
  serializan para mantener coherencia entre dirección y punto.
- El contrato de coordenadas explícitas sigue disponible para integraciones
  previas. No se alteran el contrato móvil, trampas, fotos ni agendamiento.
- No se agregaron dependencias, Places Autocomplete ni una migración nueva.

## Pruebas automatizadas

| Ejecución | Resultado | Evidencia |
| --- | --- | --- |
| Backend, código local + PostgreSQL/PostGIS aislado | 220/220 | [backend.log](backend.log) |
| Backend, imagen nueva que se desplegó | 220/220 | [backend_imagen.log](backend_imagen.log) |
| Frontend Vitest | 125/125 | [frontend.log](frontend.log) |
| Compilación frontend | Correcta | [frontend_build.log](frontend_build.log) |

Son 220 pruebas de backend ejecutadas dos veces, no 440 pruebas distintas.
Los cortes anteriores 210/122 tampoco se suman a los nuevos totales. Se añadieron
10 casos de integración SQL y 3 de interfaz; también se adaptaron expectativas
anteriores al formulario que ya no envía latitud/longitud.

Los casos nuevos cubren alta con punto, alta sin resultado, coordenadas manuales
compatibles, cambio de dirección, descarte del punto antiguo, ahorro de consultas,
reintento de pendientes, borrado de dirección, edición de nombre sin mover el
punto y rechazo de clientes de otra empresa. La interfaz prueba que no se
reenvía la ubicación anterior, muestra el resultado del servidor y conserva la
dirección ante errores de guardado.

Entorno: contenedor dedicado `killbichos-geocoding-qa-20261028`, sin puertos
publicados ni red externa; bases `panel_regression` y `croquis_regression`.
Google, OpenAI, Twilio y SMTP no se contactan en la suite automatizada.
Las respuestas de geocodificación se simulan; autenticación, roles, SQL y
PostGIS de la integración son reales.

Se conserva [backend_imagen_ruta_inicial.log](backend_imagen_ruta_inicial.log):
la primera ejecución contra la imagen tuvo 19 errores del entorno porque los
tests se montaron en `/tests` y no podían resolver la utilidad frontend por
ruta relativa (`IndexError`). Se corrigieron solo los puntos de montaje, sin
cambiar lógica para ocultar errores; la ejecución completa posterior pasó.

## Prueba real en navegador y Google

Desde `http://localhost:8080/`, usando la cuenta administrativa de demostración:

1. Se abrió Nuevo cliente y se completaron solo los tres campos del formulario.
   [Formulario sin coordenadas](formulario_sin_coordenadas.png).
2. Se creó **QA Dirección automática 2026-10-28**, teléfono sintético
   `+00000000028`, con «Avenida Providencia 1208, Providencia, Santiago, Chile».
   El punto calculado fue `-33.4290994, -70.621161`, guardado en PostGIS y
   mostrado por el panel. [Cliente ubicado](cliente_geocodificado.png).
3. Se cambió a «Providencia, Región Metropolitana, Chile», sin calle/número:
   se descartó el resultado impreciso y el punto anterior. El panel informó
   ubicación pendiente. [Resultado pendiente](direccion_imprecisa_pendiente.png).
4. Se restauró la dirección completa y se recuperó automáticamente el punto.
   [Ubicación recuperada](ubicacion_recuperada.png).

Es una comprobación real de formulario, API, Google y persistencia, no una
captura del frontend con respuestas simuladas. Se hicieron tres búsquedas de
dirección desde este flujo. No se crearon visitas ni enviaron mensajes/correos.
El cliente QA queda en la base local para revisión; no es un cliente real y
su teléfono no debe utilizarse para comunicaciones. No se declara una nueva
prueba del APK ni del iPhone con este cambio.

## Despliegue y datos locales

Con autorización explícita de Juan, se aplicaron las migraciones pendientes
`migracion_whatsapp_saliente.sql` y `migracion_password_reset.sql` antes del
backend nuevo. Son dependencias de entregas anteriores, no de geocodificación.
[Registro de migraciones](migraciones_locales.log).

Se creó y comprobó un respaldo PostgreSQL en formato custom, guardado **fuera
del repositorio** en `tmp/geocoding_panel_2026-10-28/killbichos_before_geocoding.dump`
del espacio de trabajo. No se publican el respaldo, credenciales ni `.env`.

Antes y después de migrar: 2 clientes, 2 visitas, 2 usuarios, 1 operador y
10 trampas. Al finalizar: 3 clientes por el único registro QA nuevo; el resto
de los conteos no cambia. No se borraron filas ni volúmenes.

Se reconstruyeron y recrearon exclusivamente backend y web, usando `--no-deps`
para no iniciar una segunda base. Se conserva el volumen de fotos. La imagen
anterior sigue etiquetada localmente como `killbichos-backend:before-geocoding-20261028`.
La API y el panel responden HTTP 200; backend sin reinicios inesperados.

La clave del backend se toma del `.env` raíz y no del prefijo `VITE_`. SMTP y
Twilio continúan sin configuración operativa; probar esta mejora no habilita
el envío real de avisos ni recuperación por correo. La aprobación y despliegue
en otros computadores siguen pendientes de publicar e integrar los cambios.

## Preparación posterior para prueba manual en Android

A petición de Juan se agregó después de la prueba web una visita QA para el
mismo cliente: `4bd8f2c0-9c60-422a-8057-66a0020d2ae9`, el 28/10/2026 a las
17:00 de Chile, asignada a Juan Técnico (`tecnico1@killbichos.cl`). Se usó una
hora del día actual dentro del horario configurado porque la app solo muestra
la agenda de hoy y la preparación se realizó después de las 18:00. No es una
cita real; quedó identificada como prueba en sus notas.

Se comprobó mediante login de técnico y `GET /operadores/me/visitas-hoy` que la
visita aparece con la dirección completa y el punto `-33.4290994, -70.621161`.
No se crearon trampas ni croquis desde esta comprobación, ni se enviaron mensajes.
El total de visitas locales pasa de 2 a 3 por esta única visita QA adicional.

No se recompila el APK: el instalado ya recibe `cliente.lat/lng` y centra el
mapa en ese punto cuando el croquis no tiene trampas. Abrir el croquis desde
una visita abierta permite a la app crearlo si no existe. El APK de ese corte marca
trampas, no un pin con la dirección del cliente; el punto azul indica el GPS
del teléfono, no la ubicación del cliente. Confirmación visual en el Redmi
pendiente del usuario; no se presenta la respuesta de API como prueba física.

Posteriormente Juan confirmó que la geocodificación se veía correctamente en
su teléfono y solicitó un pin rojo explícito. Esa mejora se documenta aparte
en [Android: pin del cliente](../android_pin_cliente_2026-10-28/README.md); requiere
actualizar el APK y no se da por validada en el teléfono por aquella prueba anterior.
