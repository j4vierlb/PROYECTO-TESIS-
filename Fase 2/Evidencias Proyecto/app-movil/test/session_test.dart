// =============================================================================
// test/session_test.dart — Saber si un token sigue vigente
// -----------------------------------------------------------------------------
// Al abrir la app se lee el vencimiento ("exp") del token guardado para
// decidir si se entra directo, se renueva la sesión o se vuelve al login.
// =============================================================================

import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';

import 'package:app_movil/services/session.dart';

/// Arma un JWT de prueba con el "exp" indicado (la firma no importa aquí).
String jwtQueVence(DateTime vence) {
  String parte(Map<String, dynamic> datos) => base64Url.encode(utf8.encode(jsonEncode(datos))).replaceAll('=', '');
  final payload = {'sub': 'u1', 'rol': 'operador', 'type': 'access', 'exp': vence.millisecondsSinceEpoch ~/ 1000};
  return '${parte({'alg': 'HS256', 'typ': 'JWT'})}.${parte(payload)}.firma';
}

void main() {
  final ahora = DateTime.utc(2026, 10, 20, 12);

  test('Lee el vencimiento que viene dentro del token', () {
    final vence = DateTime.utc(2026, 10, 20, 20);
    expect(vencimientoDelToken(jwtQueVence(vence)), vence);
  });

  test('Token con horas por delante está vigente', () {
    expect(tokenVencido(jwtQueVence(ahora.add(const Duration(hours: 7))), ahora: ahora), isFalse);
  });

  test('Token vencido, o a punto de vencer (margen de 5 minutos), se trata como vencido', () {
    expect(tokenVencido(jwtQueVence(ahora.subtract(const Duration(minutes: 1))), ahora: ahora), isTrue);
    expect(tokenVencido(jwtQueVence(ahora.add(const Duration(minutes: 3))), ahora: ahora), isTrue);
  });

  test('Un token dañado o que no es JWT cuenta como vencido', () {
    for (final token in ['', 'abc', 'a.b.c', 'a.${base64Url.encode(utf8.encode('{"sin":"exp"}'))}.c']) {
      expect(vencimientoDelToken(token), isNull, reason: token);
      expect(tokenVencido(token, ahora: ahora), isTrue, reason: token);
    }
  });
}
