// =============================================================================
// main.dart — Punto de entrada de la app móvil
// -----------------------------------------------------------------------------
// Es lo primero que se ejecuta al abrir la app. Crea la aplicación, le aplica
// el tema visual (colores amarillo/negro de la marca) y muestra el login.
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

import 'screens/login_screen.dart';
import 'theme/app_theme.dart';

/// Función que Flutter ejecuta al iniciar: dibuja el widget raíz de la app.
void main() {
  runApp(const KillBichosApp());
}

/// Widget raíz. En Flutter todo lo que se ve en pantalla es un "widget";
/// este es el que contiene a todos los demás.
class KillBichosApp extends StatelessWidget {
  const KillBichosApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Kill Bichos IA',
      // Oculta la cinta roja "DEBUG" de la esquina superior derecha.
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light,
      // Navegación simple con Navigator estándar: el login abre la pantalla
      // principal (Hoy / Historial) con pushReplacement, y cerrar sesión
      // vuelve al login. No se usa go_router para mantener el ejemplo simple
      // de un proyecto de tesis con pocas pantallas.
      home: const LoginScreen(),
    );
  }
}
