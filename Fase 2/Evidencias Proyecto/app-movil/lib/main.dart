// =============================================================================
// main.dart — Punto de entrada de la app móvil
// -----------------------------------------------------------------------------
// Es lo primero que se ejecuta al abrir la app. Crea la aplicación, le aplica
// el tema visual (colores amarillo/negro de la marca) y decide la primera
// pantalla: la agenda si hay una sesión guardada, o el login si no
// (ver services/session.dart).
//
// Mapa de carpetas de lib/:
//   screens/   las pantallas (login, agenda, historial, detalle, croquis)
//   services/  comunicación con el backend y guardado seguro de tokens
//   models/    clases que representan los datos (Visita, Croquis, ...)
//   theme/     colores y estilos de toda la app
//   widgets/   piezas visuales reutilizables (badge de estado, botón salir)
//   utils/     funciones de apoyo (formato de fechas)
//   config/    interruptores de configuración
//   db/        base de datos local para el modo offline (en preparación)
// =============================================================================

import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';

import 'screens/home_screen.dart';
import 'screens/login_screen.dart';
import 'services/api_client.dart';
import 'services/session.dart';
import 'services/pending_photo.dart';
import 'theme/app_theme.dart';
import 'widgets/company_brand.dart';

/// Permite navegar desde fuera de una pantalla: lo usa el aviso de "sesión
/// vencida" del ApiClient para volver al login desde donde esté el técnico.
final GlobalKey<NavigatorState> navigatorKey = GlobalKey<NavigatorState>();

/// Función que Flutter ejecuta al iniciar: dibuja el widget raíz de la app.
Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  if (!kIsWeb && defaultTargetPlatform == TargetPlatform.android) {
    try {
      await PendingPhotoStore.instance.recoverInterruptedCapture();
    } catch (_) {
      // Un plugin/captura fallido no debe impedir abrir la app ni iniciar sesión.
    }
  }
  // Si la sesión ya no se puede renovar, se vuelve al login borrando las
  // pantallas anteriores (con "atrás" no se puede volver a la agenda).
  ApiClient.onSesionVencida = () =>
      navigatorKey.currentState?.pushAndRemoveUntil(
        MaterialPageRoute(builder: (_) => const LoginScreen()),
        (route) => false,
      );
  runApp(const KillBichosApp());
}

/// Widget raíz. En Flutter todo lo que se ve en pantalla es un "widget";
/// este es el que contiene a todos los demás.
class KillBichosApp extends StatelessWidget {
  /// Decide si hay sesión al abrir. Se puede reemplazar en las pruebas.
  final Future<bool> Function() restaurarSesion;

  const KillBichosApp({
    super.key,
    this.restaurarSesion = SessionService.restaurar,
  });

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Kill Bichos IA',
      navigatorKey: navigatorKey,
      // Oculta la cinta roja "DEBUG" de la esquina superior derecha.
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light,
      // Navegación simple con Navigator estándar: el login abre la pantalla
      // principal (Hoy / Historial) con pushReplacement, y cerrar sesión
      // vuelve al login. No se usa go_router para mantener el ejemplo simple
      // de un proyecto de tesis con pocas pantallas.
      home: _InicioSesion(restaurarSesion: restaurarSesion),
    );
  }
}

/// Primera pantalla: mientras revisa la sesión guardada muestra el logo y
/// después abre la agenda o el login.
class _InicioSesion extends StatefulWidget {
  final Future<bool> Function() restaurarSesion;

  const _InicioSesion({required this.restaurarSesion});

  @override
  State<_InicioSesion> createState() => _InicioSesionState();
}

class _InicioSesionState extends State<_InicioSesion> {
  // Se guarda el Future para no repetir la revisión cada vez que se redibuja.
  late final Future<bool> _haySesion = widget.restaurarSesion().catchError(
    (_) => false,
  );

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<bool>(
      future: _haySesion,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return Scaffold(
            body: Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const CompanyLogo(size: 96),
                  const SizedBox(height: 24),
                  const CircularProgressIndicator(),
                ],
              ),
            ),
          );
        }
        return snapshot.data == true ? const HomeScreen() : const LoginScreen();
      },
    );
  }
}
