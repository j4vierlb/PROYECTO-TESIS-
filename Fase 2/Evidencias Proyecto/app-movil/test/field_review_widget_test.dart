import 'dart:convert';

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

String token() => 'header.${base64Url.encode(utf8.encode(jsonEncode({'sub': 'owner-a', 'exp': DateTime.now().add(const Duration(hours: 8)).millisecondsSinceEpoch ~/ 1000}))).replaceAll('=', '')}.signature';

Map<String, dynamic> photo({String owner = 'owner-a', String visit = 'v1'}) => {'visitId': visit, 'deviceId': 'd1', 'path': '/cache/a.jpg', 'ownerId': owner};

Map<String, dynamic> visitJson(String state) => {
  'id': 'v1', 'cliente': {'id': 'c1', 'nombre': 'Cliente QA', 'telefono_whatsapp': '+56911111111', 'direccion': 'Dirección demo', 'lat': -33.48, 'lng': -70.59},
  'operador_id': 'owner-a', 'fecha_hora': '2026-10-23T13:00:00Z', 'estado': state, 'origen_agendamiento': 'manual', 'notas': 'Prueba',
};

ApiClient mockApi({String? photoUrl, void Function()? onPatch}) => ApiClient(client: MockClient((request) async {
  if (request.method == 'PATCH') { onPatch?.call(); return http.Response(jsonEncode(visitJson('completada')), 200); }
  if (request.url.path == '/visitas/v1') return http.Response(jsonEncode(visitJson('en_curso')), 200);
  return http.Response(jsonEncode({
    'id': 'cr1', 'visita_id': 'v1', 'cliente_id': 'c1', 'version': 1, 'sugerido_por_ia': false, 'validado_por_operador': false,
    'dispositivos': [{'id': 'd1', 'codigo': 'T-01', 'tipo': 'cebadero', 'lat': -33.48, 'lng': -70.59, 'sugerido_por_ia': false, 'confirmado': false, 'estado': 'activo', 'foto_url': photoUrl}],
  }), 200);
}));

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
    FlutterSecureStorage.setMockInitialValues({'access_token': token(), 'refresh_token': 'refresh'});
    ApiClient.onSesionVencida = null;
  });

  for (final url in ['https://other.invalid/photo', 'http://[', '/dispositivos-trampa/%FF/foto']) {
    testWidgets('Croquis con URL inválida mantiene la trampa sin foto: $url', (tester) async {
      await openScreen(tester, CroquisScreen(visitaId: 'v1', apiClient: mockApi(photoUrl: url)));
      expect(tester.takeException(), isNull);
      expect(find.text('T-01 · Cebadero'), findsOneWidget);
      expect(find.byType(Image), findsNothing);
      expect(find.byTooltip('Sacar foto'), findsOneWidget);
    });
  }

  testWidgets('Bloquea PATCH de cierre con foto pendiente; descartar permite cerrar', (tester) async {
    const storage = FlutterSecureStorage();
    await storage.write(key: PendingPhotoStore.storageKey, value: jsonEncode(photo()));
    var writes = 0;
    await openScreen(tester, VisitaDetalleScreen(visitaId: 'v1', apiClient: mockApi(onPatch: () => writes++)));
    await complete(tester);
    expect(writes, 0);
    expect(find.textContaining('Hay una foto pendiente.'), findsOneWidget);
    expect(await storage.read(key: PendingPhotoStore.storageKey), isNotNull);
    await PendingPhotoStore.instance.clear();
    await complete(tester);
    expect(writes, 1);
    expect(find.text('Esta visita ya está completada'), findsOneWidget);
  });

  testWidgets('Foto de otra visita no impide completar esta', (tester) async {
    await const FlutterSecureStorage().write(key: PendingPhotoStore.storageKey, value: jsonEncode(photo(visit: 'v2')));
    var writes = 0;
    await openScreen(tester, VisitaDetalleScreen(visitaId: 'v1', apiClient: mockApi(onPatch: () => writes++)));
    await complete(tester);
    expect(writes, 1);
    expect((await PendingPhotoStore.instance.read())?.visitId, 'v2');
  });

  testWidgets('Croquis no muestra la foto pendiente de otra cuenta', (tester) async {
    await const FlutterSecureStorage().write(key: PendingPhotoStore.storageKey, value: jsonEncode(photo(owner: 'owner-b')));
    await openScreen(tester, CroquisScreen(visitaId: 'v1', apiClient: mockApi()));
    expect(find.textContaining('Hay una foto pendiente'), findsNothing);
    expect((await PendingPhotoStore.instance.read())?.ownerId, 'owner-b');
  });

  testWidgets('Logout advierte: Volver conserva tokens y foto; confirmar descarta', (tester) async {
    await const FlutterSecureStorage().write(key: PendingPhotoStore.storageKey, value: jsonEncode(photo()));
    await openScreen(tester, Scaffold(appBar: AppBar(actions: const [LogoutButton()]), body: const Text('Agenda QA')));
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
  });
}
