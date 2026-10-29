import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  final policy = File(
    'android/app/src/debug/res/xml/network_security_config.xml',
  ).readAsStringSync();

  test('HTTP debug permite solo los cuatro destinos de prueba explícitos', () {
    final hosts = RegExp(r'<domain>([^<]+)</domain>')
        .allMatches(policy)
        .map((match) => match.group(1))
        .toList();
    expect(hosts, ['localhost', '127.0.0.1', '10.0.2.2', '192.168.1.12']);
    expect(
      policy,
      contains('<base-config cleartextTrafficPermitted="false" />'),
    );
    expect(policy, isNot(contains('includeSubdomains="true"')));
  });

  test('La excepción HTTP permanece en el manifiesto debug, no en main', () {
    final debug = File('android/app/src/debug/AndroidManifest.xml')
        .readAsStringSync();
    final main = File('android/app/src/main/AndroidManifest.xml')
        .readAsStringSync();
    expect(debug, contains('android:networkSecurityConfig='));
    expect(main, isNot(contains('android:networkSecurityConfig=')));
    expect(main, isNot(contains('android:usesCleartextTraffic="true"')));
    expect(
      File('android/app/src/main/res/xml/network_security_config.xml')
          .existsSync(),
      isFalse,
    );
  });

  test('Si se compila para HTTP, su destino coincide con la lista debug', () {
    const apiUrl = String.fromEnvironment('API_BASE_URL');
    // La ejecución sin dart-define no comprueba una variante de APK concreta.
    if (apiUrl.isEmpty) return;
    final uri = Uri.parse(apiUrl);
    expect(uri.hasAuthority, isTrue);
    expect(uri.userInfo, isEmpty);
    if (uri.scheme == 'http') {
      expect(policy, contains('<domain>${uri.host}</domain>'));
    } else {
      expect(uri.scheme, 'https');
    }
  });
}
