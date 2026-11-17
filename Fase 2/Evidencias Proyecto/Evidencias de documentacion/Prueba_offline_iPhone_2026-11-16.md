# Prueba del modo offline en iPhone contra el servidor (16 de noviembre de 2026)

## Objetivo

Comprobar que los cambios hechos por el técnico sin conexión se guardan en el teléfono y, al volver la señal, llegan al servidor una sola vez y en el orden en que se hicieron.

## Condiciones

- Dispositivo: iPhone 16 Pro, app de Flutter compilada en modo release.
- Servidor: Hetzner, `https://killbichos-api.duckdns.org` (HTTPS).
- Visita usada: una visita de prueba agendada para el 16/11 a las 11:00 UTC, con una clienta de prueba.
- Cómo se simuló la falta de señal: modo avión del iPhone, con WiFi y datos apagados.

## Procedimiento

1. Con señal: iniciar sesión, abrir la visita y el croquis, para que la app guarde todo en el teléfono.
2. Activar el modo avión.
3. Sin señal se hicieron 6 cambios: 2 trampas nuevas, 1 foto de una de ellas, notas en la visita y cambios de estado de la visita hasta dejarla completada.
4. La app mostró "6 cambios pendientes" y el botón "Enviar ahora".
5. Se apagó el modo avión y se pulsó "Enviar ahora".

## Resultado en el registro del backend

Hora en UTC, tomada del registro del contenedor del backend (`docker compose logs -t backend`):

| Hora | Petición | Respuesta |
|---|---|---|
| 03:35:45 | PATCH /visitas/{id} | 200 |
| 03:35:46 | POST /croquis/{id}/dispositivos (trampa T-01) | 201 |
| 03:35:48 | POST /dispositivos-trampa/{id}/foto | 200 |
| 03:35:50 | PATCH /visitas/{id} | 200 |
| 03:35:51 | POST /croquis/{id}/dispositivos (trampa T-02) | 201 |
| 03:35:52 | PATCH /visitas/{id} | 200 |

Seis peticiones en 7 segundos, una por cada cambio pendiente, en el mismo orden en que se hicieron. No hubo errores ni reintentos.

## Resultado en la base de datos

- La visita quedó en estado "completada", con la nota "Instalada 2 croquis".
- La trampa T-01 se creó una sola vez y tiene su foto guardada.
- La trampa T-02 se creó una sola vez, sin foto (así se hizo la prueba).
- No hay trampas duplicadas.
- Los códigos T-01 y T-02 los asignó el servidor al sincronizar. Mientras el teléfono estuvo sin señal, las trampas se veían como "Trampa nueva".

## Qué comprueba

Que la cola de cambios del teléfono envía cada cambio exactamente una vez y en orden, y que el servidor lo acepta. Esto cubre lo que no se pudo verificar en la prueba con el Redmi (13 y 14 de noviembre), cuyo registro del servidor se perdió al reiniciar el backend.

## Limitaciones

- Una sola prueba, en un iPhone. No reemplaza la prueba en Android, que sigue siendo la del Redmi.
- El registro no permite saber cuál de los 3 PATCH fue la nota y cuál el estado. El resultado final en la base es el esperado.
- No se probó la pérdida de señal a mitad de un envío, ni un conflicto (por ejemplo, una visita cerrada desde el panel mientras el técnico estaba sin señal).
- Al abrir datos sin señal, la app puede tardar hasta 15 segundos antes de mostrar la copia guardada. Es una lentitud conocida que no se corrigió.
- Las capturas del iPhone ("6 cambios pendientes" y el estado final) no están en el repositorio.
