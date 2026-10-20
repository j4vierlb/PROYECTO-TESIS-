// =============================================================================
// services/session.dart — Mantener la sesión al reabrir la app
// -----------------------------------------------------------------------------
// Al abrir la app se decide si el técnico entra directo o debe escribir su
// clave, usando los tokens guardados por AuthStorage:
//   - access_token vigente                    -> entra directo.
//   - access_token vencido y hay internet     -> se renueva con /auth/refresh.
//   - sin internet                            -> entra igual; la sesión se
//                                                renueva cuando vuelva la señal.
//   - refresh_token vencido (30 días sin usar
//     la app) o cuenta desactivada            -> vuelve al login.
// =============================================================================

import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;

import 'api_client.dart';
import 'auth_storage.dart';

/// Lee la fecha de vencimiento ("exp") que viene dentro de un JWT. No
/// verifica la firma (eso lo hace el backend): solo sirve para saber si
/// vale la pena intentar usarlo. Devuelve null si el token no se puede leer.
DateTime? vencimientoDelToken(String token) {
  try {
    final partes = token.split('.');
    if (partes.length != 3) return null;
    final payload = utf8.decode(base64Url.decode(base64Url.normalize(partes[1])));
    final exp = (jsonDecode(payload) as Map<String, dynamic>)['exp'];
    if (exp is! num) return null;
    return DateTime.fromMillisecondsSinceEpoch(exp.toInt() * 1000, isUtc: true);
  } catch (_) {
    return null;
  }
}

/// true si el token ya venció o vence dentro del `margen` (para no usar uno
/// que expire a mitad de una petición). Un token ilegible cuenta como vencido.
bool tokenVencido(String token, {DateTime? ahora, Duration margen = const Duration(minutes: 5)}) {
  final vence = vencimientoDelToken(token);
  if (vence == null) return true;
  return !vence.isAfter((ahora ?? DateTime.now().toUtc()).add(margen));
}

class SessionService {
  SessionService._();

  /// Decide al abrir la app si hay una sesión utilizable. true = entrar
  /// directo a la agenda; false = mostrar el login.
  static Future<bool> restaurar({ApiClient? apiClient}) async {
    final storage = AuthStorage.instance;
    final refreshToken = await storage.getRefreshToken();
    if (refreshToken == null || tokenVencido(refreshToken, margen: Duration.zero)) {
      await storage.clear(); // nunca hubo sesión o pasaron más de 30 días
      return false;
    }
    final accessToken = await storage.getAccessToken();
    if (accessToken != null && !tokenVencido(accessToken)) return true;

    // El access_token venció: se intenta renovar.
    try {
      return await (apiClient ?? ApiClient()).refreshSession();
    } on SocketException {
      return true; // sin internet: se entra igual y se renueva más tarde
    } on TimeoutException {
      return true;
    } on http.ClientException {
      return true;
    }
  }
}
