// =============================================================================
// offline/outbox_files.dart — Fotos que esperan en la cola de envío
// -----------------------------------------------------------------------------
// Cuando una foto no se puede subir por falta de señal, se guarda una copia en
// una carpeta propia de la app. Esa copia es independiente de la del flujo de
// captura (pending_photo_files.dart): se borra solo cuando la foto se subió o
// el cambio se descartó.
// =============================================================================

import 'dart:io';
import 'dart:math';

import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

class OutboxFiles {
  static const folder = 'offline_outbox';
  final Future<Directory> Function() documentsDirectory;

  const OutboxFiles({this.documentsDirectory = getApplicationDocumentsDirectory});

  Future<Directory> _directory() async =>
      Directory(p.join((await documentsDirectory()).path, folder));

  /// Copia el archivo a la carpeta de la cola y devuelve la ruta de la copia.
  Future<String> keep(String sourcePath) async {
    final directory = await _directory();
    await directory.create(recursive: true);
    final source = File(sourcePath);
    if (!await source.exists()) {
      throw const FileSystemException('La foto ya no está disponible');
    }
    final extension = p.extension(sourcePath).toLowerCase() == '.png' ? '.png' : '.jpg';
    final name = '${DateTime.now().microsecondsSinceEpoch}_${Random.secure().nextInt(1 << 32)}$extension';
    final target = File(p.join(directory.path, name));
    await source.copy(target.path);
    return target.path;
  }

  Future<bool> exists(String path) => File(path).exists();

  /// Solo borra copias de esta carpeta; nunca la galería ni otra ruta.
  Future<void> remove(String path) async {
    try {
      if (p.basename(p.dirname(path)) != folder) return;
      final file = File(path);
      if (await file.exists()) await file.delete();
    } catch (_) {
      // Un fallo de limpieza no debe frenar la sincronización.
    }
  }
}
