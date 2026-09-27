// =============================================================================
// theme/app_theme.dart — Colores y estilos de toda la app
// -----------------------------------------------------------------------------
// Se define una sola vez aquí y Flutter lo aplica a todas las pantallas: así
// cada botón, tarjeta o campo de texto se ve igual sin repetir estilos.
// Los colores se escriben como 0xAARRGGBB (AA = opacidad, FF = opaco).
// =============================================================================

import 'package:flutter/material.dart';

/// Paleta de marca: amarillo como color de acento (botones, foco, destacados)
/// y negro para textos/appbar. El amarillo se usa en superficies chicas
/// (botones, badges, bordes) nunca como fondo grande, para que se vea
/// profesional y no como un cartel de advertencia.
class AppColors {
  AppColors._();

  static const Color yellow = Color(0xFFF5C518); // amarillo de la marca
  static const Color yellowDark = Color(0xFFC9A100); // borde de un campo enfocado
  static const Color black = Color(0xFF1A1A1A);
  static const Color background = Color(0xFFF7F7F4); // fondo gris muy claro
  static const Color surface = Colors.white; // tarjetas
  static const Color border = Color(0xFFE7E7E1);
  static const Color textPrimary = Color(0xFF1A1A1A);
  static const Color textSecondary = Color(0xFF6B6B65);
  static const Color error = Color(0xFFC62828);
}

/// Colores por estado de visita, para los badges en la agenda.
class EstadoColors {
  EstadoColors._();

  // `switch` con => devuelve un valor según el estado; `_` es "cualquier otro".

  /// Color de fondo del badge.
  static Color background(String estado) => switch (estado) {
        'en_curso' => AppColors.yellow,
        'completada' => const Color(0xFFDCEFDC),
        'cancelada' => const Color(0xFFF6D9D9),
        'reagendada' => const Color(0xFFE1E6F0),
        _ => const Color(0xFFECECE6), // agendada / default
      };

  /// Color del texto del badge.
  static Color foreground(String estado) => switch (estado) {
        'en_curso' => AppColors.black,
        'completada' => const Color(0xFF2E7D32),
        'cancelada' => AppColors.error,
        'reagendada' => const Color(0xFF33448E),
        _ => AppColors.textSecondary,
      };

  /// Texto legible para el operador ("en_curso" -> "En curso").
  static String label(String estado) => switch (estado) {
        'agendada' => 'Agendada',
        'en_curso' => 'En curso',
        'completada' => 'Completada',
        'cancelada' => 'Cancelada',
        'reagendada' => 'Reagendada',
        _ => estado,
      };
}

/// Tema de la app (se aplica en main.dart con `theme: AppTheme.light`).
class AppTheme {
  AppTheme._();

  static ThemeData get light {
    // Esquema de colores base de Material 3, partiendo del amarillo y luego
    // forzando los colores exactos de la marca.
    final colorScheme = ColorScheme.fromSeed(
      seedColor: AppColors.yellow,
      brightness: Brightness.light,
    ).copyWith(
      primary: AppColors.yellow,
      onPrimary: AppColors.black, // texto sobre amarillo = negro (buen contraste)
      secondary: AppColors.black,
      onSecondary: Colors.white,
      surface: AppColors.surface,
      onSurface: AppColors.textPrimary,
      error: AppColors.error,
    );

    return ThemeData(
      useMaterial3: true,
      colorScheme: colorScheme,
      scaffoldBackgroundColor: AppColors.background,
      // Barra superior: negra, con título blanco e íconos amarillos.
      appBarTheme: const AppBarTheme(
        backgroundColor: AppColors.black,
        foregroundColor: Colors.white,
        elevation: 0,
        centerTitle: false,
        titleTextStyle: TextStyle(
          color: Colors.white,
          fontSize: 19,
          fontWeight: FontWeight.w700,
          letterSpacing: 0.1,
        ),
        iconTheme: IconThemeData(color: AppColors.yellow),
      ),
      // Tipografía: tamaños y pesos para títulos y textos.
      textTheme: const TextTheme(
        headlineMedium: TextStyle(fontWeight: FontWeight.w800, color: AppColors.textPrimary),
        titleLarge: TextStyle(fontWeight: FontWeight.w700, color: AppColors.textPrimary),
        titleMedium: TextStyle(fontWeight: FontWeight.w600, color: AppColors.textPrimary),
        bodyLarge: TextStyle(color: AppColors.textPrimary),
        bodyMedium: TextStyle(color: AppColors.textSecondary, height: 1.4),
      ),
      // Campos de texto: fondo blanco, bordes redondeados, borde amarillo
      // oscuro cuando el campo está seleccionado.
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: Colors.white,
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: AppColors.border),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: AppColors.border),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: AppColors.yellowDark, width: 2),
        ),
        labelStyle: const TextStyle(color: AppColors.textSecondary),
      ),
      // Botón principal (FilledButton): amarillo con texto negro.
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: AppColors.yellow,
          foregroundColor: AppColors.black,
          // Deshabilitado (ej: mientras carga) se ve más transparente.
          disabledBackgroundColor: AppColors.yellow.withValues(alpha: 0.5),
          disabledForegroundColor: AppColors.black.withValues(alpha: 0.5),
          minimumSize: const Size.fromHeight(52), // alto cómodo para el dedo
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          textStyle: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16),
        ),
      ),
      // Barra inferior (Hoy / Historial): la pestaña activa lleva un fondo
      // amarillo y su ícono en negro.
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: Colors.white,
        indicatorColor: AppColors.yellow,
        labelTextStyle: const WidgetStatePropertyAll(
          TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppColors.textPrimary),
        ),
        iconTheme: WidgetStateProperty.resolveWith(
          (states) => IconThemeData(
            color: states.contains(WidgetState.selected) ? AppColors.black : AppColors.textSecondary,
          ),
        ),
      ),
      // Botón secundario (OutlinedButton): blanco con borde gris.
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: AppColors.black,
          minimumSize: const Size.fromHeight(52),
          side: const BorderSide(color: AppColors.border, width: 1.5),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          textStyle: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16),
        ),
      ),
      // Tarjetas: blancas, sin sombra, con borde fino y esquinas redondeadas.
      cardTheme: CardThemeData(
        color: Colors.white,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(14),
          side: const BorderSide(color: AppColors.border),
        ),
        margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      ),
      dividerTheme: const DividerThemeData(color: AppColors.border),
      // Mensajes emergentes abajo ("Visita iniciada", errores, etc.).
      snackBarTheme: const SnackBarThemeData(
        backgroundColor: AppColors.black,
        contentTextStyle: TextStyle(color: Colors.white),
        behavior: SnackBarBehavior.floating,
      ),
    );
  }
}
