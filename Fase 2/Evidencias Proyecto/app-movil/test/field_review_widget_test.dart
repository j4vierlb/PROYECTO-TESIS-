import 'dart:convert';

import 'package:app_movil/models/croquis.dart';
import 'package:app_movil/screens/croquis_screen.dart';
import 'package:app_movil/screens/visita_detalle_screen.dart';
import 'package:app_movil/services/api_client.dart';
import 'package:app_movil/services/auth_storage.dart';
import 'package:app_movil/services/pending_photo.dart';
import 'package:app_movil/widgets/logout_button.dart';
import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:image_picker/image_picker.dart';

import 'support/fake_pending_photo_files.dart';

String token() =>
    'header.${base64Url.encode(utf8.encode(jsonEncode({'sub': 'owner-a', 'exp': DateTime.now().add(const Duration(hours: 8)).millisecondsSinceEpoch ~/ 1000}))).replaceAll('=', '')}.signature';

Map<String, dynamic> photo({String owner = 'owner-a', String visit = 'v1'}) => {
  'visitId': visit,
  'deviceId': 'd1',
  'path': '/cache/a.jpg',
  'ownerId': owner,
};

Map<String, dynamic> visitJson(String state) => {
  'id': 'v1',
  'cliente': {
    'id': 'c1',
    'nombre': 'Cliente QA',
    'telefono_whatsapp': '+56911111111',
    'direccion': 'Dirección demo',
    'lat': -33.48,
    'lng': -70.59,
  },
  'operador_id': 'owner-a',
  'fecha_hora': '2026-10-23T13:00:00Z',
  'estado': state,
  'origen_agendamiento': 'manual',
  'notas': 'Prueba',
};

ApiClient mockApi({String? photoUrl, void Function()? onPatch}) => ApiClient(
  client: MockClient((request) async {
    if (request.method == 'PATCH') {
      onPatch?.call();
      return http.Response(jsonEncode(visitJson('completada')), 200);
    }
    if (request.url.path == '/visitas/v1') {
      return http.Response(jsonEncode(visitJson('en_curso')), 200);
    }
    return http.Response(
      jsonEncode({
        'id': 'cr1',
        'visita_id': 'v1',
        'cliente_id': 'c1',
        'version': 1,
        'sugerido_por_ia': false,
        'validado_por_operador': false,
        'dispositivos': [
          {
            'id': 'd1',
            'codigo': 'T-01',
            'tipo': 'cebadero',
            'lat': -33.48,
            'lng': -70.59,
            'sugerido_por_ia': false,
            'confirmado': false,
            'estado': 'activo',
            'foto_url': photoUrl,
          },
        ],
      }),
      200,
    );
  }),
);

class PhotoUploadApi extends ApiClient {
  final Future<void> Function(String, String) onUpload;
  PhotoUploadApi(this.onUpload) : super(client: mockApi().client);

  @override
  Future<DispositivoTrampa> uploadFoto(
    String dispositivoId,
    String rutaArchivo, {
    bool reintento = false,
  }) async {
    await onUpload(dispositivoId, rutaArchivo);
    return DispositivoTrampa.fromJson({
      'id': dispositivoId,
      'codigo': 'T-01',
      'tipo': 'cebadero',
      'lat': -33.48,
      'lng': -70.59,
      'sugerido_por_ia': false,
      'confirmado': false,
      'estado': 'activo',
      'foto_url': null,
    });
  }
}

class UnavailablePhotoFiles extends FakePendingPhotoFiles {
  const UnavailablePhotoFiles();
  @override
  Future<String> persist(XFile source) async => throw StateError('sin espacio');
}

Future<void> openScreen(WidgetTester tester, Widget screen) async {
  await tester.binding.setSurfaceSize(const Size(1100, 1600));
  addTearDown(() => tester.binding.setSurfaceSize(null));
  await tester.pumpWidget(MaterialApp(home: screen));
  await tester.pumpAndSettle();
}

Future<void> complete(WidgetTester tester) async {
  await tester.tap(find.text('Completar visita'));
  await tester.pumpAndSettle();
  await tester.tap(find.text('Completar', findRichText: false));
  await tester.pumpAndSettle();
}

void main() {
  setUp(() {
    FlutterSecureStorage.setMockInitialValues({
      'access_token': token(),
      'refresh_token': 'refresh',
    });
    ApiClient.onSesionVencida = null;
  });

  for (final state in ['en_curso', 'completada']) {
    testWidgets('Detalle transmite nombre, dirección y punto al croquis: $state', (tester) async {
      final api = ApiClient(client: MockClient((request) async {
        if (request.url.path == '/visitas/v1') {
          return http.Response(jsonEncode(visitJson(state)), 200);
        }
        return mockApi().client!.send(request).then(http.Response.fromStream);
      }));
      await openScreen(tester, VisitaDetalleScreen(visitaId: 'v1', apiClient: api));
      await tester.tap(find.text('Ver croquis'));
      await tester.pumpAndSettle();
      final screen = tester.widget<CroquisScreen>(find.byType(CroquisScreen));
      expect(screen.clienteNombre, 'Cliente QA');
      expect(screen.clienteDireccion, 'Dirección demo');
      expect(screen.clienteLat, -33.48);
      expect(screen.clienteLng, -70.59);
      expect(screen.readOnly, state == 'completada');
      expect(tester.takeException(), isNull);
    });
  }

  for (final url in [
    'https://other.invalid/photo',
    'http://[',
    '/dispositivos-trampa/%FF/foto',
  ]) {
    testWidgets('Croquis con URL inválida mantiene la trampa sin foto: $url', (
      tester,
    ) async {
      await openScreen(
        tester,
        CroquisScreen(
          visitaId: 'v1',
          apiClient: mockApi(photoUrl: url),
        ),
      );
      expect(tester.takeException(), isNull);
      expect(find.text('T-01 · Cebadero'), findsOneWidget);
      expect(find.byWidgetPredicate((widget) => widget is Image && widget.image is NetworkImage), findsNothing);
      expect(find.byTooltip('Sacar foto'), findsOneWidget);
    });
  }

  testWidgets(
    'Bloquea PATCH de cierre con foto pendiente; descartar permite cerrar',
    (tester) async {
      const storage = FlutterSecureStorage();
      await storage.write(
        key: PendingPhotoStore.storageKey,
        value: jsonEncode(photo()),
      );
      var writes = 0;
      await openScreen(
        tester,
        VisitaDetalleScreen(
          visitaId: 'v1',
          apiClient: mockApi(onPatch: () => writes++),
        ),
      );
      await complete(tester);
      expect(writes, 0);
      expect(find.textContaining('Hay una foto pendiente.'), findsOneWidget);
      expect(await storage.read(key: PendingPhotoStore.storageKey), isNotNull);
      await PendingPhotoStore.instance.clear();
      await complete(tester);
      expect(writes, 1);
      expect(find.text('Esta visita ya está completada'), findsOneWidget);
    },
  );

  testWidgets('Foto de otra visita no impide completar esta', (tester) async {
    await const FlutterSecureStorage().write(
      key: PendingPhotoStore.storageKey,
      value: jsonEncode(photo(visit: 'v2')),
    );
    var writes = 0;
    await openScreen(
      tester,
      VisitaDetalleScreen(
        visitaId: 'v1',
        apiClient: mockApi(onPatch: () => writes++),
      ),
    );
    await complete(tester);
    expect(writes, 1);
    expect((await PendingPhotoStore.instance.read())?.visitId, 'v2');
  });

  testWidgets('Croquis no muestra la foto pendiente de otra cuenta', (
    tester,
  ) async {
    await const FlutterSecureStorage().write(
      key: PendingPhotoStore.storageKey,
      value: jsonEncode(photo(owner: 'owner-b')),
    );
    await openScreen(
      tester,
      CroquisScreen(visitaId: 'v1', apiClient: mockApi()),
    );
    expect(find.textContaining('Hay una foto pendiente'), findsNothing);
    expect((await PendingPhotoStore.instance.read())?.ownerId, 'owner-b');
  });

  testWidgets(
    'Pendiente propia bloquea cámara sin ofrecer descartar la de otra cuenta',
    (tester) async {
      var captures = 0;
      final store = PendingPhotoStore(
        pick: (_) async {
          captures++;
          return null;
        },
      );
      await store.storage.write(
        key: PendingPhotoStore.storageKey,
        value: jsonEncode(photo(visit: 'v2')),
      );
      await openScreen(
        tester,
        CroquisScreen(visitaId: 'v1', apiClient: mockApi(), photoStore: store),
      );
      await tester.tap(find.byTooltip('Sacar foto'));
      await tester.pumpAndSettle();
      expect(
        find.textContaining('Reintenta o descarta primero'),
        findsOneWidget,
      );
      expect(find.text('Foto pendiente de otra cuenta'), findsNothing);
      expect(captures, 0);
      expect((await store.read())?.visitId, 'v2');
    },
  );

  testWidgets('Volver conserva la foto ajena y no abre cámara', (tester) async {
    var captures = 0;
    final store = PendingPhotoStore(
      pick: (_) async {
        captures++;
        return null;
      },
    );
    await store.storage.write(
      key: PendingPhotoStore.storageKey,
      value: jsonEncode(photo(owner: 'owner-b')),
    );
    await openScreen(
      tester,
      CroquisScreen(visitaId: 'v1', apiClient: mockApi(), photoStore: store),
    );
    await tester.tap(find.byTooltip('Sacar foto'));
    await tester.pumpAndSettle();
    expect(find.text('Foto pendiente de otra cuenta'), findsOneWidget);
    expect(find.textContaining('/cache/a.jpg'), findsNothing);
    expect(find.textContaining('owner-b'), findsNothing);
    await tester.tap(find.text('Volver'));
    await tester.pumpAndSettle();
    expect(captures, 0);
    expect((await store.read())?.ownerId, 'owner-b');
    expect((await store.read())?.path, '/cache/a.jpg');
  });

  for (final source in [ImageSource.camera, ImageSource.gallery]) {
    testWidgets(
      'Descartar envío ajeno permite abrir $source con cuenta actual',
      (tester) async {
        var captures = 0;
        late PendingPhotoStore store;
        store = PendingPhotoStore(
          pick: (selectedSource) async {
            captures++;
            expect(selectedSource, source);
            final pending = await store.readForCurrentAccount();
            expect(pending?.ownerId, 'owner-a');
            expect(pending?.visitId, 'v1');
            expect(pending?.deviceId, 'd1');
            expect(pending?.path, isNull);
            return null; // Cancelar el selector no debe restaurar el envío ajeno.
          },
        );
        await store.storage.write(
          key: PendingPhotoStore.storageKey,
          value: jsonEncode(photo(owner: 'owner-b')),
        );
        await openScreen(
          tester,
          CroquisScreen(
            visitaId: 'v1',
            apiClient: mockApi(),
            photoStore: store,
          ),
        );
        await tester.tap(find.byTooltip('Sacar foto'));
        await tester.pumpAndSettle();
        expect((await store.read())?.ownerId, 'owner-b');
        await tester.tap(find.text('Descartar y continuar'));
        await tester.pumpAndSettle();
        await tester.tap(
          find.text(
            source == ImageSource.camera
                ? 'Sacar foto'
                : 'Elegir de la galería',
          ),
        );
        await tester.pumpAndSettle();
        expect(captures, 1);
        expect(await store.read(), isNull);
        expect(find.textContaining('No se pudo abrir la cámara'), findsNothing);
        expect(tester.takeException(), isNull);
      },
    );
  }

  testWidgets('Pendiente antigua sin dueño ofrece descarte explícito', (
    tester,
  ) async {
    await const FlutterSecureStorage().write(
      key: PendingPhotoStore.storageKey,
      value: jsonEncode({...photo(), 'ownerId': null}),
    );
    await openScreen(
      tester,
      CroquisScreen(visitaId: 'v1', apiClient: mockApi()),
    );
    await tester.tap(find.byTooltip('Sacar foto'));
    await tester.pumpAndSettle();
    expect(find.text('Foto pendiente de otra cuenta'), findsOneWidget);
    await tester.tap(find.text('Volver'));
    await tester.pumpAndSettle();
    expect((await PendingPhotoStore.instance.read())?.path, '/cache/a.jpg');
  });

  testWidgets('Tras descartar foto ajena captura y sube solo la foto nueva', (
    tester,
  ) async {
    final store = PendingPhotoStore(
      files: const FakePendingPhotoFiles(),
      pick: (_) async => XFile('/cache/new.jpg'),
    );
    await store.storage.write(
      key: PendingPhotoStore.storageKey,
      value: jsonEncode(photo(owner: 'owner-b', visit: 'old-visit')),
    );
    var uploads = 0;
    final api = PhotoUploadApi((deviceId, path) async {
      uploads++;
      expect(deviceId, 'd1');
      expect(path, '/cache/new.jpg');
      final pending = await store.readForCurrentAccount();
      expect(pending?.ownerId, 'owner-a');
      expect(pending?.visitId, 'v1');
      expect(pending?.path, '/cache/new.jpg');
    });
    await openScreen(
      tester,
      CroquisScreen(visitaId: 'v1', apiClient: api, photoStore: store),
    );
    await tester.tap(find.byTooltip('Sacar foto'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Descartar y continuar'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Sacar foto'));
    await tester.pumpAndSettle();
    expect(uploads, 1);
    expect(await store.read(), isNull);
    expect(find.text('Foto de T-01 guardada'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'Conflicto al capturar informa pendiente, no permisos de cámara',
    (tester) async {
      await openScreen(
        tester,
        CroquisScreen(visitaId: 'v1', apiClient: mockApi()),
      );
      await tester.tap(find.byTooltip('Sacar foto'));
      await tester.pumpAndSettle();
      // Aparece un pendiente entre la comprobación y el selector.
      await const FlutterSecureStorage().write(
        key: PendingPhotoStore.storageKey,
        value: jsonEncode(photo()),
      );
      await tester.tap(find.text('Sacar foto'));
      await tester.pumpAndSettle();
      expect(
        find.text('Reintenta o descarta primero la foto pendiente'),
        findsOneWidget,
      );
      expect(find.textContaining('No se pudo abrir la cámara'), findsNothing);
      expect((await PendingPhotoStore.instance.read())?.ownerId, 'owner-a');
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets(
    'Fallo de disco mantiene el envío visible y no simula fallo de cámara',
    (tester) async {
      var uploads = 0;
      final store = PendingPhotoStore(
        files: const UnavailablePhotoFiles(),
        pick: (_) async => XFile('/cache/new.jpg'),
      );
      await openScreen(
        tester,
        CroquisScreen(
          visitaId: 'v1',
          photoStore: store,
          apiClient: PhotoUploadApi((_, _) async {
            uploads++;
          }),
        ),
      );
      await tester.tap(find.byTooltip('Sacar foto'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Sacar foto'));
      await tester.pumpAndSettle();
      expect(
        find.textContaining('No se pudo conservar la foto'),
        findsOneWidget,
      );
      expect(find.textContaining('Hay una foto pendiente'), findsOneWidget);
      expect(find.textContaining('No se pudo abrir la cámara'), findsNothing);
      expect((await store.read())?.path, '/cache/new.jpg');
      expect(uploads, 0);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets(
    'Logout advierte: Volver conserva tokens y foto; confirmar descarta',
    (tester) async {
      await const FlutterSecureStorage().write(
        key: PendingPhotoStore.storageKey,
        value: jsonEncode(photo()),
      );
      await openScreen(
        tester,
        Scaffold(
          appBar: AppBar(actions: const [LogoutButton()]),
          body: const Text('Agenda QA'),
        ),
      );
      await tester.tap(find.byTooltip('Cerrar sesión'));
      await tester.pumpAndSettle();
      expect(find.text('Foto sin enviar'), findsOneWidget);
      await tester.tap(find.text('Volver'));
      await tester.pumpAndSettle();
      expect(await AuthStorage.instance.getAccessToken(), isNotNull);
      expect(await PendingPhotoStore.instance.read(), isNotNull);
      await tester.tap(find.byTooltip('Cerrar sesión'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Salir y descartar'));
      await tester.pumpAndSettle();
      expect(await AuthStorage.instance.getAccessToken(), isNull);
      expect(await PendingPhotoStore.instance.read(), isNull);
      expect(find.text('Iniciar sesión'), findsOneWidget);
    },
  );
}
