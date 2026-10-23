import 'dart:convert';

import 'package:app_movil/services/auth_storage.dart';
import 'package:app_movil/services/pending_photo.dart';
import 'package:app_movil/services/session.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:image_picker/image_picker.dart';

String ownerToken(String owner) => 'header.${base64Url.encode(utf8.encode(jsonEncode({'sub': owner}))).replaceAll('=', '')}.signature';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUp(() => FlutterSecureStorage.setMockInitialValues({'access_token': ownerToken('owner-a')}));
  test(
    'Antes de abrir camara se registra visita y trampa, no otro destino',
    () async {
      late PendingPhotoStore store;
      store = PendingPhotoStore(
        pick: (_) async {
          final pending = await store.read();
          expect(pending?.visitId, 'v1');
          expect(pending?.deviceId, 'd1');
          expect(pending?.path, isNull);
          return XFile('/cache/camera.jpg');
        },
      );
      await store.capture('v1', 'd1', ImageSource.camera);
      expect((await store.read())?.path, '/cache/camera.jpg');
    },
  );
  test('Cancelar galeria no deja foto pendiente', () async {
    final store = PendingPhotoStore(pick: (_) async => null);
    expect(await store.capture('v1', 'd1', ImageSource.gallery), isNull);
    expect(await store.read(), isNull);
  });
  test('Error de permisos de camara limpia seleccion sin archivo', () async {
    final store = PendingPhotoStore(
      pick: (_) => throw StateError('permission denied'),
    );
    await expectLater(
      store.capture('v1', 'd1', ImageSource.camera),
      throwsStateError,
    );
    expect(await store.read(), isNull);
  });
  test(
    'Foto no enviada persiste entre instancias sin cambiar el destino',
    () async {
      await PendingPhotoStore(pick: (_) async => XFile('/cache/photo.png'))
          .capture('v1', 'd1', ImageSource.gallery);
      final reopened = await PendingPhotoStore().read();
      expect(reopened?.path, '/cache/photo.png');
      expect(reopened?.deviceId, 'd1');
    },
  );
  test(
    'Una segunda captura no sobreescribe silenciosamente la pendiente',
    () async {
      final store = PendingPhotoStore(pick: (_) async => XFile('/cache/a.jpg'));
      await store.capture('v1', 'd1', ImageSource.camera);
      await expectLater(
        store.capture('v2', 'd2', ImageSource.camera),
        throwsStateError,
      );
      expect((await store.read())?.deviceId, 'd1');
    },
  );
  test(
    'Recupera lostData de Android y mantiene visita y trampa originales',
    () async {
      FlutterSecureStorage.setMockInitialValues({
        PendingPhotoStore.storageKey: jsonEncode({
          'visitId': 'v1',
          'deviceId': 'd1',
          'path': null,
        }),
      });
      final store = PendingPhotoStore(
        recover: () async =>
            LostDataResponse(files: [XFile('/cache/recovered.jpg')]),
      );
      await store.recoverInterruptedCapture();
      final recovered = await store.read();
      expect(recovered?.path, '/cache/recovered.jpg');
      expect(recovered?.visitId, 'v1');
      expect(recovered?.deviceId, 'd1');
    },
  );
  test('LostData sin destino conocido no se adjunta a otra trampa', () async {
    final store = PendingPhotoStore(
      recover: () async =>
          LostDataResponse(files: [XFile('/cache/orphan.jpg')]),
    );
    await store.recoverInterruptedCapture();
    expect(await store.read(), isNull);
  });
  test('Logout elimina pendiente de la sesion anterior', () async {
    final store = PendingPhotoStore(pick: (_) async => XFile('/cache/a.jpg'));
    await store.capture('v1', 'd1', ImageSource.camera);
    await AuthStorage.instance.clear(manualLogout: true);
    expect(await store.read(), isNull);
  });
  test('Metadatos corruptos se descartan sin impedir abrir la app', () async {
    FlutterSecureStorage.setMockInitialValues({
      PendingPhotoStore.storageKey: 'invalid',
    });
    expect(await PendingPhotoStore().read(), isNull);
  });
  test('Vencimiento borra tokens, no la foto ni su cuenta original', () async {
    final store = PendingPhotoStore(pick: (_) async => XFile('/cache/a.jpg'));
    await store.capture('v1', 'd1', ImageSource.camera);
    await AuthStorage.instance.clear();
    expect(await AuthStorage.instance.getAccessToken(), isNull);
    expect((await store.read())?.path, '/cache/a.jpg');
    expect((await store.read())?.ownerId, 'owner-a');
    expect(await store.readForCurrentAccount(), isNull);
    await AuthStorage.instance.saveTokens(accessToken: ownerToken('owner-a'), refreshToken: 'refresh');
    expect((await store.readForCurrentAccount())?.deviceId, 'd1');
  });
  test('Otra cuenta no puede ver ni reasignar el envio pendiente', () async {
    final store = PendingPhotoStore(pick: (_) async => XFile('/cache/a.jpg'));
    await store.capture('v1', 'd1', ImageSource.camera);
    await AuthStorage.instance.clear();
    await AuthStorage.instance.saveTokens(accessToken: ownerToken('owner-b'), refreshToken: 'refresh');
    expect(await store.readForCurrentAccount(), isNull);
    expect((await store.read())?.ownerId, 'owner-a');
    await expectLater(store.capture('v2', 'd2', ImageSource.camera), throwsStateError);
  });
  test('Pendiente de version anterior conserva el propietario al vencer', () async {
    FlutterSecureStorage.setMockInitialValues({
      'access_token': ownerToken('owner-a'),
      PendingPhotoStore.storageKey: jsonEncode({'visitId': 'v1', 'deviceId': 'd1', 'path': '/cache/legacy.jpg'}),
    });
    await AuthStorage.instance.clear();
    expect((await PendingPhotoStore().read())?.ownerId, 'owner-a');
    await AuthStorage.instance.saveTokens(accessToken: ownerToken('owner-b'), refreshToken: 'refresh');
    expect(await PendingPhotoStore().readForCurrentAccount(), isNull);
  });
  test('Sin token anterior no adjudica una foto antigua a la cuenta nueva', () async {
    FlutterSecureStorage.setMockInitialValues({
      PendingPhotoStore.storageKey: jsonEncode({'visitId': 'v1', 'deviceId': 'd1', 'path': '/cache/legacy.jpg'}),
    });
    await AuthStorage.instance.saveTokens(accessToken: ownerToken('owner-b'), refreshToken: 'refresh');
    expect(await PendingPhotoStore().readForCurrentAccount(), isNull);
    expect((await PendingPhotoStore().read())?.path, '/cache/legacy.jpg');
  });
  test('No inicia una captura sin identidad de sesion', () async {
    FlutterSecureStorage.setMockInitialValues({});
    await expectLater(PendingPhotoStore().capture('v1', 'd1', ImageSource.camera), throwsStateError);
    expect(await PendingPhotoStore().read(), isNull);
  });
  test('Arranque con refresh vencido vuelve a login sin perder la foto', () async {
    final store = PendingPhotoStore(pick: (_) async => XFile('/cache/a.jpg'));
    await store.capture('v1', 'd1', ImageSource.camera);
    expect(await SessionService.restaurar(), isFalse);
    expect(await AuthStorage.instance.getAccessToken(), isNull);
    expect((await store.read())?.path, '/cache/a.jpg');
    expect((await store.read())?.ownerId, 'owner-a');
  });
}
