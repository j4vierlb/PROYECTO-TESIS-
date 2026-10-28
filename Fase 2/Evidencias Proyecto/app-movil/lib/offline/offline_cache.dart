// =============================================================================
// offline/offline_cache.dart — Última copia local de lo que entrega el backend
// -----------------------------------------------------------------------------
// Claves de la cache (siempre dentro de la cuenta dueña):
//   visitas_hoy       lista de la agenda del día
//   historial         primera página del historial
//   visita:<id>       una visita
//   croquis:<visitId> el croquis de una visita, con sus trampas
//   trampa:<id>       a qué visita pertenece una trampa (para ubicarla)
// Cualquier fallo del almacenamiento se traga: la app sigue funcionando como
// antes, solo que sin modo offline.
// =============================================================================

import 'dart:convert';

import '../models/croquis.dart';
import '../models/visita.dart';
import 'local_store.dart';

class OfflineCache {
  final LocalStore store;
  final Future<String?> Function() ownerProvider;

  OfflineCache(this.store, this.ownerProvider);

  Future<T?> _guard<T>(Future<T?> Function(String owner) action) async {
    try {
      final owner = await ownerProvider();
      if (owner == null) return null;
      return await action(owner);
    } catch (_) {
      return null;
    }
  }

  // --- Agenda e historial ---------------------------------------------------

  Future<List<Visita>?> readVisitasHoy() => _guard((owner) async {
        final text = await store.getCache(owner, 'visitas_hoy');
        return text == null ? null : _visitas(text);
      });

  Future<void> writeVisitasHoy(List<Visita> visitas) => _guard<void>((owner) async {
        await store.putCache(owner, 'visitas_hoy', jsonEncode([for (final v in visitas) v.toJson()]));
        for (final visita in visitas) {
          await store.putCache(owner, 'visita:${visita.id}', jsonEncode(visita.toJson()));
        }
      });

  Future<List<Visita>?> readHistorial() => _guard((owner) async {
        final text = await store.getCache(owner, 'historial');
        return text == null ? null : _visitas(text);
      });

  Future<void> writeHistorial(List<Visita> visitas) => _guard<void>((owner) async {
        await store.putCache(owner, 'historial', jsonEncode([for (final v in visitas) v.toJson()]));
      });

  List<Visita> _visitas(String text) => [
        for (final item in jsonDecode(text) as List<dynamic>) Visita.fromJson(item as Map<String, dynamic>),
      ];

  // --- Visitas --------------------------------------------------------------

  Future<Visita?> readVisita(String id) => _guard((owner) async {
        final text = await store.getCache(owner, 'visita:$id');
        return text == null ? null : Visita.fromJson(jsonDecode(text) as Map<String, dynamic>);
      });

  /// Guarda la visita y la actualiza también dentro de la agenda y del
  /// historial guardados, para que todas las pantallas coincidan.
  Future<void> writeVisita(Visita visita) => _guard<void>((owner) async {
        await store.putCache(owner, 'visita:${visita.id}', jsonEncode(visita.toJson()));
        for (final key in const ['visitas_hoy', 'historial']) {
          final text = await store.getCache(owner, key);
          if (text == null) continue;
          final list = jsonDecode(text) as List<dynamic>;
          var changed = false;
          for (var i = 0; i < list.length; i++) {
            final item = list[i] as Map<String, dynamic>;
            if (item['id'] == visita.id) {
              // El historial trae dispositivos_instalados; se conserva.
              final merged = visita.toJson();
              merged['dispositivos_instalados'] ??= item['dispositivos_instalados'];
              list[i] = merged;
              changed = true;
            }
          }
          if (changed) await store.putCache(owner, key, jsonEncode(list));
        }
      });

  /// Aplica un cambio local (estado y/o notas) a la copia guardada. Devuelve
  /// la visita ya modificada, o null si no hay copia guardada.
  Future<Visita?> patchVisita(String id, {String? estado, String? notas}) async {
    final current = await readVisita(id);
    if (current == null) return null;
    final json = current.toJson();
    if (estado != null) json['estado'] = estado;
    if (notas != null) json['notas'] = notas;
    final patched = Visita.fromJson(json);
    await writeVisita(patched);
    return patched;
  }

  // --- Croquis y trampas ----------------------------------------------------

  Future<Croquis?> readCroquis(String visitId) => _guard((owner) async {
        final text = await store.getCache(owner, 'croquis:$visitId');
        return text == null ? null : Croquis.fromJson(jsonDecode(text) as Map<String, dynamic>);
      });

  Future<void> writeCroquis(Croquis croquis) => _guard<void>((owner) async {
        await store.putCache(owner, 'croquis:${croquis.visitaId}', jsonEncode(croquis.toJson()));
        for (final device in croquis.dispositivos) {
          await store.putCache(owner, 'trampa:${device.id}', croquis.visitaId);
        }
      });

  /// Visita a la que pertenece una trampa, o null si no se conoce.
  Future<String?> visitOfDevice(String deviceId) =>
      _guard((owner) => store.getCache(owner, 'trampa:$deviceId'));

  /// Reemplaza la trampa (por id) dentro del croquis guardado, o la agrega si
  /// todavía no estaba. Devuelve false si no hay croquis guardado.
  Future<bool> putDevice(String visitId, DispositivoTrampa device) async {
    final croquis = await readCroquis(visitId);
    if (croquis == null) return false;
    final devices = [...croquis.dispositivos];
    final index = devices.indexWhere((d) => d.id == device.id);
    if (index >= 0) {
      devices[index] = device;
    } else {
      devices.add(device);
    }
    await writeCroquis(croquis.copyWithDispositivos(devices));
    return true;
  }

  Future<DispositivoTrampa?> readDevice(String visitId, String deviceId) async {
    final croquis = await readCroquis(visitId);
    if (croquis == null) return null;
    for (final d in croquis.dispositivos) {
      if (d.id == deviceId) return d;
    }
    return null;
  }

  /// Aplica a la copia local el efecto de una acción sobre una trampa, igual
  /// que lo haría el backend: confirmar la marca confirmada, mover cambia su
  /// ubicación y eliminar la deja "retirado".
  Future<DispositivoTrampa?> patchDevice(
    String visitId,
    String deviceId,
    String accion, {
    double? lat,
    double? lng,
  }) async {
    final current = await readDevice(visitId, deviceId);
    if (current == null) return null;
    final json = current.toJson();
    switch (accion) {
      case 'confirmar':
        json['confirmado'] = true;
      case 'mover':
        if (lat != null && lng != null) {
          json['lat'] = lat;
          json['lng'] = lng;
        }
      case 'eliminar':
        json['estado'] = 'retirado';
    }
    final patched = DispositivoTrampa.fromJson(json);
    await putDevice(visitId, patched);
    return patched;
  }

  /// Borra la copia de una visita y de su croquis: la próxima lectura los
  /// pedirá de nuevo al servidor (se usa cuando un cambio local se descartó).
  Future<void> invalidateVisit(String visitId) => _guard<void>((owner) async {
        await store.deleteCache(owner, 'visita:$visitId');
        await store.deleteCache(owner, 'croquis:$visitId');
      });
}
