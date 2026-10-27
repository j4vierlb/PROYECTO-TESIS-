// =============================================================================
// offline/local_store.dart — Almacenamiento local del modo offline
// -----------------------------------------------------------------------------
// Dos cosas viven en el teléfono, separadas por cuenta (`owner`):
//   - cache:  la última copia de lo que el backend entregó (agenda, visitas,
//             croquis), para poder verlo sin señal.
//   - outbox: los cambios que el técnico hizo sin señal y todavía no se
//             enviaron, en el orden en que los hizo.
// LocalStore es la interfaz; SqliteLocalStore es la real y MemoryLocalStore se
// usa en las pruebas.
// =============================================================================

import 'dart:convert';

/// Tipos de cambio que se pueden dejar en cola.
class OpKind {
  OpKind._();
  static const visitaUpdate = 'visita_update';
  static const dispositivoUpdate = 'dispositivo_update';
  static const dispositivoAdd = 'dispositivo_add';
  static const foto = 'foto';
}

/// Un cambio hecho sin señal, pendiente de enviarse al backend.
class PendingOp {
  final int? id; // lo asigna el almacén al guardarlo
  final String owner;
  final String kind; // ver OpKind
  final String visitId;
  final Map<String, dynamic> payload;
  final DateTime createdAt;
  final int attempts;
  final String? lastError;

  const PendingOp({
    this.id,
    required this.owner,
    required this.kind,
    required this.visitId,
    required this.payload,
    required this.createdAt,
    this.attempts = 0,
    this.lastError,
  });

  PendingOp copyWith({int? id, int? attempts, String? lastError}) => PendingOp(
        id: id ?? this.id,
        owner: owner,
        kind: kind,
        visitId: visitId,
        payload: payload,
        createdAt: createdAt,
        attempts: attempts ?? this.attempts,
        lastError: lastError ?? this.lastError,
      );

  /// Texto corto para avisarle al técnico qué cambio se descartó.
  String get descripcion {
    switch (kind) {
      case OpKind.visitaUpdate:
        final estado = payload['estado'] as String?;
        if (estado == 'en_curso') return 'iniciar la visita';
        if (estado == 'completada') return 'completar la visita';
        return 'editar la visita';
      case OpKind.dispositivoUpdate:
        switch (payload['accion']) {
          case 'confirmar':
            return 'confirmar una trampa';
          case 'mover':
            return 'mover una trampa';
          case 'eliminar':
            return 'retirar una trampa';
        }
        return 'cambiar una trampa';
      case OpKind.dispositivoAdd:
        return 'agregar una trampa';
      case OpKind.foto:
        return 'subir una foto';
    }
    return 'un cambio';
  }
}

abstract class LocalStore {
  // --- Cache (última copia del backend) -------------------------------------
  Future<void> putCache(String owner, String key, String json);
  Future<String?> getCache(String owner, String key);
  Future<void> deleteCache(String owner, String key);

  // --- Outbox (cambios pendientes) ------------------------------------------
  /// Guarda el cambio al final de la cola y devuelve su id.
  Future<int> enqueue(PendingOp op);

  /// Cambios pendientes de la cuenta, del más antiguo al más nuevo.
  Future<List<PendingOp>> pending(String owner);
  Future<int> pendingCount(String owner);
  Future<void> removeOp(int id);
  Future<void> markAttempt(int id, String? error);
}

/// Implementación en memoria: la usan las pruebas.
class MemoryLocalStore implements LocalStore {
  final Map<String, String> _cache = {};
  final List<PendingOp> _ops = [];
  int _nextId = 1;

  String _k(String owner, String key) => '$owner|$key';

  @override
  Future<void> putCache(String owner, String key, String json) async =>
      _cache[_k(owner, key)] = json;

  @override
  Future<String?> getCache(String owner, String key) async => _cache[_k(owner, key)];

  @override
  Future<void> deleteCache(String owner, String key) async =>
      _cache.remove(_k(owner, key));

  @override
  Future<int> enqueue(PendingOp op) async {
    final saved = op.copyWith(id: _nextId++);
    _ops.add(saved);
    return saved.id!;
  }

  @override
  Future<List<PendingOp>> pending(String owner) async =>
      [for (final op in _ops) if (op.owner == owner) op];

  @override
  Future<int> pendingCount(String owner) async =>
      _ops.where((op) => op.owner == owner).length;

  @override
  Future<void> removeOp(int id) async => _ops.removeWhere((op) => op.id == id);

  @override
  Future<void> markAttempt(int id, String? error) async {
    final index = _ops.indexWhere((op) => op.id == id);
    if (index < 0) return;
    _ops[index] = _ops[index].copyWith(attempts: _ops[index].attempts + 1, lastError: error);
  }
}

String encodePayload(Map<String, dynamic> payload) => jsonEncode(payload);
Map<String, dynamic> decodePayload(String text) =>
    jsonDecode(text) as Map<String, dynamic>;
