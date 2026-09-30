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

El mapa de Google está **apagado** porque necesita una API key de Google Maps (de pago). Sin ella, el croquis se gestiona desde la lista de trampas. Con una key configurada (`ios/Flutter/Secrets.xcconfig` y `android/secrets.properties`, ver sus `.example`), se activa con `--dart-define=MAPS_ENABLED=true`.

## Pruebas

```bash
flutter analyze
flutter test
```
