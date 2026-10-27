# Identidad visual del panel y Android — 26/10/2026

Entrega preparada en `juan`, posterior a la integración de la PR #21.
Esta actualización no modifica aquella PR ya integrada; necesita una nueva
revisión antes de incorporarla a `main`.
La recuperación de contraseña se mantiene como trabajo independiente con
sus propias pruebas y guía. No se sobrescribieron esos cambios.

## Cambios

- Mismo logo original en el panel y la app, sin redibujar ni alterar el archivo.
  SHA-256 de ambos PNG originales:
  `E0E17E36183805927166B652B1EF51564CD918250AAAC66475700580E450DB5A`.
- Paleta compartida con `app-movil/lib/theme/app_theme.dart`: amarillo
  `#F5C518`, negro `#1A1A1A`, fondo `#F7F7F4`, bordes `#E7E7E1` y texto
  secundario `#6B6B65`. Android ya usaba esta paleta; el panel dejó el verde.
- Panel: logo en login, navegación y ambos formularios de recuperación;
  favicon, foco visible, botones y selección con la misma identidad.
- Colores por estado de visita alineados al tema móvil. Las trampas conservan
  sus colores semánticos: confirmadas, sugeridas, por revisar y retiradas.
- Android: componente de marca accesible en arranque/login y cabeceras de
  agenda, historial, visita y croquis; etiqueta del launcher **Kill Bichos**.
  El ícono Android ya usaba el logo real y se conserva.
- Los cambios de cabecera están en Dart compartido. No se modifican archivos
  de configuración de iOS ni se compila/verifica la versión instalada de iPhone.

## Verificación

- **113/113 pruebas web**, incluidas recuperación y funcionamiento del panel:
  [frontend.log](frontend.log). Hay 6 nuevas/reincorporadas de marca sobre las
  107 del corte anterior; no se suman ambos totales.
- Compilación web correcta: [frontend_build.log](frontend_build.log).
- **102/102 pruebas Flutter**: [flutter_test.log](flutter_test.log). Incluye
  las 95 funcionales más 7 de marca, incluso cabecera estrecha con texto grande.
- Análisis Flutter sin problemas: [flutter_analyze.log](flutter_analyze.log).
- APK debug compilado: [flutter_build.log](flutter_build.log). Persisten los
  warnings conocidos de package_info_plus/KGP y SDK XML; no impiden compilar.
- Prueba de URL de foto inválida sigue comprobando ausencia de `NetworkImage`:
  ya no exige ausencia de todas las imágenes, porque la cabecera lleva un logo
  local `AssetImage`. No se elimina la prueba ni su comprobación funcional.

## Evidencia visual

Revisión real del panel en navegador integrado, en ventana estrecha:

- [Login](panel_login.png).
- [Recuperación](panel_recuperacion.png).

En esa ventana se requiere scroll vertical para ver el formulario completo;
el logo conserva sus proporciones y los campos siguen accesibles. No se
introdujeron credenciales ni se enviaron solicitudes de recuperación real.
La revisión autenticada de estados del panel se hizo con pruebas DOM y
respuestas sintéticas, no con nuevos datos en la base de trabajo.

Android: APK instalado con `adb install -r` (sin borrar datos), resultado
`Success`, y actividad iniciada en `KillBichos_API36`. Durante el arranque, la
interfaz del sistema Android mostró **System UI isn't responding**; el host
tenía aproximadamente 340 MB libres. Se detuvo el emulador y se recuperaron
unos 4 GB libres. No se guarda una captura de ese aviso como evidencia de
correcto funcionamiento de la app, ni se declara una validación manual visual
aprobada en este intento. La comprobación visual final de Android queda pendiente.

## APK de este corte

Ruta local ignorada por Git:
`app-movil/build/app/outputs/flutter-apk/app-debug.apk`.

- Versión: `1.0.0+1`, debug, paquete `com.killbichosia.app_movil`.
- Tamaño: **186236050 bytes**.
- SHA-256: `CBCEDD3D8EB1F5313FF137B8627B30DBCB1D2FB7AB4252C28BC5FD76A60C1CC4`.
- `API_BASE_URL=http://127.0.0.1:8000`, `MAPS_ENABLED=true`.
- Conserva la configuración anterior de acceso por ADB. No está configurado
  aún para llegar por Wi-Fi al backend desde un teléfono físico.

Ni el APK ni claves/.env se agregan a Git. No se cambiaron package ID,
restricciones de Google Maps, permisos de red o lógica del backend por el
trabajo visual. No hay validación en Redmi ni comparación con el iPhone instalado.
