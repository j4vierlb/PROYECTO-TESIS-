// =============================================================================
// offline/owner.dart — Qué cuenta es dueña de los datos guardados
// -----------------------------------------------------------------------------
// Lo guardado en el teléfono se separa por cuenta, usando el "sub" (id del
// usuario) que viene dentro del token. Así, si otro técnico inicia sesión en
// el mismo teléfono, no ve ni envía los cambios del anterior.
// =============================================================================

import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;

import '../services/api_client.dart';
import '../services/auth_storage.dart';

/// Id del usuario que viene dentro de un JWT, o null si no se puede leer. No
/// verifica la firma: solo sirve para separar los datos locales por cuenta.
String? jwtSubject(String? token) {
  if (token == null) return null;
  try {
    final parts = token.split('.');
    if (parts.length != 3) return null;
    final claims = jsonDecode(utf8.decode(base64Url.decode(base64Url.normalize(parts[1]))));
    final subject = claims is Map<String, dynamic> ? claims['sub'] : null;
    return subject is String && subject.isNotEmpty ? subject : null;
  } catch (_) {
    return null;
  }
}

/// Dueño de los datos para la sesión actual. Usa el access_token y, si ya no
/// está, el refresh_token (el id de usuario es el mismo en ambos).
Future<String?> currentOwner() async {
  try {
    final storage = AuthStorage.instance;
    return jwtSubject(await storage.getAccessToken()) ?? jwtSubject(await storage.getRefreshToken());
  } catch (_) {
    return null;
  }
}

/// true si el error es de red (sin señal, tiempo agotado, servidor
/// inalcanzable): el cambio se puede reintentar más tarde sin perderlo.
bool esErrorDeRed(Object error) =>
    error is SocketException ||
    error is TimeoutException ||
    error is http.ClientException ||
    error is HandshakeException;

/// true si vale la pena reintentar: error de red, o un servidor caído o
/// saturado (5xx, 408, 429). Un 4xx como 403, 404 o 409 fallaría igual al
/// reintentar: es un conflicto con el servidor.
bool esReintentable(Object error) {
  if (esErrorDeRed(error)) return true;
  if (error is ApiException) {
    final code = error.statusCode;
    return code >= 500 || code == 408 || code == 429;
  }
  return false;
}
