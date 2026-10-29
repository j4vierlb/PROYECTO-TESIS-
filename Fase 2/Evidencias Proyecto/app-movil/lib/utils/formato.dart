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

const _dias = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo'];
const _meses = [
  'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
  'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre',
];

/// Día de una visita para agrupar la lista de próximas: "Mañana",
/// "Pasado mañana" o, más adelante, "Lunes 2 de noviembre". Compara el día
/// local de la visita con el de `hoy` (por defecto, ahora).
String etiquetaDia(DateTime fechaHoraUtc, {DateTime? hoy}) {
  final local = fechaHoraUtc.toLocal();
  final ahora = hoy ?? DateTime.now();
  // Se comparan días, no instantes: así la hora no cambia el resultado ni el
  // cambio de horario de verano. DateTime.utc evita los saltos de ese cambio.
  final dia = DateTime.utc(local.year, local.month, local.day);
  final base = DateTime.utc(ahora.year, ahora.month, ahora.day);
  final diferencia = dia.difference(base).inDays;
  if (diferencia == 0) return 'Hoy';
  if (diferencia == 1) return 'Mañana';
  if (diferencia == 2) return 'Pasado mañana';
  final nombre = _dias[local.weekday - 1];
  return '${nombre[0].toUpperCase()}${nombre.substring(1)} ${local.day} de ${_meses[local.month - 1]}';
}
