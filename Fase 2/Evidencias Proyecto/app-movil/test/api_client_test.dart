import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:app_movil/services/api_client.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

String accessToken() {
  final payload = base64Url
      .encode(
        utf8.encode(
          jsonEncode({
            'sub': 'owner-a',
            'exp':
                DateTime.now()
                    .add(const Duration(hours: 8))
                    .millisecondsSinceEpoch ~/
                1000,
          }),
        ),
      )
      .replaceAll('=', '');
  return 'eyJhbGciOiJIUzI1NiJ9.$payload.test-signature';
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late String access;
  setUp(() {
    access = accessToken();
    FlutterSecureStorage.setMockInitialValues({
      'access_token': access,
      'refresh_token': 'refresh-test',
    });
    ApiClient.onSesionVencida = null;
  });
  test('Agenda transmite token en header, nunca en URL', () async {
    final api = ApiClient(
      client: MockClient((request) async {
        expect(request.headers['Authorization'], 'Bearer $access');
        expect(request.url.toString(), isNot(contains(access)));
        return http.Response('[]', 200);
      }),
    );
    expect(await api.fetchVisitasHoy(), isEmpty);
  });
  test('401 renueva y repite una sola vez con el token nuevo', () async {
    var calls = 0;
    final api = ApiClient(
      client: MockClient((request) async {
        calls++;
        if (request.url.path == '/auth/refresh') {
          return http.Response(
            jsonEncode({
              'access_token': 'new-access',
              'refresh_token': 'new-refresh',
            }),
            200,
          );
        }
        return request.headers['Authorization'] == 'Bearer new-access'
            ? http.Response('[]', 200)
            : http.Response('{}', 401);
      }),
    );
    expect(await api.fetchVisitasHoy(), isEmpty);
    expect(calls, 3);
  });
  test('Segundo 401 no forma bucle: cierra sesion y avisa una vez', () async {
    var notices = 0;
    var calls = 0;
    ApiClient.onSesionVencida = () => notices++;
    final api = ApiClient(
      client: MockClient((request) async {
        calls++;
        return request.url.path == '/auth/refresh'
            ? http.Response(
                '{"access_token":"new","refresh_token":"new-r"}',
                200,
              )
            : http.Response('{}', 401);
      }),
    );
    await expectLater(
      api.fetchVisitasHoy(),
      throwsA(isA<ApiException>().having((e) => e.statusCode, 'status', 401)),
    );
    expect(calls, 3);
    expect(notices, 1);
    expect(
      await const FlutterSecureStorage().read(key: 'access_token'),
      isNull,
    );
  });
  test('Sin red conserva tokens para reintentar', () async {
    final api = ApiClient(
      client: MockClient((_) => throw http.ClientException('offline')),
    );
    await expectLater(
      api.fetchVisitasHoy(),
      throwsA(isA<http.ClientException>()),
    );
    expect(
      await const FlutterSecureStorage().read(key: 'access_token'),
      access,
    );
  });
  test('401 al renovar conserva foto pendiente y solicita reingreso', () async {
    const storage = FlutterSecureStorage();
    await storage.write(
      key: 'pending_field_photo',
      value: jsonEncode({
        'visitId': 'v1',
        'deviceId': 'd1',
        'path': '/cache/a.jpg',
        'ownerId': 'owner-a',
      }),
    );
    var notices = 0;
    ApiClient.onSesionVencida = () => notices++;
    final api = ApiClient(
      client: MockClient((_) async => http.Response('{}', 401)),
    );
    await expectLater(api.fetchVisitasHoy(), throwsA(isA<ApiException>()));
    expect(notices, 1);
    expect(await storage.read(key: 'access_token'), isNull);
    expect(
      jsonDecode((await storage.read(key: 'pending_field_photo'))!)['path'],
      '/cache/a.jpg',
    );
  });
  test('Timeout de login tambien esta acotado', () async {
    final api = ApiClient(
      client: MockClient((_) => Completer<http.Response>().future),
      requestTimeout: const Duration(milliseconds: 10),
    );
    await expectLater(
      api.login('test@example.invalid', 'invalid'),
      throwsA(isA<TimeoutException>()),
    );
  });
  test('Timeout contempla el cuerpo, no solo los headers', () async {
    final body = StreamController<List<int>>();
    final api = ApiClient(
      client: _StreamingClient(body.stream),
      requestTimeout: const Duration(milliseconds: 10),
    );
    await expectLater(api.fetchVisitasHoy(), throwsA(isA<TimeoutException>()));
    body.add(utf8.encode('[]'));
    await body.close();
  });
  test('422 mantiene el mensaje de validacion del backend', () async {
    final api = ApiClient(
      client: MockClient(
        (_) async =>
            http.Response('{"detail":[{"msg":"Coordenadas invalidas"}]}', 422),
      ),
    );
    await expectLater(
      api.fetchVisitasHoy(),
      throwsA(
        isA<ApiException>().having(
          (e) => e.message,
          'mensaje',
          contains('Coordenadas invalidas'),
        ),
      ),
    );
  });
  test('Foto relativa conserva la version de cache del backend', () {
    expect(
      ApiClient().fotoUrlCompleta('/dispositivos-trampa/d1/foto?v=abc123'),
      endsWith('/dispositivos-trampa/d1/foto?v=abc123'),
    );
  });
  for (final path in [
    null,
    '',
    'http://[',
    'https://other.invalid/foto',
    '//other.invalid/foto',
    '/other/foto',
    '/dispositivos-trampa/d1/foto?token=secret',
    '/dispositivos-trampa/../foto',
    '/dispositivos-trampa/%FF/foto',
    '/dispositivos-trampa/d1/foto?v=%FF',
    '/dispositivos-trampa/d1/otra/foto',
    '/dispositivos-trampa/%2F../foto',
  ]) {
    test(
      'Rechaza foto fuera del contrato: $path',
      () => expect(ApiClient().fotoUrlCompleta(path), isNull),
    );
  }
  test(
    'Cabeceras de fotos renuevan access vencido antes de abrir imagen',
    () async {
      FlutterSecureStorage.setMockInitialValues({
        'access_token': 'expired',
        'refresh_token': 'refresh-test',
      });
      final api = ApiClient(
        client: MockClient(
          (_) async => http.Response(
            '{"access_token":"new","refresh_token":"new-r"}',
            200,
          ),
        ),
      );
      expect((await api.authHeaders())['Authorization'], 'Bearer new');
    },
  );
  test('Upload PNG conserva MIME y Authorization', () async {
    final dir = await Directory.systemTemp.createTemp('field-photo-test-');
    try {
      final file = File('${dir.path}/photo.png')
        ..writeAsBytesSync([137, 80, 78, 71]);
      final api = ApiClient(
        client: MockClient((request) async {
          expect(request.headers['Authorization'], 'Bearer $access');
          expect(
            utf8.decode(request.bodyBytes, allowMalformed: true),
            contains('image/png'),
          );
          return http.Response(
            '{"id":"d1","codigo":"T-01","tipo":"cebadero","lat":-33.48,"lng":-70.59,"sugerido_por_ia":false,"confirmado":true,"estado":"activo","foto_url":"/dispositivos-trampa/d1/foto?v=1"}',
            200,
          );
        }),
      );
      expect((await api.uploadFoto('d1', file.path)).fotoUrl, isNotNull);
    } finally {
      await dir.delete(recursive: true);
    }
  });
}

class _StreamingClient extends http.BaseClient {
  final Stream<List<int>> body;
  _StreamingClient(this.body);
  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async =>
      http.StreamedResponse(body, 200);
}
