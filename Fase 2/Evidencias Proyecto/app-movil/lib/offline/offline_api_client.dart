// =============================================================================
// offline/offline_api_client.dart — ApiClient que funciona sin señal
// -----------------------------------------------------------------------------
// Las pantallas ya usan un ApiClient. Este lo reemplaza sin que cambien:
//   - Las LECTURAS (agenda, visita, croquis, historial) siguen el camino de
//     SyncService: servidor primero y, sin señal, la última copia guardada.
//   - Las ESCRITURAS (estado y notas de la visita, acciones sobre trampas,
//     trampas nuevas, fotos) se guardan primero en el teléfono, se aplican en
//     la copia local para que el técnico las vea de inmediato, y se envían al
//     servidor en cuanto se puede. Sin señal quedan en cola.
// Si el almacenamiento local falla, cada método hace la petición normal.
// =============================================================================

import 'dart:math';

import '../models/croquis.dart';
import '../models/visita.dart';
import '../services/api_client.dart';
import 'local_store.dart';
import 'outbox_files.dart';
import 'sync_service.dart';

class OfflineApiClient extends ApiClient {
  final SyncService sync;
  final OutboxFiles outbox;

  OfflineApiClient({SyncService? sync, OutboxFiles? files})
      : sync = sync ?? SyncService.shared,
        outbox = files ?? const OutboxFiles();

  /// Instancia que usan las pantallas por defecto.
  static final OfflineApiClient shared = OfflineApiClient();

  /// true si todavía quedan cambios sin enviar: sirve para decirle al técnico
  /// "guardado en el teléfono" en lugar de "guardado".
  bool get hayPendientes => sync.status.value.pending > 0;

  // --- Lecturas -------------------------------------------------------------

  @override
  Future<List<Visita>> fetchVisitasHoy() => sync.refreshAgenda();

  @override
  Future<List<Visita>> fetchVisitasProximas({int dias = 14}) => sync.readProximas(dias);

  @override
  Future<List<Visita>> fetchHistorial({int limit = 20, int offset = 0}) =>
      sync.readHistorial(limit, offset);

  @override
  Future<Visita> fetchVisita(String visitaId) => sync.readVisita(visitaId);

  @override
  Future<Croquis> fetchCroquis(String visitaId) => sync.readCroquis(visitaId);

  @override
  Future<Croquis> createCroquis(String visitaId) => sync.createCroquis(visitaId);

  // --- Escrituras -----------------------------------------------------------

  @override
  Future<Visita> updateVisita(String visitaId, {String? estado, String? notas}) async {
    final owner = await sync.ownerProvider();
    final actual = owner == null ? null : await sync.cache.readVisita(visitaId);
    if (owner == null || actual == null) {
      return sync.remote.updateVisita(visitaId, estado: estado, notas: notas);
    }
    try {
      await sync.enqueue(PendingOp(
        owner: owner,
        kind: OpKind.visitaUpdate,
        visitId: visitaId,
        payload: {'estado': ?estado, 'notas': ?notas},
        createdAt: DateTime.now(),
      ));
    } catch (_) {
      return sync.remote.updateVisita(visitaId, estado: estado, notas: notas);
    }
    await sync.cache.patchVisita(visitaId, estado: estado, notas: notas);
    await sync.flushUnlessOffline();
    // Si el servidor descartó el cambio por conflicto, la copia se borró: se
    // vuelve a pedir tal como quedó allá.
    return (await sync.cache.readVisita(visitaId)) ?? await sync.readVisita(visitaId);
  }

  @override
  Future<DispositivoTrampa> updateDispositivo(
    String dispositivoId,
    String accion, {
    double? lat,
    double? lng,
  }) async {
    final owner = await sync.ownerProvider();
    final visitaId = owner == null ? null : await sync.cache.visitOfDevice(dispositivoId);
    final actual = visitaId == null ? null : await sync.cache.readDevice(visitaId, dispositivoId);
    if (owner == null || visitaId == null || actual == null) {
      return sync.remote.updateDispositivo(dispositivoId, accion, lat: lat, lng: lng);
    }
    try {
      await sync.enqueue(PendingOp(
        owner: owner,
        kind: OpKind.dispositivoUpdate,
        visitId: visitaId,
        payload: {'id': dispositivoId, 'accion': accion, 'lat': ?lat, 'lng': ?lng},
        createdAt: DateTime.now(),
      ));
    } catch (_) {
      return sync.remote.updateDispositivo(dispositivoId, accion, lat: lat, lng: lng);
    }
    await sync.cache.patchDevice(visitaId, dispositivoId, accion, lat: lat, lng: lng);
    await sync.flushUnlessOffline();
    // Si el cambio se descartó por conflicto, la trampa vuelve a como está en
    // el servidor (la pantalla muestra el aviso del banner).
    return (await sync.cache.readDevice(visitaId, dispositivoId)) ?? actual;
  }

  @override
  Future<DispositivoTrampa> addDispositivo(
    String visitaId, {
    String? id,
    required String tipo,
    required double lat,
    required double lng,
  }) async {
    final owner = await sync.ownerProvider();
    final croquis = owner == null ? null : await sync.cache.readCroquis(visitaId);
    if (owner == null || croquis == null) {
      return sync.remote.addDispositivo(visitaId, id: id, tipo: tipo, lat: lat, lng: lng);
    }
    // El id lo genera el teléfono: así reintentar el envío no duplica la trampa.
    final trampaId = id ?? nuevoUuid();
    try {
      await sync.enqueue(PendingOp(
        owner: owner,
        kind: OpKind.dispositivoAdd,
        visitId: visitaId,
        payload: {'id': trampaId, 'tipo': tipo, 'lat': lat, 'lng': lng},
        createdAt: DateTime.now(),
      ));
    } catch (_) {
      return sync.remote.addDispositivo(visitaId, id: id, tipo: tipo, lat: lat, lng: lng);
    }
    // El código definitivo (T-05...) lo asigna el servidor al sincronizar.
    final provisoria = DispositivoTrampa(
      id: trampaId,
      codigo: 'Trampa nueva',
      tipo: tipo,
      lat: lat,
      lng: lng,
      sugeridoPorIa: false,
      confirmado: true,
      estado: 'activo',
    );
    await sync.cache.putDevice(visitaId, provisoria);
    await sync.flushUnlessOffline();
    final guardada = await sync.cache.readDevice(visitaId, trampaId);
    if (guardada == null) {
      throw ApiException(409, 'No se pudo agregar la trampa: la visita cambió en el sistema');
    }
    return guardada;
  }

  @override
  Future<DispositivoTrampa> uploadFoto(
    String dispositivoId,
    String rutaArchivo, {
    bool reintento = false,
  }) async {
    final owner = await sync.ownerProvider();
    final visitaId = owner == null ? null : await sync.cache.visitOfDevice(dispositivoId);
    if (owner == null || visitaId == null) {
      return sync.remote.uploadFoto(dispositivoId, rutaArchivo, reintento: reintento);
    }
    // La foto se copia a una carpeta propia: la cola no depende de la copia
    // temporal de la captura, que se borra al terminar el flujo de la cámara.
    final String guardada;
    try {
      guardada = await outbox.keep(rutaArchivo);
    } catch (_) {
      return sync.remote.uploadFoto(dispositivoId, rutaArchivo, reintento: reintento);
    }
    try {
      await sync.enqueue(PendingOp(
        owner: owner,
        kind: OpKind.foto,
        visitId: visitaId,
        payload: {'deviceId': dispositivoId, 'path': guardada},
        createdAt: DateTime.now(),
      ));
    } catch (_) {
      await outbox.remove(guardada);
      return sync.remote.uploadFoto(dispositivoId, rutaArchivo, reintento: reintento);
    }
    await sync.flushUnlessOffline();
    final trampa = await sync.cache.readDevice(visitaId, dispositivoId);
    if (trampa == null) {
      throw ApiException(409, 'No se pudo guardar la foto: la trampa ya no existe en el sistema');
    }
    return trampa;
  }
}

/// Mensaje de éxito para el técnico: si el cambio quedó en cola por falta de
/// señal, lo dice con claridad en lugar de afirmar que ya llegó al servidor.
String mensajeGuardado(ApiClient client, String ok) =>
    client is OfflineApiClient && client.hayPendientes
        ? 'Guardado en el teléfono. Se enviará cuando haya señal.'
        : ok;

/// Identificador único (UUID v4) generado en el teléfono.
String nuevoUuid([Random? random]) {
  final rng = random ?? Random.secure();
  final bytes = List<int>.generate(16, (_) => rng.nextInt(256));
  bytes[6] = (bytes[6] & 0x0f) | 0x40; // versión 4
  bytes[8] = (bytes[8] & 0x3f) | 0x80; // variante RFC 4122
  String hex(int from, int to) =>
      bytes.sublist(from, to).map((b) => b.toRadixString(16).padLeft(2, '0')).join();
  return '${hex(0, 4)}-${hex(4, 6)}-${hex(6, 8)}-${hex(8, 10)}-${hex(10, 16)}';
}
