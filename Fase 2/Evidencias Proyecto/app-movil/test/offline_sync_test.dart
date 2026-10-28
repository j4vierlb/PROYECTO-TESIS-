// Pruebas del modo offline: lectura con respaldo, cola de cambios, orden de
// envío, conflictos (el servidor gana), cuentas separadas y trampas sin duplicar.
// No usan red ni SQLite: un servidor simulado que se puede "desconectar" y un
// almacén en memoria (ver support/offline_fakes.dart).

import 'dart:io';

import 'package:app_movil/offline/local_store.dart';
import 'package:app_movil/offline/offline_api_client.dart';
import 'package:app_movil/offline/sync_service.dart';
import 'package:app_movil/services/api_client.dart';
import 'package:flutter_test/flutter_test.dart';

import 'support/offline_fakes.dart';

void main() {
  group('Lectura con respaldo', () {
    test('con señal guarda la agenda y el croquis; sin señal los entrega', () async {
      final e = Entorno();
      await e.prepararDia();
      expect(e.remote.calls, contains('fetchCroquis:$visitaId'));

      e.remote.online = false;
      final agenda = await e.client.fetchVisitasHoy();
      final detalle = await e.client.fetchVisita(visitaId);
      final mapa = await e.client.fetchCroquis(visitaId);

      expect(agenda.single.cliente.nombre, 'Restaurante Don José');
      expect(detalle.estado, 'agendada');
      expect(mapa.dispositivos.single.codigo, 'T-01');
      expect(e.sync.status.value.offline, isTrue);
    });

    test('sin señal y sin nada guardado el error llega a la pantalla', () async {
      final e = Entorno();
      e.remote.online = false;
      await expectLater(e.client.fetchVisitasHoy(), throwsA(isA<SocketException>()));
      await expectLater(e.client.fetchCroquis(visitaId), throwsA(isA<SocketException>()));
    });

    test('al volver la señal se marca conectado y se actualiza la copia', () async {
      final e = Entorno();
      await e.prepararDia();
      e.remote.online = false;
      await e.client.fetchVisitasHoy();
      expect(e.sync.status.value.offline, isTrue);

      e.remote.online = true;
      e.remote.visitas[visitaId] = visita(visitaId, estado: 'en_curso');
      final agenda = await e.sync.refreshAgenda();
      expect(agenda.single.estado, 'en_curso');
      expect(e.sync.status.value.offline, isFalse);
    });

    test('el historial guarda solo la primera página', () async {
      final e = Entorno();
      await e.client.fetchHistorial();
      e.remote.online = false;
      expect((await e.client.fetchHistorial()).single.estado, 'completada');
      await expectLater(e.client.fetchHistorial(offset: 20), throwsA(isA<SocketException>()));
    });

    test('un error 5xx también cae a la copia guardada', () async {
      final e = Entorno();
      await e.prepararDia();
      e.remote.failWithStatus = 503;
      expect((await e.client.fetchVisita(visitaId)).id, visitaId);
    });

    test('prepara el día: crea el croquis de una visita abierta que no tenía', () async {
      final e = Entorno();
      e.remote.croquisPorVisita.clear();
      await e.prepararDia();
      expect(e.remote.calls, contains('createCroquis:$visitaId'));
      e.remote.online = false;
      expect((await e.client.fetchCroquis(visitaId)).dispositivos, isEmpty);
    });

    test('una visita completada sin croquis no se crea al preparar el día', () async {
      final e = Entorno();
      e.remote.visitas[visitaId] = visita(visitaId, estado: 'completada');
      e.remote.croquisPorVisita.clear();
      await e.prepararDia();
      expect(e.remote.calls.where((c) => c.startsWith('createCroquis')), isEmpty);
    });
  });

  group('Cambios de la visita sin señal', () {
    test('iniciar visita sin señal: se ve al instante y se envía al volver', () async {
      final e = Entorno();
      await e.prepararDia();
      e.remote.online = false;

      final local = await e.client.updateVisita(visitaId, estado: 'en_curso');

      expect(local.estado, 'en_curso');
      expect(e.visitaServidor.estado, 'agendada'); // el servidor aún no lo sabe
      expect(e.sync.status.value.pending, 1);
      expect(e.client.hayPendientes, isTrue);
      expect((await e.client.fetchVisita(visitaId)).estado, 'en_curso');
      expect((await e.client.fetchVisitasHoy()).single.estado, 'en_curso');

      e.remote.online = true;
      await e.sync.flush();

      expect(e.visitaServidor.estado, 'en_curso');
      expect(e.sync.status.value.pending, 0);
      expect(e.sync.status.value.conflicts, isEmpty);
    });

    test('con señal el cambio se envía de inmediato y no queda en cola', () async {
      final e = Entorno();
      await e.prepararDia();
      final visita = await e.client.updateVisita(visitaId, estado: 'en_curso');
      expect(visita.estado, 'en_curso');
      expect(e.visitaServidor.estado, 'en_curso');
      expect(e.sync.status.value.pending, 0);
      expect(e.client.hayPendientes, isFalse);
    });

    test('los cambios se envían en el mismo orden en que se hicieron', () async {
      final e = Entorno();
      await e.prepararDia();
      e.remote.online = false;
      await e.client.updateVisita(visitaId, estado: 'en_curso');
      await e.client.updateVisita(visitaId, notas: 'Había roedores en la bodega');
      await e.client.updateVisita(visitaId, estado: 'completada');
      expect(e.sync.status.value.pending, 3);

      e.remote.online = true;
      e.remote.calls.clear();
      await e.sync.flush();

      expect(
        e.remote.calls.where((c) => c.startsWith('updateVisita')),
        ['updateVisita:en_curso:-', 'updateVisita:-:Había roedores en la bodega', 'updateVisita:completada:-'],
      );
      expect(e.visitaServidor.estado, 'completada');
      expect(e.visitaServidor.notas, 'Había roedores en la bodega');
    });

    test('si la conexión se corta a mitad del envío, lo que falta se conserva', () async {
      final e = Entorno();
      await e.prepararDia();
      e.remote.online = false;
      await e.client.updateVisita(visitaId, estado: 'en_curso');
      await e.client.updateVisita(visitaId, notas: 'Notas');

      // Vuelve la señal, pasa el primer envío y se corta antes del segundo.
      e.remote.online = true;
      e.remote.cutAfterUpdate = true;
      await e.sync.flush();

      expect(e.visitaServidor.estado, 'en_curso');
      expect(e.visitaServidor.notas, isNull);
      expect(e.sync.status.value.pending, 1);
      expect(e.sync.status.value.offline, isTrue);

      e.remote.cutAfterUpdate = false;
      e.remote.online = true;
      await e.sync.flush();
      expect(e.visitaServidor.notas, 'Notas');
      expect(e.sync.status.value.pending, 0);
    });

    test('un error 5xx conserva el cambio para reintentar', () async {
      final e = Entorno();
      await e.prepararDia();
      e.remote.failWithStatus = 503;
      await e.client.updateVisita(visitaId, estado: 'en_curso');
      expect(e.sync.status.value.pending, 1);
      expect(e.sync.status.value.conflicts, isEmpty);
    });

    test('sesión vencida (401) conserva el cambio hasta volver a entrar', () async {
      final e = Entorno();
      await e.prepararDia();
      e.remote.failWithStatus = 401;
      await e.client.updateVisita(visitaId, estado: 'en_curso');
      expect(e.sync.status.value.pending, 1);
      expect(e.sync.status.value.conflicts, isEmpty);
    });
  });

  group('Conflictos: el servidor gana', () {
    test('si el panel completó la visita, el cambio del técnico se descarta y se avisa', () async {
      final e = Entorno();
      await e.prepararDia();
      e.remote.online = false;
      await e.client.updateVisita(visitaId, estado: 'en_curso');

      e.remote.visitas[visitaId] = visita(visitaId, estado: 'completada');
      e.remote.online = true;
      await e.sync.flush();

      expect(e.visitaServidor.estado, 'completada'); // no se pisó
      expect(e.sync.status.value.pending, 0);
      expect(e.sync.status.value.conflicts.single, contains('iniciar la visita'));
      expect(e.sync.status.value.conflicts.single, contains('completada'));
      // La copia local se descartó: la próxima lectura trae lo del servidor.
      expect((await e.client.fetchVisita(visitaId)).estado, 'completada');
    });

    test('si el panel canceló la visita, también se descarta', () async {
      final e = Entorno();
      await e.prepararDia();
      e.remote.online = false;
      await e.client.updateVisita(visitaId, notas: 'Observación');
      e.remote.visitas[visitaId] = visita(visitaId, estado: 'cancelada');
      e.remote.online = true;
      await e.sync.flush();
      expect(e.visitaServidor.notas, isNull);
      expect(e.sync.status.value.conflicts.single, contains('cancelada'));
    });

    test('si la visita ya estaba en ese estado no hay conflicto ni se repite el envío', () async {
      final e = Entorno();
      await e.prepararDia();
      e.remote.online = false;
      await e.client.updateVisita(visitaId, estado: 'en_curso');
      e.remote.visitas[visitaId] = visita(visitaId, estado: 'en_curso');
      e.remote.online = true;
      e.remote.calls.clear();
      await e.sync.flush();
      expect(e.sync.status.value.conflicts, isEmpty);
      expect(e.remote.calls.where((c) => c.startsWith('updateVisita')), isEmpty);
    });

    test('un cambio rechazado por el servidor (403) se descarta y se informa', () async {
      final e = Entorno();
      await e.prepararDia();
      e.remote.online = false;
      await e.client.updateDispositivo(trampaId, 'confirmar');
      e.remote.croquisPorVisita.clear(); // la trampa ya no existe en el servidor
      e.remote.online = true;
      await e.sync.flush();
      expect(e.sync.status.value.pending, 0);
      expect(e.sync.status.value.conflicts.single, contains('confirmar una trampa'));
    });

    test('el aviso de conflictos se puede cerrar', () async {
      final e = Entorno();
      await e.prepararDia();
      e.remote.online = false;
      await e.client.updateVisita(visitaId, estado: 'en_curso');
      e.remote.visitas[visitaId] = visita(visitaId, estado: 'cancelada');
      e.remote.online = true;
      await e.sync.flush();
      expect(e.sync.status.value.visible, isTrue);
      e.sync.dismissConflicts();
      expect(e.sync.status.value.conflicts, isEmpty);
    });
  });

  group('Trampas sin señal', () {
    test('confirmar, mover y retirar se ven al instante y se envían después', () async {
      final e = Entorno();
      await e.prepararDia();
      e.remote.online = false;

      final confirmada = await e.client.updateDispositivo(trampaId, 'confirmar');
      final movida = await e.client.updateDispositivo(trampaId, 'mover', lat: -33.5, lng: -70.6);
      final retirada = await e.client.updateDispositivo(trampaId, 'eliminar');

      expect(confirmada.confirmado, isTrue);
      expect((movida.lat, movida.lng), (-33.5, -70.6));
      expect(retirada.estado, 'retirado');
      final local = await e.client.fetchCroquis(visitaId);
      expect(local.dispositivos.single.estado, 'retirado');
      expect(e.sync.status.value.pending, 3);

      e.remote.online = true;
      await e.sync.flush();
      final servidor = e.croquisServidor.dispositivos.single;
      expect((servidor.confirmado, servidor.lat, servidor.estado), (true, -33.5, 'retirado'));
      expect(e.sync.status.value.pending, 0);
    });

    test('una trampa nueva sin señal queda provisoria y toma su código al sincronizar', () async {
      final e = Entorno();
      await e.prepararDia();
      e.remote.online = false;

      final nueva = await e.client.addDispositivo(visitaId, tipo: 'cebadero', lat: -33.49, lng: -70.6);

      expect(nueva.codigo, 'Trampa nueva');
      expect(nueva.confirmado, isTrue);
      expect(e.croquisServidor.dispositivos.length, 1);
      expect((await e.client.fetchCroquis(visitaId)).dispositivos.length, 2);

      e.remote.online = true;
      await e.sync.flush();

      expect(e.croquisServidor.dispositivos.length, 2);
      final real = e.croquisServidor.dispositivos.last;
      expect(real.id, nueva.id); // mismo id: no se duplica ni se pierde la relación
      expect(real.codigo, 'T-02');
      final local = await e.client.fetchCroquis(visitaId);
      expect(local.dispositivos.map((d) => d.codigo), ['T-01', 'T-02']);
    });

    test('reintentar el envío de una trampa nueva no la duplica', () async {
      final e = Entorno();
      await e.prepararDia();
      e.remote.online = false;
      final nueva = await e.client.addDispositivo(visitaId, tipo: 'cebadero', lat: -33.49, lng: -70.6);

      // El servidor la recibe pero la respuesta se pierde: la app cree que falló.
      e.remote.online = true;
      await e.remote.addDispositivo(visitaId, id: nueva.id, tipo: 'cebadero', lat: -33.49, lng: -70.6);
      await e.sync.flush();

      expect(e.croquisServidor.dispositivos.where((d) => d.id == nueva.id).length, 1);
      expect(e.sync.status.value.pending, 0);
    });

    test('los ids de las trampas nuevas son UUID v4 distintos', () {
      final a = nuevoUuid();
      final b = nuevoUuid();
      final formato = RegExp(r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$');
      expect(a, matches(formato));
      expect(b, matches(formato));
      expect(a, isNot(b));
    });

    test('si la visita se cerró mientras tanto, agregar la trampa falla con aviso claro', () async {
      final e = Entorno();
      await e.prepararDia();
      e.remote.failWithStatus = null;
      e.remote.visitas[visitaId] = visita(visitaId, estado: 'completada');
      e.remote.croquisPorVisita.clear(); // el servidor rechaza con 404/409
      await expectLater(
        e.client.addDispositivo(visitaId, tipo: 'cebadero', lat: -33.49, lng: -70.6),
        throwsA(isA<ApiException>()),
      );
      expect(e.sync.status.value.pending, 0);
      expect(e.sync.status.value.conflicts.single, contains('agregar una trampa'));
    });
  });

  group('Fotos sin señal', () {
    test('la foto queda en cola con su propia copia y se sube al volver', () async {
      final e = Entorno();
      await e.prepararDia();
      e.remote.online = false;

      final trampa = await e.client.uploadFoto(trampaId, '/tmp/captura.jpg');

      expect(trampa.fotoUrl, isNull);
      expect(e.outbox.guardadas.single, startsWith('/outbox/'));
      expect(e.sync.status.value.pending, 1);

      e.remote.online = true;
      await e.sync.flush();

      expect(e.croquisServidor.dispositivos.single.fotoUrl, isNotNull);
      expect(e.outbox.guardadas, isEmpty); // la copia se borró al subirse
      expect((await e.client.fetchCroquis(visitaId)).dispositivos.single.fotoUrl, isNotNull);
    });

    test('la foto de una trampa nueva espera a que la trampa exista', () async {
      final e = Entorno();
      await e.prepararDia();
      e.remote.online = false;
      final nueva = await e.client.addDispositivo(visitaId, tipo: 'cebadero', lat: -33.49, lng: -70.6);
      await e.client.uploadFoto(nueva.id, '/tmp/nueva.jpg');
      expect(e.sync.status.value.pending, 2);

      e.remote.online = true;
      e.remote.calls.clear();
      await e.sync.flush();

      expect(
        e.remote.calls.where((c) => c.startsWith('addDispositivo') || c.startsWith('uploadFoto')),
        ['addDispositivo:${nueva.id}', 'uploadFoto:/outbox/copia_0.jpg'],
      );
      expect(e.croquisServidor.dispositivos.last.fotoUrl, isNotNull);
    });

    test('si la copia de la foto ya no existe, el cambio se descarta con aviso', () async {
      final e = Entorno();
      await e.prepararDia();
      e.remote.online = false;
      await e.client.uploadFoto(trampaId, '/tmp/captura.jpg');
      e.outbox.guardadas.clear(); // el sistema borró el archivo
      e.remote.online = true;
      await e.sync.flush();
      expect(e.sync.status.value.pending, 0);
      expect(e.sync.status.value.conflicts.single, contains('subir una foto'));
    });
  });

  group('Cuentas separadas', () {
    test('otro técnico en el mismo teléfono no ve ni envía los cambios del anterior', () async {
      final e = Entorno();
      await e.prepararDia();
      e.remote.online = false;
      await e.client.updateVisita(visitaId, estado: 'en_curso');

      e.owner = 'tecnico-2';
      e.remote.online = true;
      await e.sync.flush();
      expect(e.visitaServidor.estado, 'agendada'); // no se envió con la cuenta equivocada
      expect(await e.sync.pendingCount(), 0);

      e.remote.online = false;
      await expectLater(e.client.fetchVisitasHoy(), throwsA(isA<SocketException>())); // sin copia ajena

      e.owner = 'tecnico-1';
      e.remote.online = true;
      await e.sync.flush();
      expect(e.visitaServidor.estado, 'en_curso'); // al volver el dueño, sí se envía
    });

    test('sin sesión no se guarda nada y las escrituras van directo al servidor', () async {
      final e = Entorno();
      e.owner = null;
      final visita = await e.client.updateVisita(visitaId, estado: 'en_curso');
      expect(visita.estado, 'en_curso');
      expect(e.sync.status.value.pending, 0);
    });
  });

  group('Si falla el almacenamiento del teléfono', () {
    test('la app sigue funcionando como antes, sin modo offline', () async {
      final e = Entorno();
      final sync = SyncService(
        store: _StoreRoto(),
        remote: e.remote,
        ownerProvider: () async => 'tecnico-1',
        files: e.outbox,
      );
      final client = OfflineApiClient(sync: sync, files: e.outbox);

      expect((await client.fetchVisitasHoy()).length, 1);
      expect((await client.updateVisita(visitaId, estado: 'en_curso')).estado, 'en_curso');
      expect(e.visitaServidor.estado, 'en_curso');
    });
  });

  group('Estado para la franja de conexión', () {
    test('no se ve cuando todo está en orden y se ve con cambios pendientes', () async {
      final e = Entorno();
      await e.prepararDia();
      expect(e.sync.status.value.visible, isFalse);
      e.remote.online = false;
      await e.client.updateVisita(visitaId, estado: 'en_curso');
      expect(e.sync.status.value.visible, isTrue);
      expect(e.sync.status.value.offline, isTrue);
      expect(e.sync.status.value.pending, 1);
    });

    test('el ciclo automático envía lo pendiente al volver la señal', () async {
      final e = Entorno();
      await e.prepararDia();
      e.remote.online = false;
      await e.client.updateVisita(visitaId, estado: 'en_curso');
      e.remote.online = true;
      await e.sync.tick();
      expect(e.visitaServidor.estado, 'en_curso');
      expect(e.sync.status.value.pending, 0);
      expect(e.sync.status.value.offline, isFalse);
    });

    test('el ciclo automático detecta que volvió la señal aunque no haya pendientes', () async {
      final e = Entorno();
      await e.prepararDia();
      e.remote.online = false;
      await e.client.fetchVisitasHoy();
      expect(e.sync.status.value.offline, isTrue);
      e.remote.online = true;
      await e.sync.tick();
      expect(e.sync.status.value.offline, isFalse);
    });
  });
}

/// Almacén que siempre falla (disco lleno, plugin ausente...).
class _StoreRoto implements LocalStore {
  Never _falla() => throw StateError('almacenamiento no disponible');

  @override
  Future<void> putCache(String owner, String key, String json) async => _falla();
  @override
  Future<String?> getCache(String owner, String key) async => _falla();
  @override
  Future<void> deleteCache(String owner, String key) async => _falla();
  @override
  Future<int> enqueue(PendingOp op) async => _falla();
  @override
  Future<List<PendingOp>> pending(String owner) async => _falla();
  @override
  Future<int> pendingCount(String owner) async => _falla();
  @override
  Future<void> removeOp(int id) async => _falla();
  @override
  Future<void> markAttempt(int id, String? error) async => _falla();
}
