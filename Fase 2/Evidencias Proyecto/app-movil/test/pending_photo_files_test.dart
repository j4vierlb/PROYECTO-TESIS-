import 'dart:convert';
import 'dart:io';

import 'package:app_movil/services/auth_storage.dart';
import 'package:app_movil/services/pending_photo.dart';
import 'package:app_movil/services/pending_photo_files.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:image_picker/image_picker.dart';
import 'package:path/path.dart' as p;

String accountToken(String owner) =>
    'header.${base64Url.encode(utf8.encode(jsonEncode({'sub': owner}))).replaceAll('=', '')}.signature';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late Directory sandbox;
  late Directory cache;
  late Directory documents;
  late File original;
  late PendingPhotoFiles files;

  setUp(() async {
    FlutterSecureStorage.setMockInitialValues({
      'access_token': accountToken('a'),
    });
    sandbox = await Directory.systemTemp.createTemp('pending_photo_qa_');
    cache = await Directory(p.join(sandbox.path, 'cache')).create();
    documents = await Directory(p.join(sandbox.path, 'documents')).create();
    original = await File(p.join(cache.path, 'camera.jpg'))
        .writeAsBytes([1, 2, 3, 4]);
    files = PendingPhotoFiles(documentsDirectory: () async => documents);
  });
  tearDown(() async => sandbox.delete(recursive: true));

  PendingPhotoStore store({Future<LostDataResponse> Function()? recover}) =>
      PendingPhotoStore(
        files: files,
        pick: (_) async => XFile(original.path),
        recover: recover,
      );

  Future<void> seed({String? path, String? owner = 'a'}) async {
    await const FlutterSecureStorage().write(
      key: PendingPhotoStore.storageKey,
      value: jsonEncode(PendingPhoto('v1', 'd1', path, owner).toJson()),
    );
  }

  test('Captura persiste fuera de caché y sobrevive borrado de original y reinicio', () async {
    final pending = (await store().capture('v1', 'd1', ImageSource.camera))!;
    expect(pending.path, isNot(original.path));
    expect(
      p.dirname(pending.path!),
      p.join(documents.path, PendingPhotoFiles.folder),
    );
    await original.delete();
    final reopened = await store().readForCurrentAccount();
    expect(reopened?.ownerId, 'a');
    expect(reopened?.visitId, 'v1');
    expect(reopened?.deviceId, 'd1');
    expect(await File(reopened!.path!).readAsBytes(), [1, 2, 3, 4]);
  });

  test('Galería PNG conserva extensión y archivo original', () async {
    original = await File(p.join(cache.path, 'gallery.png'))
        .writeAsBytes([5, 6]);
    final pending = (await store().capture('v1', 'd1', ImageSource.gallery))!;
    expect(p.extension(pending.path!), '.png');
    expect(await original.readAsBytes(), [5, 6]);
    expect(await File(pending.path!).readAsBytes(), [5, 6]);
  });

  test(
    'Reintentar no crea copias adicionales de la misma foto persistente',
    () async {
      final pending = await store().capture('v1', 'd1', ImageSource.camera);
      final again = await store().prepareForUpload();
      expect(again?.path, pending?.path);
      expect(await Directory(p.dirname(again!.path!)).list().length, 1);
    },
  );

  test('LostData se copia antes de exponer la ruta recuperada', () async {
    await seed();
    final photos = store(
      recover: () async => LostDataResponse(files: [XFile(original.path)]),
    );
    await photos.recoverInterruptedCapture();
    final pending = (await photos.read())!;
    expect(pending.ownerId, 'a');
    expect(pending.path, isNot(original.path));
    await original.delete();
    expect(await File(pending.path!).readAsBytes(), [1, 2, 3, 4]);
  });

  test(
    'Arranque migra ruta antigua sin cambiar propietario o destino',
    () async {
      await seed(path: original.path);
      final photos = store(recover: () async => LostDataResponse.empty());
      await photos.recoverInterruptedCapture();
      final pending = (await photos.read())!;
      expect(pending.ownerId, 'a');
      expect(pending.visitId, 'v1');
      expect(pending.deviceId, 'd1');
      await original.delete();
      expect(await File(pending.path!).readAsBytes(), [1, 2, 3, 4]);
    },
  );

  test(
    'LostData no sustituye un pendiente que ya tiene su propia foto',
    () async {
      final photos = store();
      final pending = await photos.capture('v1', 'd1', ImageSource.camera);
      final unrelated = await File(p.join(cache.path, 'other.jpg'))
          .writeAsBytes([9]);
      final recovering = store(
        recover: () async => LostDataResponse(files: [XFile(unrelated.path)]),
      );
      await recovering.recoverInterruptedCapture();
      expect((await photos.read())?.path, pending?.path);
      expect(await File(pending!.path!).readAsBytes(), [1, 2, 3, 4]);
    },
  );

  test('Descarte limpia copia privada, pero no el archivo original', () async {
    final photos = store();
    final pending = await photos.capture('v1', 'd1', ImageSource.camera);
    await photos.clear();
    expect(await photos.read(), isNull);
    expect(await File(pending!.path!).exists(), isFalse);
    expect(await original.exists(), isTrue);
  });

  test(
    'Descarte de metadatos antiguos no borra archivos de caché o galería',
    () async {
      await seed(path: original.path);
      await store().clear();
      expect(await original.exists(), isTrue);
    },
  );

  test(
    'Limpieza no borra una carpeta homónima fuera del directorio privado',
    () async {
      final elsewhere = await Directory(
        p.join(sandbox.path, PendingPhotoFiles.folder),
      ).create();
      final untouched = await File(p.join(elsewhere.path, 'photo.jpg'))
          .writeAsBytes([8]);
      await seed(path: untouched.path);
      await store().clear();
      expect(await untouched.readAsBytes(), [8]);
    },
  );

  test('Otra cuenta no prepara ni reasigna el archivo persistente', () async {
    final photos = store();
    final pending = await photos.capture('v1', 'd1', ImageSource.camera);
    await AuthStorage.instance.clear();
    await AuthStorage.instance.saveTokens(
      accessToken: accountToken('b'),
      refreshToken: 'refresh',
    );
    expect(await photos.prepareForUpload(), isNull);
    expect((await photos.read())?.ownerId, 'a');
    expect(await File(pending!.path!).exists(), isTrue);
    await photos.clear(); // Equivale al descarte confirmado de la pantalla.
    expect(await File(pending.path!).exists(), isFalse);
    expect(await original.exists(), isTrue);
  });

  test(
    'Fallo de copia conserva destino y permite volver a intentar persistir',
    () async {
      var unavailable = true;
      files = PendingPhotoFiles(
        documentsDirectory: () async {
          if (unavailable) throw const FileSystemException('sin espacio');
          return documents;
        },
      );
      final photos = store();
      await expectLater(
        photos.capture('v1', 'd1', ImageSource.camera),
        throwsA(isA<PendingPhotoStorageException>()),
      );
      expect((await photos.read())?.path, original.path);
      expect((await photos.read())?.ownerId, 'a');
      unavailable = false;
      final ready = await photos.prepareForUpload();
      expect(ready?.path, isNot(original.path));
      expect(await File(ready!.path!).readAsBytes(), [1, 2, 3, 4]);
    },
  );

  test(
    'Caché antigua ya eliminada muestra fallo y conserva opción de descarte',
    () async {
      await seed(path: original.path);
      await original.delete();
      await expectLater(
        store().prepareForUpload(),
        throwsA(isA<PendingPhotoStorageException>()),
      );
      expect((await store().read())?.deviceId, 'd1');
      await store().clear();
      expect(await store().read(), isNull);
    },
  );
}
