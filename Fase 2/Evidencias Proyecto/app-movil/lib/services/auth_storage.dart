// =============================================================================
// services/auth_storage.dart — Guardado seguro de la sesión
// -----------------------------------------------------------------------------
// Guarda los tokens que entrega el login para no pedir la clave en cada
// pantalla. Se guardan cifrados, nunca en texto plano.
// =============================================================================

import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Guarda los tokens JWT cifrados (Keychain en iOS, Keystore/EncryptedSharedPreferences
/// en Android) en vez de en texto plano, como pide la decisión de formato del proyecto.
class AuthStorage {
  // Singleton: una sola instancia para toda la app (AuthStorage.instance).
  AuthStorage._();
  static final AuthStorage instance = AuthStorage._();

  final FlutterSecureStorage _storage = const FlutterSecureStorage();

  // Nombres ("llaves") con los que se guarda cada token.
  static const String _accessTokenKey = 'access_token';
  static const String _refreshTokenKey = 'refresh_token';

  /// Guarda los dos tokens después de un login exitoso.
  Future<void> saveTokens({required String accessToken, required String refreshToken}) async {
    await _storage.write(key: _accessTokenKey, value: accessToken);
    await _storage.write(key: _refreshTokenKey, value: refreshToken);
  }

  /// Token que se envía en cada request. null si no hay sesión.
  Future<String?> getAccessToken() => _storage.read(key: _accessTokenKey);

  /// Token de renovación (todavía no se usa: falta el endpoint /auth/refresh).
  Future<String?> getRefreshToken() => _storage.read(key: _refreshTokenKey);

  /// Borra la sesión (se usa al cerrar sesión).
  Future<void> clear() async {
    await _storage.delete(key: _accessTokenKey);
    await _storage.delete(key: _refreshTokenKey);
  }
}
