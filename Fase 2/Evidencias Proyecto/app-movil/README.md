# App móvil Kill Bichos IA (Flutter)

App para los técnicos en terreno: agenda del día, detalle de visita (iniciar, completar, notas), croquis con sus trampas (confirmar y retirar) e historial de visitas completadas.

## No va en Docker

La app se compila e instala en el teléfono o en un simulador. El backend sí corre en Docker (ver `README.md` de la raíz), y la app se conecta a él por la red.

## Apuntar la app al backend

La dirección del backend se pasa **al compilar** con `--dart-define=API_BASE_URL=...`:

| Dónde corre la app | `API_BASE_URL` |
|---|---|
| iPhone real (misma WiFi que el computador) | `http://IP-DEL-COMPUTADOR:8000` (en macOS: `ipconfig getifaddr en0`) |
| Simulador de iPhone | `http://127.0.0.1:8000` |
| Emulador de Android | `http://10.0.2.2:8000` |
| Android por USB con `adb reverse tcp:8000 tcp:8000` | `http://127.0.0.1:8000` |
| Chrome | `http://127.0.0.1:8000`, con `--web-port=5173` |

La IP del computador puede cambiar al cambiar de red: si la app dice "No se pudo conectar con el servidor", vuelve a compilar con la IP actual.

## Correr la app

```bash
cd "Fase 2/Evidencias Proyecto/app-movil"
flutter pub get

# iPhone real por cable: versión release (queda instalada y se abre sin cable)
flutter run --release --dart-define=API_BASE_URL=http://$(ipconfig getifaddr en0):8000

# Simulador o desarrollo con recarga en caliente (tecla r)
flutter run --dart-define=API_BASE_URL=http://127.0.0.1:8000
```

Usuario de prueba: `tecnico1@killbichos.cl` / `demo1234`.

## Mapa del croquis

El mapa de Google viene **apagado por defecto**. Sin una API key válida, el croquis se gestiona desde la lista de trampas. Con una key configurada (`ios/Flutter/Secrets.xcconfig` y `android/secrets.properties`, ver sus `.example`), se activa con `--dart-define=MAPS_ENABLED=true`. Cada plataforma necesita su autorización en Google Cloud; una clave restringida a iOS o al navegador no autoriza Android. Ver [preparación y pruebas de Android](ANDROID.md).

## Modo offline

El técnico puede trabajar sin señal. Con conexión, la app deja guardado en el teléfono lo del día (agenda, visitas y croquis); sin ella, sigue mostrando esa copia y los cambios quedan en una cola que se envía sola al volver la señal.

- **Se puede hacer sin señal:** iniciar y completar visitas, editar notas, confirmar, mover y retirar trampas, agregar trampas nuevas y sacar fotos.
- **Franja de estado:** arriba de cualquier pantalla aparece "Sin conexión" y cuántos cambios esperan enviarse. Se envían solos cada 20 segundos y al volver a la app, o con el botón "Enviar ahora".
- **Conflictos, el servidor gana:** si el panel cerró o canceló la visita mientras el técnico estaba sin señal, ese cambio se descarta y se le avisa en la franja.
- **Trampas nuevas:** quedan como "Trampa nueva" hasta sincronizar, y el servidor les asigna su código (T-05...). El teléfono genera el id de la trampa, así reintentar un envío cortado no la duplica.
- **Cuentas:** lo guardado se separa por técnico. Otro técnico en el mismo teléfono no ve ni envía los cambios del anterior. Al cerrar sesión con cambios sin enviar, la app avisa.
- **Para que funcione hay que haber abierto la agenda con señal** al menos una vez ese día. Sin copia guardada, una pantalla nueva necesita conexión.
- **Límites:** el historial guarda solo su primera página; la sugerencia con IA y subir el croquis por primera vez requieren conexión.

Código en `lib/offline/` (motor y cola) y `lib/db/` (SQLite).

## Pruebas

```bash
flutter analyze
flutter test
```
