// =============================================================================
// models/croquis.dart — Modelos de Croquis y DispositivoTrampa
// -----------------------------------------------------------------------------
// Un croquis es el plano de una visita; dentro tiene la lista de trampas
// (cebaderos, trampas de pegamento, etc.) con su ubicación y estado.
// =============================================================================

/// Modelos que reflejan CroquisResponse/DeviceResponse del backend
/// (ver Fase 2/Evidencias Proyecto/backend/app/schemas.py).
class DispositivoTrampa {
  final String id;
  final String codigo; // etiqueta física, ej: "T-01"
  final String tipo; // cebadero, trampa_pegamento, trampa_luz u otro
  final double lat;
  final double lng;
  final bool sugeridoPorIa; // true si la ubicación la propuso la IA
  final bool confirmado; // true si el operador la validó en terreno
  final String estado; // activo, retirado o revisar

  DispositivoTrampa({
    required this.id,
    required this.codigo,
    required this.tipo,
    required this.lat,
    required this.lng,
    required this.sugeridoPorIa,
    required this.confirmado,
    required this.estado,
  });

  /// Crea una trampa a partir del JSON del backend.
  factory DispositivoTrampa.fromJson(Map<String, dynamic> json) => DispositivoTrampa(
        id: json['id'] as String,
        codigo: json['codigo'] as String,
        tipo: json['tipo'] as String,
        lat: (json['lat'] as num).toDouble(),
        lng: (json['lng'] as num).toDouble(),
        sugeridoPorIa: json['sugerido_por_ia'] as bool,
        confirmado: json['confirmado'] as bool,
        estado: json['estado'] as String,
      );
}

/// El croquis de una visita, con todas sus trampas.
class Croquis {
  final String id;
  final String visitaId;
  final String clienteId;
  final int version;
  final String? imagenSatelitalUrl;
  final bool sugeridoPorIa;
  final bool validadoPorOperador;
  final List<DispositivoTrampa> dispositivos;

  Croquis({
    required this.id,
    required this.visitaId,
    required this.clienteId,
    required this.version,
    this.imagenSatelitalUrl,
    required this.sugeridoPorIa,
    required this.validadoPorOperador,
    required this.dispositivos,
  });

  /// Devuelve una copia del croquis con otra lista de trampas. Los campos son
  /// `final` (no se pueden cambiar), así que para actualizar una trampa en
  /// pantalla se crea un croquis nuevo con la lista modificada.
  Croquis copyWithDispositivos(List<DispositivoTrampa> nuevosDispositivos) => Croquis(
        id: id,
        visitaId: visitaId,
        clienteId: clienteId,
        version: version,
        imagenSatelitalUrl: imagenSatelitalUrl,
        sugeridoPorIa: sugeridoPorIa,
        validadoPorOperador: validadoPorOperador,
        dispositivos: nuevosDispositivos,
      );

  /// Crea el croquis a partir del JSON del backend, convirtiendo también
  /// cada elemento de "dispositivos" en un DispositivoTrampa.
  factory Croquis.fromJson(Map<String, dynamic> json) => Croquis(
        id: json['id'] as String,
        visitaId: json['visita_id'] as String,
        clienteId: json['cliente_id'] as String,
        version: json['version'] as int,
        imagenSatelitalUrl: json['imagen_satelital_url'] as String?,
        sugeridoPorIa: json['sugerido_por_ia'] as bool,
        validadoPorOperador: json['validado_por_operador'] as bool,
        dispositivos: (json['dispositivos'] as List<dynamic>)
            .map((item) => DispositivoTrampa.fromJson(item as Map<String, dynamic>))
            .toList(),
      );
}
