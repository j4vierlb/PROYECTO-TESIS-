// =============================================================================
// db/local_database.dart — Base de datos local del teléfono (SQLite)
// -----------------------------------------------------------------------------
// Pensada para el modo offline: que el técnico pueda seguir trabajando sin
// señal y que los cambios se sincronicen con el backend después.
// Todavía NO se usa en ninguna pantalla: es la base preparada.
// =============================================================================

import 'package:path/path.dart';
import 'package:sqflite/sqflite.dart';

/// Base de datos local (SQLite) para poder trabajar sin conexión en terreno.
///
/// Por ahora esto es solo el esqueleto: crea la tabla "visitas" con su
/// columna updated_at (para detectar qué registros cambiaron localmente y
/// deben subirse al backend). La lógica de sincronización real —bajar la
/// agenda al iniciar sesión, subir cambios hechos offline, resolver
/// conflictos— se implementa en un paso posterior.
class LocalDatabase {
  // Patrón "singleton": existe una sola instancia en toda la app, accesible
  // como LocalDatabase.instance. El constructor privado impide crear otras.
  LocalDatabase._();
  static final LocalDatabase instance = LocalDatabase._();

  static const String _dbName = 'kill_bichos.db';
  // Si en el futuro cambia la estructura de las tablas, se sube este número
  // y se agrega una migración (onUpgrade).
  static const int _dbVersion = 1;

  Database? _db;

  /// Devuelve la base abierta. La primera vez la abre (o la crea); las
  /// siguientes reutiliza la misma conexión.
  Future<Database> get database async {
    _db ??= await _open();
    return _db!;
  }

  Future<Database> _open() async {
    // Carpeta donde el sistema operativo permite guardar bases de datos.
    final dbPath = await getDatabasesPath();
    final path = join(dbPath, _dbName);
    return openDatabase(
      path,
      version: _dbVersion,
      // onCreate solo se ejecuta la primera vez, cuando el archivo no existe.
      onCreate: (db, version) async {
        await db.execute('''
          CREATE TABLE visitas (
            id TEXT PRIMARY KEY,
            cliente_nombre TEXT NOT NULL,
            direccion TEXT NOT NULL,
            lat REAL NOT NULL,
            lng REAL NOT NULL,
            fecha_hora TEXT NOT NULL,
            estado TEXT NOT NULL,
            notas TEXT,
            updated_at TEXT NOT NULL
          )
        ''');
      },
    );
  }
}
