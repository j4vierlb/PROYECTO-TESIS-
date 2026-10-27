// =============================================================================
// offline/sqlite_local_store.dart — LocalStore guardado en SQLite
// =============================================================================

import 'package:sqflite/sqflite.dart';

import '../db/local_database.dart';
import 'local_store.dart';

class SqliteLocalStore implements LocalStore {
  final LocalDatabase _database;

  SqliteLocalStore([LocalDatabase? database]) : _database = database ?? LocalDatabase.instance;

  @override
  Future<void> putCache(String owner, String key, String json) async {
    final db = await _database.database;
    await db.insert(
      'cache',
      {'owner': owner, 'key': key, 'json': json, 'updated_at': DateTime.now().toUtc().toIso8601String()},
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

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

  @override
  Future<int> pendingCount(String owner) async {
    final db = await _database.database;
    final result = await db.rawQuery('SELECT COUNT(*) AS n FROM outbox WHERE owner = ?', [owner]);
    return Sqflite.firstIntValue(result) ?? 0;
  }

  @override
  Future<void> removeOp(int id) async {
    final db = await _database.database;
    await db.delete('outbox', where: 'id = ?', whereArgs: [id]);
  }

  @override
  Future<void> markAttempt(int id, String? error) async {
    final db = await _database.database;
    await db.rawUpdate('UPDATE outbox SET attempts = attempts + 1, last_error = ? WHERE id = ?', [error, id]);
  }
}
