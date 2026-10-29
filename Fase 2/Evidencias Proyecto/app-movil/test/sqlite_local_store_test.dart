// Pruebas del almacén SQLite real (no el de memoria): esquema, consultas,
// orden de la cola y migración desde la versión 1 de la base.

import 'dart:io';

import 'package:app_movil/db/local_database.dart';
import 'package:app_movil/offline/local_store.dart';
import 'package:app_movil/offline/sqlite_local_store.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:path/path.dart' as p;
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

PendingOp op(String owner, String kind, {String visitId = 'v-1', Map<String, dynamic>? payload}) => PendingOp(
      owner: owner,
      kind: kind,
      visitId: visitId,
      payload: payload ?? {'estado': 'en_curso'},
      createdAt: DateTime.utc(2026, 10, 27, 12),
    );

void main() {
  setUpAll(() {
    sqfliteFfiInit();
    databaseFactory = databaseFactoryFfi;
  });

  late SqliteLocalStore store;
  late Directory carpeta;
  late String ruta;

  // Cada prueba usa su propio archivo: SQLite en memoria comparte la base
  // entre pruebas y se contaminaría.
  setUp(() {
    carpeta = Directory.systemTemp.createTempSync('kb_sqlite_test');
    ruta = p.join(carpeta.path, 'prueba.db');
    store = SqliteLocalStore(LocalDatabase.forTesting(ruta));
  });

  tearDown(() async {
    // El factory reutiliza la conexión abierta de esta ruta. Cerrar primero:
    // Windows impide borrar un archivo SQLite que todavía tiene un handle.
    final db = await databaseFactory.openDatabase(ruta);
    await db.close();
    final tempRoot = Directory.systemTemp.resolveSymbolicLinksSync();
    final target = carpeta.resolveSymbolicLinksSync();
    if (!p.isWithin(tempRoot, target) || !p.basename(target).startsWith('kb_sqlite_test')) {
      throw StateError('La limpieza solo admite el directorio temporal de esta prueba');
    }
    await carpeta.delete(recursive: true);
  });

  test('guarda y lee la cache por cuenta; reemplazar pisa el valor anterior', () async {
    await store.putCache('a', 'visitas_hoy', '[1]');
    await store.putCache('b', 'visitas_hoy', '[2]');
    expect(await store.getCache('a', 'visitas_hoy'), '[1]');
    expect(await store.getCache('b', 'visitas_hoy'), '[2]');
    await store.putCache('a', 'visitas_hoy', '[3]');
    expect(await store.getCache('a', 'visitas_hoy'), '[3]');
    expect(await store.getCache('a', 'no-existe'), isNull);
    await store.deleteCache('a', 'visitas_hoy');
    expect(await store.getCache('a', 'visitas_hoy'), isNull);
    expect(await store.getCache('b', 'visitas_hoy'), '[2]');
  });

  test('la cola conserva el orden de creación y separa cuentas', () async {
    final primero = await store.enqueue(op('a', OpKind.visitaUpdate));
    await store.enqueue(op('b', OpKind.visitaUpdate));
    final tercero = await store.enqueue(op('a', OpKind.dispositivoUpdate, payload: {'id': 't', 'accion': 'mover', 'lat': -33.5, 'lng': -70.6}));

    final deA = await store.pending('a');
    expect(deA.map((o) => o.id), [primero, tercero]);
    expect(deA.last.kind, OpKind.dispositivoUpdate);
    expect(deA.last.payload['lat'], -33.5);
    expect(deA.first.createdAt, DateTime.utc(2026, 10, 27, 12));
    expect(await store.pendingCount('a'), 2);
    expect(await store.pendingCount('b'), 1);
    expect(await store.pendingCount('c'), 0);
  });

  test('quitar un cambio y registrar intentos fallidos', () async {
    final id = await store.enqueue(op('a', OpKind.visitaUpdate));
    await store.markAttempt(id, 'Sin señal');
    await store.markAttempt(id, 'Error 503');
    final guardado = (await store.pending('a')).single;
    expect(guardado.attempts, 2);
    expect(guardado.lastError, 'Error 503');
    await store.removeOp(id);
    expect(await store.pendingCount('a'), 0);
  });

  test('guarda cambios con texto largo y caracteres especiales sin perderlos', () async {
    final notas = 'Ñandú "bodega" ✓ \n línea 2 — ${'x' * 5000}';
    await store.enqueue(op('a', OpKind.visitaUpdate, payload: {'notas': notas}));
    expect((await store.pending('a')).single.payload['notas'], notas);
  });

  test('migra una base de la versión 1 (tabla visitas sin uso) y queda funcionando', () async {
    // Base v1 como la dejaba la versión anterior de la app.
    final v1 = await databaseFactory.openDatabase(
      ruta,
      options: OpenDatabaseOptions(
        version: 1,
        onCreate: (db, _) async {
          await db.execute('CREATE TABLE visitas (id TEXT PRIMARY KEY, updated_at TEXT NOT NULL)');
          await db.insert('visitas', {'id': 'vieja', 'updated_at': 'x'});
        },
      ),
    );
    await v1.close();

    // Al abrirla con el código nuevo se migra a la versión 2.
    await store.putCache('a', 'k', 'v');
    expect(await store.getCache('a', 'k'), 'v');
    await store.enqueue(op('a', OpKind.visitaUpdate));
    expect(await store.pendingCount('a'), 1);

    final db = await databaseFactory.openDatabase(ruta, options: OpenDatabaseOptions(readOnly: true));
    final tablas = (await db.rawQuery("SELECT name FROM sqlite_master WHERE type='table'")).map((t) => t['name']);
    await db.close();
    expect(tablas, containsAll(['cache', 'outbox']));
    expect(tablas, isNot(contains('visitas')));
  });

  test('los datos sobreviven al cerrar y volver a abrir la base', () async {
    await store.putCache('a', 'k', 'persistente');
    await store.enqueue(op('a', OpKind.foto, payload: {'deviceId': 't', 'path': '/outbox/1.jpg'}));
    // Probar persistencia real: no reutilizar la misma conexión abierta.
    final firstConnection = await databaseFactory.openDatabase(ruta);
    await firstConnection.close();
    final otraSesion = SqliteLocalStore(LocalDatabase.forTesting(ruta));
    expect(await otraSesion.getCache('a', 'k'), 'persistente');
    expect((await otraSesion.pending('a')).single.payload['path'], '/outbox/1.jpg');
  });
}
