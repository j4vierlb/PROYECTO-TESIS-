// =============================================================================
// offline/sqlite_local_store.dart — LocalStore guardado en SQLite
// =============================================================================

import 'package:sqflite/sqflite.dart';

import '../db/local_database.dart';
import 'local_store.dart';

// Implementación REAL de LocalStore: guarda todo en una base SQLite dentro del
// teléfono (paquete sqflite). Usa dos tablas:
//   - 'cache'  = la última copia de lo que se vio con señal.
//   - 'outbox' = la cola de cambios hechos sin señal, pendientes de enviar.
// Las pruebas usan otra implementación en memoria, por eso existe LocalStore.
class SqliteLocalStore implements LocalStore {
  final LocalDatabase _database;

  SqliteLocalStore([LocalDatabase? database]) : _database = database ?? LocalDatabase.instance;

  // Guarda la copia de un dato. 'replace' significa que si ya había una con la
  // misma llave (owner + key) se pisa, en vez de dar error por duplicado.
  @override
  Future<void> putCache(String owner, String key, String json) async {
    final db = await _database.database;
    await db.insert(
      'cache',
      {'owner': owner, 'key': key, 'json': json, 'updated_at': DateTime.now().toUtc().toIso8601String()},
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  // Devuelve el JSON guardado, o null si no hay copia. Los '?' con whereArgs
  // evitan la inyección SQL: los valores nunca se pegan al texto de la consulta.
  @override
  Future<String?> getCache(String owner, String key) async {
    final db = await _database.database;
    final rows = await db.query(
      'cache',
      columns: ['json'],
      where: 'owner = ? AND key = ?',
      whereArgs: [owner, key],
      limit: 1,
    );
    return rows.isEmpty ? null : rows.first['json'] as String;
  }

  @override
  Future<void> deleteCache(String owner, String key) async {
    final db = await _database.database;
    await db.delete('cache', where: 'owner = ? AND key = ?', whereArgs: [owner, key]);
  }

  // Agrega un cambio a la cola (tabla outbox) con su fecha y su contador de
  // intentos en cero.
  @override
  Future<int> enqueue(PendingOp op) async {
    final db = await _database.database;
    return db.insert('outbox', {
      'owner': op.owner,
      'kind': op.kind,
      'visit_id': op.visitId,
      'payload': encodePayload(op.payload),
      'created_at': op.createdAt.toUtc().toIso8601String(),
      'attempts': op.attempts,
      'last_error': op.lastError,
    });
  }

  // Lee la cola del técnico en orden de llegada (id ascendente): los cambios
  // se envían en el mismo orden en que se hicieron.
  @override
  Future<List<PendingOp>> pending(String owner) async {
    final db = await _database.database;
    final rows = await db.query('outbox', where: 'owner = ?', whereArgs: [owner], orderBy: 'id ASC');
    return [
      for (final row in rows)
        PendingOp(
          id: row['id'] as int,
          owner: row['owner'] as String,
          kind: row['kind'] as String,
          visitId: row['visit_id'] as String,
          payload: decodePayload(row['payload'] as String),
          createdAt: DateTime.parse(row['created_at'] as String),
          attempts: row['attempts'] as int,
          lastError: row['last_error'] as String?,
        ),
    ];
  }

  // Cuenta cuántos cambios esperan. Es el número que muestra la franja
  // 'Sin conexión' de arriba.
  @override
  Future<int> pendingCount(String owner) async {
    final db = await _database.database;
    final result = await db.rawQuery('SELECT COUNT(*) AS n FROM outbox WHERE owner = ?', [owner]);
    return Sqflite.firstIntValue(result) ?? 0;
  }

  // Quita un cambio de la cola (porque ya se envió o se descartó por conflicto).
  @override
  Future<void> removeOp(int id) async {
    final db = await _database.database;
    await db.delete('outbox', where: 'id = ?', whereArgs: [id]);
  }

  // Suma un intento fallido y guarda el último error, para saber por qué no
  // se ha podido enviar.
  @override
  Future<void> markAttempt(int id, String? error) async {
    final db = await _database.database;
    await db.rawUpdate('UPDATE outbox SET attempts = attempts + 1, last_error = ? WHERE id = ?', [error, id]);
  }
}
