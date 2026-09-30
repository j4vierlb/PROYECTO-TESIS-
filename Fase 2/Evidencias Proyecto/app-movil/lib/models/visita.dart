// =============================================================================
// models/visita.dart — Modelos de Visita y Cliente
// -----------------------------------------------------------------------------
// El backend responde en JSON (texto). Estas clases convierten ese JSON en
// objetos de Dart con campos tipados, para que las pantallas escriban
// `visita.cliente.nombre` en vez de `json['cliente']['nombre']`.
// =============================================================================

/// Modelos que reflejan exactamente el JSON que entrega el backend
/// (ver Fase 2/Evidencias Proyecto/backend/app/schemas.py: ClientSummary y
/// VisitResponse) — mismos nombres de campo en snake_case en el JSON, pero
/// convertidos a camelCase del lado Dart por convención del lenguaje.
class Cliente {
  final String id;
  final String nombre;
  final String telefonoWhatsapp;
  // Pueden venir vacíos (null): un cliente que llegó por WhatsApp se registra
  // solo con su teléfono, antes de dar su dirección, y sin coordenadas.
  final String? direccion;
  final double? lat;
  final double? lng;

  Cliente({
    required this.id,
    required this.nombre,
    required this.telefonoWhatsapp,
    this.direccion,
    this.lat,
    this.lng,
  });

  /// Dirección para mostrar en pantalla, con un texto si todavía no existe.
  String get direccionTexto => (direccion == null || direccion!.trim().isEmpty) ? 'Sin dirección registrada' : direccion!;

  /// Crea un Cliente a partir del JSON del backend.
  factory Cliente.fromJson(Map<String, dynamic> json) => Cliente(
        id: json['id'] as String,
        nombre: json['nombre'] as String,
        telefonoWhatsapp: json['telefono_whatsapp'] as String,
        direccion: json['direccion'] as String?,
        // `num` acepta tanto 10 como 10.5; toDouble() lo deja siempre decimal.
        // El `?` deja el valor en null si el backend no mandó coordenadas.
        lat: (json['lat'] as num?)?.toDouble(),
        lng: (json['lng'] as num?)?.toDouble(),
      );
}

/// Una visita agendada al cliente.
class Visita {
  final String id;
  final Cliente cliente;
  final String operadorId;
  final DateTime fechaHora;
  final String estado; // agendada, en_curso, completada, cancelada, reagendada
  final String origenAgendamiento; // whatsapp_ia o manual
  // El `?` indica que el campo puede venir vacío (null).
  final String? notas;
  // Solo viene en el historial: trampas que quedaron instaladas.
  final int? dispositivosInstalados;

  Visita({
    required this.id,
    required this.cliente,
    required this.operadorId,
    required this.fechaHora,
    required this.estado,
    required this.origenAgendamiento,
    this.notas,
    this.dispositivosInstalados,
  });

  /// Crea una Visita a partir del JSON del backend (incluye al cliente).
  factory Visita.fromJson(Map<String, dynamic> json) => Visita(
        id: json['id'] as String,
        cliente: Cliente.fromJson(json['cliente'] as Map<String, dynamic>),
        operadorId: json['operador_id'] as String,
        // El backend entrega fecha_hora en ISO 8601 UTC (ej: "...Z");
        // DateTime.parse la reconoce como UTC automáticamente.
        fechaHora: DateTime.parse(json['fecha_hora'] as String),
        estado: json['estado'] as String,
        origenAgendamiento: json['origen_agendamiento'] as String,
        notas: json['notas'] as String?,
        dispositivosInstalados: json['dispositivos_instalados'] as int?,
      );
}
