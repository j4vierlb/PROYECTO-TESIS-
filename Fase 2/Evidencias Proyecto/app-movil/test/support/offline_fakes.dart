// Simuladores compartidos por las pruebas del modo offline: un servidor que se
// puede "desconectar", un almacén en memoria y una carpeta de fotos falsa.

import 'dart:io';

import 'package:app_movil/models/croquis.dart';
import 'package:app_movil/models/visita.dart';
import 'package:app_movil/offline/local_store.dart';
import 'package:app_movil/offline/offline_api_client.dart';
import 'package:app_movil/offline/outbox_files.dart';
import 'package:app_movil/offline/sync_service.dart';
import 'package:app_movil/services/api_client.dart';

const visitaId = '11111111-1111-1111-1111-111111111111';
const otraVisitaId = '22222222-2222-2222-2222-222222222222';
const trampaId = '33333333-3333-3333-3333-333333333333';

Visita visita(String id, {String estado = 'agendada', String? notas}) => Visita.fromJson({
      'id': id,
      'cliente': {
        'id': 'c-1',
        'nombre': 'Restaurante Don José',
        'telefono_whatsapp': '+56911111111',
        'direccion': 'Av. Macul 123',
        'lat': -33.48,
        'lng': -70.59,
      },
      'operador_id': 'op-1',
      'fecha_hora': '2026-10-27T13:00:00Z',
      'estado': estado,
      'origen_agendamiento': 'manual',
      'notas': notas,
    });

Map<String, dynamic> trampaJson(String id, String codigo, {bool confirmado = false, String estado = 'activo'}) => {
      'id': id,
      'codigo': codigo,
      'tipo': 'cebadero',
      'lat': -33.4801,
      'lng': -70.5901,
      'sugerido_por_ia': true,
      'confirmado': confirmado,
      'estado': estado,
      'foto_url': null,
    };

Croquis croquis(String visitId, List<Map<String, dynamic>> trampas) => Croquis.fromJson({
      'id': 'cr-$visitId',
      'visita_id': visitId,
      'cliente_id': 'c-1',
      'version': 1,
      'imagen_satelital_url': null,
      'sugerido_por_ia': false,
      'validado_por_operador': false,
      'dispositivos': trampas,
    });

/// Servidor simulado: guarda el estado "real" y falla con SocketException
/// cuando `online` es false.
class FakeRemote extends ApiClient {
  bool online = true;
  int? failWithStatus; // si se define, toda petición responde ese error HTTP
  bool cutAfterUpdate = false; // se desconecta justo después de un updateVisita
  final Map<String, Visita> visitas = {};
  final Map<String, Croquis> croquisPorVisita = {};
  final List<String> calls = [];
  int proximoCodigo = 2;

  void _check() {
    if (!online) throw const SocketException('Sin señal');
    final status = failWithStatus;
    if (status != null) throw ApiException(status, 'Error $status');
  }

  @override
  Future<List<Visita>> fetchVisitasHoy() async {
    _check();
    calls.add('fetchVisitasHoy');
    return visitas.values.toList();
  }

  @override
  Future<List<Visita>> fetchHistorial({int limit = 20, int offset = 0}) async {
    _check();
    calls.add('fetchHistorial');
    return [visita('hist-1', estado: 'completada')];
  }

  @override
  Future<Visita> fetchVisita(String visitaId) async {
    _check();
    calls.add('fetchVisita');
    final found = visitas[visitaId];
    if (found == null) throw ApiException(404, 'Visita no encontrada');
    return found;
  }

  @override
  Future<Croquis> fetchCroquis(String visitaId) async {
    _check();
    calls.add('fetchCroquis:$visitaId');
    final found = croquisPorVisita[visitaId];
    if (found == null) throw ApiException(404, 'Croquis no encontrado');
    return found;
  }

  @override
  Future<Croquis> createCroquis(String visitaId) async {
    _check();
    calls.add('createCroquis:$visitaId');
    return croquisPorVisita[visitaId] = croquis(visitaId, []);
  }

  @override
  Future<Visita> updateVisita(String visitaId, {String? estado, String? notas}) async {
    _check();
    calls.add('updateVisita:${estado ?? '-'}:${notas ?? '-'}');
    final actual = visitas[visitaId]!;
    final json = actual.toJson();
    if (estado != null) json['estado'] = estado;
    if (notas != null) json['notas'] = notas;
    final actualizada = visitas[visitaId] = Visita.fromJson(json);
    if (cutAfterUpdate) online = false;
    return actualizada;
  }

  Croquis _croquisDe(String trampaId) => croquisPorVisita.values.firstWhere(
        (c) => c.dispositivos.any((d) => d.id == trampaId),
        orElse: () => throw ApiException(404, 'Trampa no encontrada'),
      );

  @override
  Future<DispositivoTrampa> updateDispositivo(String dispositivoId, String accion, {double? lat, double? lng}) async {
    _check();
    calls.add('updateDispositivo:$accion');
    final cr = _croquisDe(dispositivoId);
    final json = cr.dispositivos.firstWhere((d) => d.id == dispositivoId).toJson();
    if (accion == 'confirmar') json['confirmado'] = true;
    if (accion == 'eliminar') json['estado'] = 'retirado';
    if (accion == 'mover') {
      json['lat'] = lat;
      json['lng'] = lng;
    }
    final nueva = DispositivoTrampa.fromJson(json);
    croquisPorVisita[cr.visitaId] =
        cr.copyWithDispositivos([for (final d in cr.dispositivos) d.id == dispositivoId ? nueva : d]);
    return nueva;
  }

  @override
  Future<DispositivoTrampa> addDispositivo(
    String visitaId, {
    String? id,
    required String tipo,
    required double lat,
    required double lng,
  }) async {
    _check();
    calls.add('addDispositivo:$id');
    final cr = croquisPorVisita[visitaId];
    if (cr == null) throw ApiException(404, 'Croquis no encontrado');
    // Idempotente, como el backend: el mismo id no se duplica.
    for (final d in cr.dispositivos) {
      if (d.id == id) return d;
    }
    final nueva = DispositivoTrampa.fromJson({
      ...trampaJson(id ?? 'sin-id', 'T-0${proximoCodigo++}', confirmado: true),
      'sugerido_por_ia': false,
      'tipo': tipo,
      'lat': lat,
      'lng': lng,
    });
    croquisPorVisita[visitaId] = cr.copyWithDispositivos([...cr.dispositivos, nueva]);
    return nueva;
  }

  @override
  Future<DispositivoTrampa> uploadFoto(String dispositivoId, String rutaArchivo, {bool reintento = false}) async {
    _check();
    calls.add('uploadFoto:$rutaArchivo');
    final cr = _croquisDe(dispositivoId);
    final json = cr.dispositivos.firstWhere((d) => d.id == dispositivoId).toJson();
    json['foto_url'] = '/dispositivos-trampa/$dispositivoId/foto?v=1';
    final nueva = DispositivoTrampa.fromJson(json);
    croquisPorVisita[cr.visitaId] =
        cr.copyWithDispositivos([for (final d in cr.dispositivos) d.id == dispositivoId ? nueva : d]);
    return nueva;
  }
}

/// Reemplaza la carpeta de fotos pendientes por una lista en memoria.
class FakeOutbox extends OutboxFiles {
  final Set<String> guardadas = {};
  final List<String> borradas = [];
  int _n = 0;

  @override
  Future<String> keep(String sourcePath) async {
    final copia = '/outbox/copia_${_n++}.jpg';
    guardadas.add(copia);
    return copia;
  }

  @override
  Future<bool> exists(String path) async => guardadas.contains(path);

  @override
  Future<void> remove(String path) async {
    guardadas.remove(path);
    borradas.add(path);
  }
}

class Entorno {
  final FakeRemote remote = FakeRemote();
  final MemoryLocalStore store = MemoryLocalStore();
  final FakeOutbox outbox = FakeOutbox();
  String? owner = 'tecnico-1';
  late final SyncService sync = SyncService(
    store: store,
    remote: remote,
    ownerProvider: () async => owner,
    files: outbox,
  );
  late final OfflineApiClient client = OfflineApiClient(sync: sync, files: outbox);

  /// Servidor con una visita y un croquis con una trampa sugerida por la IA.
  Entorno() {
    remote.visitas[visitaId] = visita(visitaId);
    remote.croquisPorVisita[visitaId] = croquis(visitaId, [trampaJson(trampaId, 'T-01')]);
  }

  /// Abre la agenda y el croquis con señal, como hace el técnico al empezar el día.
  Future<void> prepararDia() async {
    await client.fetchVisitasHoy();
    await sync.prefetch(await client.fetchVisitasHoy());
  }

  Visita get visitaServidor => remote.visitas[visitaId]!;
  Croquis get croquisServidor => remote.croquisPorVisita[visitaId]!;
}
