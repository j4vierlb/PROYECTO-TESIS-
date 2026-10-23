import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:image_picker/image_picker.dart';

class PendingPhoto {
  final String visitId;
  final String deviceId;
  final String? path;
  final String? ownerId;
  const PendingPhoto(this.visitId, this.deviceId, [this.path, this.ownerId]);

  Map<String, dynamic> toJson() => {
    'visitId': visitId,
    'deviceId': deviceId,
    'path': path,
    'ownerId': ownerId,
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
        data['ownerId'] as String?,
      );
    } catch (_) {
      await clear();
      return null;
    }
  }

  Future<void> _save(PendingPhoto photo) =>
      storage.write(key: storageKey, value: jsonEncode(photo.toJson()));
  Future<void> clear() => storage.delete(key: storageKey);

  // El sub solo separa archivos locales entre cuentas. La autorización real
  // sigue siendo responsabilidad del backend; nunca se guarda el JWT aquí.
  String? _subject(String? token) {
    if (token == null) return null;
    try {
      final parts = token.split('.');
      if (parts.length != 3) return null;
      final claims = jsonDecode(
        utf8.decode(base64Url.decode(base64Url.normalize(parts[1]))),
      );
      final subject = claims['sub'];
      return subject is String && subject.isNotEmpty ? subject : null;
    } catch (_) {
      return null;
    }
  }

  Future<void> bindLegacyOwner(String? previousToken) async {
    final photo = await read();
    final owner = _subject(previousToken);
    if (photo != null && photo.ownerId == null && owner != null) {
      await _save(
        PendingPhoto(photo.visitId, photo.deviceId, photo.path, owner),
      );
    }
  }

  Future<PendingPhoto?> readForCurrentAccount() async {
    final photo = await read();
    final owner = _subject(await storage.read(key: 'access_token'));
    return owner != null && photo?.ownerId == owner ? photo : null;
  }

  Future<PendingPhoto?> capture(
    String visitId,
    String deviceId,
    ImageSource source,
  ) async {
    if (await read() != null) {
      throw StateError('Reintenta o descarta primero la foto pendiente');
    }
    final owner = _subject(await storage.read(key: 'access_token'));
    if (owner == null) {
      throw StateError('Vuelve a iniciar sesión antes de capturar');
    }
    // Se registra el destino ANTES de salir hacia cámara/galería.
    await _save(PendingPhoto(visitId, deviceId, null, owner));
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
    final pending = PendingPhoto(visitId, deviceId, photo.path, owner);
    await _save(pending);
    return pending;
  }

  /// Android puede destruir MainActivity al usar la cámara con poca RAM.
  /// La foto recuperada se conserva para revisión/reintento, no se reasigna.
  Future<void> recoverInterruptedCapture() async {
    await bindLegacyOwner(
      await storage.read(key: 'access_token') ??
          await storage.read(key: 'refresh_token'),
    );
    final lost = await recover();
    final pending = await read();
    if (pending == null) return; // nunca adjuntar a una trampa desconocida
    final files = lost.files;
    if (files != null && files.isNotEmpty) {
      await _save(
        PendingPhoto(
          pending.visitId,
          pending.deviceId,
          files.first.path,
          pending.ownerId,
        ),
      );
    } else if (pending.path == null) {
      await clear(); // selección cancelada o sin archivo recuperable
    }
  }
}
