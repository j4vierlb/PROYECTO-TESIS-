// =============================================================================
// config/app_config.dart — Interruptores de configuración
// -----------------------------------------------------------------------------
// Valores que se fijan al compilar la app con --dart-define=NOMBRE=valor,
// sin necesidad de cambiar el código.
// =============================================================================

/// Interruptores de configuración de la app.
class AppConfig {
  // Constructor privado: esta clase no se instancia, solo agrupa constantes.
  AppConfig._();

  /// El mapa de Google solo funciona con una API key válida; sin ella la app
  /// se cae al dibujarlo. Por eso viene apagado. Cuando ya exista la key
  /// (ver README), se compila con: --dart-define=MAPS_ENABLED=true
  static const bool mapsEnabled = bool.fromEnvironment('MAPS_ENABLED');
}
