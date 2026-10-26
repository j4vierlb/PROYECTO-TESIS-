import 'package:app_movil/services/pending_photo_files.dart';
import 'package:image_picker/image_picker.dart';

/// Los tests de flujo no simulan el disco; los de persistencia usan archivos reales.
class FakePendingPhotoFiles extends PendingPhotoFiles {
  const FakePendingPhotoFiles();

  @override
  Future<String> persist(XFile source) async => source.path;

  @override
  Future<void> remove(String path) async {}
}
