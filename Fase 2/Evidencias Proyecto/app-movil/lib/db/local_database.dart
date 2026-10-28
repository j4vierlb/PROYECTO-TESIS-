// =============================================================================
// db/local_database.dart — Base de datos local del teléfono (SQLite)
// -----------------------------------------------------------------------------
// Guarda lo necesario para trabajar sin señal en terreno:
//   - cache:  última copia de la agenda, las visitas y los croquis.
//   - outbox: cambios hechos sin señal, pendientes de enviar al backend.
// La lógica (qué se guarda y cuándo se envía) vive en lib/offline/.
// =============================================================================

import 'package:path/path.dart';
import 'package:sqflite/sqflite.dart';

/// Base de datos local (SQLite) para poder trabajar sin conexión en terreno.
class LocalDatabase {
  // Patrón "singleton": existe una sola instancia en toda la app, accesible
  // como LocalDatabase.instance. El constructor privado impide crear otras.
  LocalDatabase._([this._pathOverride]);
  static final LocalDatabase instance = LocalDatabase._();

  /// Base en otra ruta (las pruebas usan ':memory:'), sin tocar la de la app.
  factory LocalDatabase.forTesting(String path) => LocalDatabase._(path);

  final String? _pathOverride;

  static const String _dbName = 'kill_bichos.db';
  // v1 tenía una tabla "visitas" que nunca se usó. v2 la reemplaza por
  // cache + outbox.
  static const int _dbVersion = 2;

  Database? _db;

  /// Devuelve la base abierta. La primera vez la abre (o la crea); las
  /// siguientes reutiliza la misma conexión.
  Future<Database> get database async {
    _db ??= await _open();
    return _db!;
  }

  Future<Database> _open() async {
    // Carpeta donde el sistema operativo permite guardar bases de datos.
    final path = _pathOverride ?? join(await getDatabasesPath(), _dbName);
    return openDatabase(
      path,
      version: _dbVersion,
      // onCreate solo se ejecuta la primera vez, cuando el archivo no existe.
      onCreate: (db, version) => _createTables(db),
      onUpgrade: (db, oldVersion, newVersion) async {
        if (oldVersion < 2) {
          await db.execute('DROP TABLE IF EXISTS visitas');
          await _createTables(db);
        }
      },
    );
  }

  Future<void> _createTables(Database db) async {
    // Cada fila de cache es un JSON tal como lo entregó el backend. La clave
    // dice qué es ('visitas_hoy', 'visita:<id>', 'croquis:<id>'...) y el
    // dueño separa las cuentas que usan el mismo teléfono.
    await db.execute('''
      CREATE TABLE IF NOT EXISTS cache (
        owner TEXT NOT NULL,
        key TEXT NOT NULL,
        json TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        PRIMARY KEY (owner, key)
      )
    ''');
    // Cola de cambios hechos sin señal, en orden de creación (id autoincremental).
    await db.execute('''
      CREATE TABLE IF NOT EXISTS outbox (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        owner TEXT NOT NULL,
        kind TEXT NOT NULL,
        visit_id TEXT NOT NULL,
        payload TEXT NOT NULL,
        created_at TEXT NOT NULL,
        attempts INTEGER NOT NULL DEFAULT 0,
        last_error TEXT
      )
    ''');
    await db.execute('CREATE INDEX IF NOT EXISTS idx_outbox_owner ON outbox(owner, id)');
  }
}
