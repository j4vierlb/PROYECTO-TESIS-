// =============================================================================
// utils/formato.dart — Formato de fechas para mostrar en pantalla
// =============================================================================

/// Formatos de fecha para mostrar al operador. El backend entrega las fechas
/// en UTC; aquí se convierten a la hora local del teléfono.
///
/// Rellena con cero a la izquierda: 5 -> "05".
String _dosDigitos(int valor) => valor.toString().padLeft(2, '0');

/// Hora local, ej: "07:00".
String formatHora(DateTime fechaHoraUtc) {
  // toLocal() pasa de UTC a la zona horaria del teléfono (Chile: UTC-3/-4).
  final local = fechaHoraUtc.toLocal();
  return '${_dosDigitos(local.hour)}:${_dosDigitos(local.minute)}';
}

/// Fecha local, ej: "24/09/2026".
String formatFecha(DateTime fechaHoraUtc) {
  final local = fechaHoraUtc.toLocal();
  return '${_dosDigitos(local.day)}/${_dosDigitos(local.month)}/${local.year}';
}

/// Fecha y hora juntas, ej: "24/09/2026 · 07:00".
String formatFechaHora(DateTime fechaHoraUtc) => '${formatFecha(fechaHoraUtc)} · ${formatHora(fechaHoraUtc)}';
