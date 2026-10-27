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
  // Dirección relativa de la foto de referencia en el backend
  // (ej: "/dispositivos-trampa/<id>/foto?v=..."), o null si no tiene.
  final String? fotoUrl;

  DispositivoTrampa({
    required this.id,
    required this.codigo,
    required this.tipo,
    required this.lat,
    required this.lng,
    required this.sugeridoPorIa,
    required this.confirmado,
    required this.estado,
    this.fotoUrl,
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
        fotoUrl: json['foto_url'] as String?,
      );

  /// Inverso de fromJson: el modo offline guarda el croquis en el teléfono
  /// con el mismo formato que entrega el backend.
  Map<String, dynamic> toJson() => {
        'id': id,
        'codigo': codigo,
        'tipo': tipo,
        'lat': lat,
        'lng': lng,
        'sugerido_por_ia': sugeridoPorIa,
        'confirmado': confirmado,
        'estado': estado,
        'foto_url': fotoUrl,
      };
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

  /// Inverso de fromJson (ver DispositivoTrampa.toJson).
  Map<String, dynamic> toJson() => {
        'id': id,
        'visita_id': visitaId,
        'cliente_id': clienteId,
        'version': version,
        'imagen_satelital_url': imagenSatelitalUrl,
        'sugerido_por_ia': sugeridoPorIa,
        'validado_por_operador': validadoPorOperador,
        'dispositivos': [for (final d in dispositivos) d.toJson()],
      };
}

/// Respuesta de POST /croquis/{visita_id}/sugerencia: el croquis con las
/// trampas nuevas que propuso la IA, más su explicación (no se guarda).
class SugerenciaCroquis {
  final Croquis croquis;
  final String origen; // "ia" o "reglas" (plan B si la IA no estaba disponible)
  final String? resumen;
  final List<String> advertencias;

  SugerenciaCroquis({
    required this.croquis,
    required this.origen,
    this.resumen,
    required this.advertencias,
  });

  factory SugerenciaCroquis.fromJson(Map<String, dynamic> json) => SugerenciaCroquis(
        croquis: Croquis.fromJson(json),
        origen: json['origen'] as String,
        resumen: json['resumen'] as String?,
        advertencias: (json['advertencias'] as List<dynamic>? ?? const []).cast<String>(),
      );
}
