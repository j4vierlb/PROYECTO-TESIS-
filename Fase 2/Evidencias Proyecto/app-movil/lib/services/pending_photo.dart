import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:image_picker/image_picker.dart';

class PendingPhoto {
  final String visitId;
  final String deviceId;
  final String? path;
  const PendingPhoto(this.visitId, this.deviceId, [this.path]);

  Map<String, dynamic> toJson() => {
    'visitId': visitId,
    'deviceId': deviceId,
    'path': path,
  };
}

/// Un solo envío pendiente, asociado a la visita y trampa originales. No
/// contiene tokens y no envía automáticamente nada después de reiniciar.
class PendingPhotoStore {
  static const storageKey = 'pending_field_photo';
  static final instance = PendingPhotoStore();
  final FlutterSecureStorage storage;
  final Future<XFile?> Function(ImageSource) pick;
  final Future<LostDataResponse> Function() recover;

  PendingPhotoStore({
    this.storage = const FlutterSecureStorage(),
    Future<XFile?> Function(ImageSource)? pick,
    Future<LostDataResponse> Function()? recover,
  }) : pick =
           pick ??
           ((source) => ImagePicker().pickImage(
             source: source,
             maxWidth: 1600,
             imageQuality: 70,
           )),
       recover = recover ?? (() => ImagePicker().retrieveLostData());

  Future<PendingPhoto?> read() async {
    final value = await storage.read(key: storageKey);
    if (value == null) return null;
    try {
      final data = jsonDecode(value) as Map<String, dynamic>;
      return PendingPhoto(
        data['visitId'] as String,
        data['deviceId'] as String,
        data['path'] as String?,
      );
    } catch (_) {
      await clear();
      return null;
    }
  }

  Future<void> _save(PendingPhoto photo) =>
      storage.write(key: storageKey, value: jsonEncode(photo.toJson()));
  Future<void> clear() => storage.delete(key: storageKey);

  Future<PendingPhoto?> capture(
    String visitId,
    String deviceId,
    ImageSource source,
  ) async {
    if (await read() != null) {
      throw StateError('Reintenta o descarta primero la foto pendiente');
    }
    // Se registra el destino ANTES de salir hacia cámara/galería.
    await _save(PendingPhoto(visitId, deviceId));
    XFile? photo;
    try {
      photo = await pick(source);
    } catch (_) {
      await clear();
      rethrow;
    }
    if (photo == null) {
      await clear();
      return null;
    }
    final pending = PendingPhoto(visitId, deviceId, photo.path);
    await _save(pending);
    return pending;
  }

  /// Android puede destruir MainActivity al usar la cámara con poca RAM.
  /// La foto recuperada se conserva para revisión/reintento, no se reasigna.
  Future<void> recoverInterruptedCapture() async {
    final lost = await recover();
    final pending = await read();
    if (pending == null) return; // nunca adjuntar a una trampa desconocida
    final files = lost.files;
    if (files != null && files.isNotEmpty) {
      await _save(
        PendingPhoto(pending.visitId, pending.deviceId, files.first.path),
      );
    } else if (pending.path == null) {
      await clear(); // selección cancelada o sin archivo recuperable
    }
  }
}
