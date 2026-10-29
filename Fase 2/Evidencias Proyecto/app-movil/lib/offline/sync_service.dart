// =============================================================================
// offline/sync_service.dart — Motor del modo offline
// -----------------------------------------------------------------------------
// Hace tres cosas:
//   1. LEER con respaldo: pide los datos al backend y los guarda en el
//      teléfono; si no hay señal, entrega la última copia guardada.
//   2. ENVIAR lo pendiente: los cambios hechos sin señal esperan en una cola y
//      se mandan, en orden, apenas vuelve la conexión.
//   3. DECIDIR conflictos: si el servidor cambió algo mientras el técnico
//      estaba sin señal (visita cerrada o cancelada, trampa ya inexistente...),
//      el servidor gana: ese cambio se descarta y se le avisa al técnico.
// =============================================================================

import 'dart:async';

import 'package:flutter/widgets.dart';

import '../models/croquis.dart';
import '../models/visita.dart';
import '../services/api_client.dart';
import 'local_store.dart';
import 'offline_cache.dart';
import 'outbox_files.dart';
import 'owner.dart';
import 'sqlite_local_store.dart';

/// Lo que la pantalla necesita saber para avisarle al técnico.
class SyncStatus {
  final int pending; // cambios guardados que aún no se enviaron
  final bool syncing; // enviando ahora mismo
  final bool offline; // el último intento de hablar con el servidor falló
  final List<String> conflicts; // cambios descartados que el técnico no ha visto

  const SyncStatus({
    this.pending = 0,
    this.syncing = false,
    this.offline = false,
    this.conflicts = const [],
  });

  bool get visible => offline || pending > 0 || syncing || conflicts.isNotEmpty;

  SyncStatus copyWith({int? pending, bool? syncing, bool? offline, List<String>? conflicts}) => SyncStatus(
        pending: pending ?? this.pending,
        syncing: syncing ?? this.syncing,
        offline: offline ?? this.offline,
        conflicts: conflicts ?? this.conflicts,
      );
}

/// Un cambio que el servidor ya no acepta porque la situación cambió.
class _Conflict implements Exception {
  final String message;
  _Conflict(this.message);
}

class SyncService with WidgetsBindingObserver {
  final LocalStore store;
  // Cliente SIN modo offline: el motor habla directo con el backend.
  final ApiClient remote;
  final Future<String?> Function() ownerProvider;
  final OutboxFiles files;
  final Duration pollInterval;
  late final OfflineCache cache = OfflineCache(store, ownerProvider);

  final ValueNotifier<SyncStatus> status = ValueNotifier(const SyncStatus());

  SyncService({
    required this.store,
    required this.remote,
    Future<String?> Function()? ownerProvider,
    OutboxFiles? files,
    this.pollInterval = const Duration(seconds: 20),
  })  : ownerProvider = ownerProvider ?? currentOwner,
        files = files ?? const OutboxFiles();

  /// Instancia compartida por toda la app.
  static final SyncService shared = SyncService(store: SqliteLocalStore(), remote: ApiClient());

  DateTime? _offlineSince;
  Future<void>? _flushing;
  Future<void>? _prefetching;
  Timer? _timer;

  // --- Ciclo de vida --------------------------------------------------------

  /// Activa el envío automático: cada pocos segundos y al volver a la app.
  void start() {
    WidgetsBinding.instance.addObserver(this);
    _timer ??= Timer.periodic(pollInterval, (_) => unawaited(tick()));
    unawaited(refreshPending());
  }

  void stop() {
    WidgetsBinding.instance.removeObserver(this);
    _timer?.cancel();
    _timer = null;
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) unawaited(tick());
  }

  /// Un ciclo de trabajo: envía lo pendiente o, si no hay nada pendiente pero
  /// se había perdido la señal, comprueba si ya volvió.
  Future<void> tick() async {
    try {
      if (await pendingCount() > 0) {
        await flush();
      } else if (status.value.offline) {
        await refreshAgenda();
      }
    } catch (_) {
      // Sin señal: se reintenta en el próximo ciclo.
    }
  }

  // --- Estado ---------------------------------------------------------------

  void _set({int? pending, bool? syncing, bool? offline, List<String>? conflicts}) {
    status.value = status.value.copyWith(
      pending: pending,
      syncing: syncing,
      offline: offline,
      conflicts: conflicts,
    );
  }

  void markOnline() {
    _offlineSince = null;
    if (status.value.offline) _set(offline: false);
  }

  void markOffline() {
    _offlineSince = DateTime.now();
    if (!status.value.offline) _set(offline: true);
  }

  /// true si hace muy poco falló la conexión: no tiene sentido esperar otro
  /// tiempo de espera completo antes de guardar el cambio en el teléfono.
  bool get _recentlyOffline =>
      _offlineSince != null && DateTime.now().difference(_offlineSince!) < const Duration(seconds: 15);

  Future<int> pendingCount() async {
    try {
      final owner = await ownerProvider();
      return owner == null ? 0 : await store.pendingCount(owner);
    } catch (_) {
      return 0;
    }
  }

  Future<void> refreshPending() async => _set(pending: await pendingCount());

  /// El técnico ya vio los avisos de cambios descartados.
  void dismissConflicts() => _set(conflicts: const []);

  /// Guarda un cambio en la cola. Lanza si el almacenamiento falla (quien
  /// llama entonces hace la petición directa, como antes del modo offline).
  Future<void> enqueue(PendingOp op) async {
    await store.enqueue(op);
    await refreshPending();
  }

  // --- Envío de lo pendiente ------------------------------------------------

  Future<void> flushUnlessOffline() => _recentlyOffline ? Future.value() : flush();

  /// Envía los cambios pendientes en orden. Si la conexión falla, se detiene y
  /// conserva todo; si el servidor rechaza uno por conflicto, lo descarta y
  /// sigue con el siguiente.
  Future<void> flush() => _flushing ??= _flush().whenComplete(() => _flushing = null);

  Future<void> _flush() async {
    String? owner;
    List<PendingOp> ops;
    try {
      owner = await ownerProvider();
      if (owner == null) return;
      ops = await store.pending(owner);
    } catch (_) {
      return;
    }
    if (ops.isEmpty) {
      _set(pending: 0, syncing: false);
      return;
    }

    _set(syncing: true);
    final conflicts = <String>[];
    for (final op in ops) {
      try {
        await _apply(op);
        await store.removeOp(op.id!);
        markOnline();
      } on _Conflict catch (conflict) {
        await _discard(op);
        conflicts.add('No se pudo ${op.descripcion}: ${conflict.message}.');
      } on ApiException catch (error) {
        if (error.statusCode == 401) {
          // Sesión vencida: el trabajo se conserva hasta volver a entrar.
          await store.markAttempt(op.id!, error.message);
          break;
        }
        if (esReintentable(error)) {
          await store.markAttempt(op.id!, error.message);
          break;
        }
        await _discard(op);
        conflicts.add('No se pudo ${op.descripcion}: ${error.message}.');
      } catch (error) {
        // Error de red u otro imprevisto: se conserva y se reintenta luego.
        await store.markAttempt(op.id!, error.toString());
        if (esErrorDeRed(error)) markOffline();
        break;
      }
    }

    int remaining = 0;
    try {
      remaining = await store.pendingCount(owner);
    } catch (_) {
      remaining = ops.length;
    }
    _set(
      pending: remaining,
      syncing: false,
      conflicts: [...status.value.conflicts, ...conflicts],
    );
  }

  /// Quita el cambio de la cola y deja que la próxima lectura vuelva a pedir
  /// al servidor lo que el técnico tenía modificado localmente.
  Future<void> _discard(PendingOp op) async {
    await store.removeOp(op.id!);
    if (op.kind == OpKind.foto) {
      final path = op.payload['path'] as String?;
      if (path != null) await files.remove(path);
    }
    await cache.invalidateVisit(op.visitId);
  }

  Future<void> _apply(PendingOp op) async {
    final data = op.payload;
    switch (op.kind) {
      case OpKind.visitaUpdate:
        final estado = data['estado'] as String?;
        final notas = data['notas'] as String?;
        // El servidor gana: antes de pisar la visita se mira cómo está allá.
        final actual = await remote.fetchVisita(op.visitId);
        final cerrada = actual.estado == 'completada' || actual.estado == 'cancelada';
        if (estado != null && estado == actual.estado && notas == null) {
          await cache.writeVisita(actual); // ya estaba aplicado
          return;
        }
        if (cerrada) {
          throw _Conflict('la visita ya figura como ${actual.estado} en el sistema');
        }
        final actualizada = await remote.updateVisita(op.visitId, estado: estado, notas: notas);
        await cache.writeVisita(actualizada);
      case OpKind.dispositivoUpdate:
        final trampa = await remote.updateDispositivo(
          data['id'] as String,
          data['accion'] as String,
          lat: (data['lat'] as num?)?.toDouble(),
          lng: (data['lng'] as num?)?.toDouble(),
        );
        await cache.putDevice(op.visitId, trampa);
      case OpKind.dispositivoAdd:
        final trampa = await remote.addDispositivo(
          op.visitId,
          id: data['id'] as String,
          tipo: data['tipo'] as String,
          lat: (data['lat'] as num).toDouble(),
          lng: (data['lng'] as num).toDouble(),
        );
        await cache.putDevice(op.visitId, trampa);
      case OpKind.foto:
        final path = data['path'] as String;
        if (!await files.exists(path)) throw _Conflict('la foto ya no está guardada en el teléfono');
        final trampa = await remote.uploadFoto(data['deviceId'] as String, path);
        await cache.putDevice(op.visitId, trampa);
        await files.remove(path);
      default:
        throw _Conflict('tipo de cambio desconocido');
    }
  }

  // --- Lecturas con respaldo ------------------------------------------------

  /// Pide al servidor y guarda la copia; sin señal entrega la última guardada.
  /// Si hay cambios sin enviar, muestra la copia local (que ya los incluye)
  /// para no volver atrás lo que el técnico acaba de hacer.
  Future<T> _read<T>({
    required Future<T> Function() fromServer,
    required Future<T?> Function() fromCache,
    required Future<void> Function(T value) save,
  }) async {
    await flushUnlessOffline();
    if (await pendingCount() > 0) {
      final local = await fromCache();
      if (local != null) return local;
    }
    try {
      final value = await fromServer();
      await save(value);
      markOnline();
      return value;
    } catch (error) {
      if (!esReintentable(error)) rethrow;
      if (esErrorDeRed(error)) markOffline();
      final local = await fromCache();
      if (local != null) return local;
      rethrow;
    }
  }

  Future<List<Visita>> refreshAgenda() async {
    final visitas = await _read<List<Visita>>(
      fromServer: remote.fetchVisitasHoy,
      fromCache: cache.readVisitasHoy,
      save: cache.writeVisitasHoy,
    );
    // Se deja todo lo del día listo en el teléfono, por si se pierde la señal.
    if (!status.value.offline) unawaited(prefetch(visitas));
    return visitas;
  }

  /// Visitas de los próximos días: servidor primero y, sin señal, la última
  /// copia guardada. Se guarda siempre la última lista pedida, sin importar `dias`.
  Future<List<Visita>> readProximas(int dias) => _read<List<Visita>>(
        fromServer: () => remote.fetchVisitasProximas(dias: dias),
        fromCache: cache.readProximas,
        save: cache.writeProximas,
      );

  Future<List<Visita>> readHistorial(int limit, int offset) => _read<List<Visita>>(
        fromServer: () => remote.fetchHistorial(limit: limit, offset: offset),
        // Solo la primera página se guarda; las siguientes exigen conexión.
        fromCache: () async => offset == 0 ? cache.readHistorial() : null,
        save: (visitas) async {
          if (offset == 0) await cache.writeHistorial(visitas);
        },
      );

  Future<Visita> readVisita(String id) => _read<Visita>(
        fromServer: () => remote.fetchVisita(id),
        fromCache: () => cache.readVisita(id),
        save: cache.writeVisita,
      );

  Future<Croquis> readCroquis(String visitId) => _read<Croquis>(
        fromServer: () => remote.fetchCroquis(visitId),
        fromCache: () => cache.readCroquis(visitId),
        save: cache.writeCroquis,
      );

  Future<Croquis> createCroquis(String visitId) async {
    final croquis = await remote.createCroquis(visitId);
    await cache.writeCroquis(croquis);
    markOnline();
    return croquis;
  }

  // --- Preparar el día ------------------------------------------------------

  /// Baja el croquis de cada visita del día para poder trabajar sin señal. Si
  /// una visita abierta todavía no tiene croquis, se crea (lo mismo que haría
  /// la app al abrirla). No pisa nada si hay cambios sin enviar.
  Future<void> prefetch(List<Visita> visitas) => _prefetching ??= _prefetch(visitas).whenComplete(() => _prefetching = null);

  Future<void> _prefetch(List<Visita> visitas) async {
    for (final visita in visitas) {
      if (visita.estado == 'cancelada') continue;
      if (await pendingCount() > 0) return;
      final abierta = visita.estado != 'completada';
      try {
        Croquis croquis;
        try {
          croquis = await remote.fetchCroquis(visita.id);
        } on ApiException catch (error) {
          if (error.statusCode != 404 || !abierta) rethrow;
          croquis = await remote.createCroquis(visita.id);
        }
        if (await pendingCount() > 0) return;
        await cache.writeCroquis(croquis);
      } catch (error) {
        if (esReintentable(error)) return; // sin señal: se reintenta después
        // Otro rechazo del servidor para esta visita: se sigue con la siguiente.
      }
    }
  }
}
