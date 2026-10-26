import 'dart:io';
import 'dart:math';

import 'package:image_picker/image_picker.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

/// Copias privadas del envío pendiente, fuera de la caché de image_picker.
class PendingPhotoFiles {
  static const folder = 'pending_field_photos';
  final Future<Directory> Function() documentsDirectory;

  const PendingPhotoFiles({
    this.documentsDirectory = getApplicationDocumentsDirectory,
  });

  Future<Directory> _directory() async =>
      Directory(p.join((await documentsDirectory()).path, folder));

  Future<String> persist(XFile source) async {
    final directory = await _directory();
    await directory.create(recursive: true);
    if (!await File(source.path).exists()) {
      throw const FileSystemException('La captura ya no está disponible');
    }
    if (p.equals(
      p.dirname(p.absolute(source.path)),
      p.absolute(directory.path),
    )) {
      return source.path;
    }
    final extension = p.extension(source.path).toLowerCase() == '.png'
        ? '.png'
        : '.jpg';
    final name =
        '${DateTime.now().microsecondsSinceEpoch}_'
        '${Random.secure().nextInt(1 << 32)}$extension';
    final target = File(p.join(directory.path, name));
    try {
      await source.saveTo(target.path);
      return target.path;
    } catch (_) {
      if (await target.exists()) await target.delete();
      rethrow;
    }
  }

  /// Solo borra nuestra copia; nunca la galería ni una ruta externa.
  Future<void> remove(String path) async {
    if (p.basename(p.dirname(path)) != folder) return;
    final directory = await _directory();
    if (!p.equals(p.dirname(p.absolute(path)), p.absolute(directory.path))) {
      return;
    }
    final file = File(path);
    if (await file.exists()) await file.delete();
  }
}

class PendingPhotoStorageException implements Exception {
  const PendingPhotoStorageException();
  String get message =>
      'No se pudo conservar la foto fuera de la caché. '
      'Libera espacio y reintenta, o descarta el envío pendiente.';
}
