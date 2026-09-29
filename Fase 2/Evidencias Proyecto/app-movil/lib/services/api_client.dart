// =============================================================================
// services/api_client.dart — Comunicación con el backend
// -----------------------------------------------------------------------------
// Todas las llamadas HTTP de la app pasan por aquí. Las pantallas nunca usan
// `http` directamente: llaman a estos métodos y reciben objetos ya
// convertidos (Visita, Croquis...) o una ApiException si algo falla.
// =============================================================================

import 'dart:convert';

import 'package:http/http.dart' as http;

import '../models/croquis.dart';
import '../models/visita.dart';
import 'auth_storage.dart';

/// Excepción con el mensaje real que devolvió el backend (siempre viene como
/// {"detail": "..."}), para poder mostrárselo tal cual al operador.
class ApiException implements Exception {
  final int statusCode; // código HTTP: 401, 403, 404...
  final String message;

  ApiException(this.statusCode, this.message);

  @override
  String toString() => message;
}

class ApiClient {
  // Un iPhone físico no comparte la red del Mac como el simulador, así que
  // necesita la IP real del Mac en la WiFi (no "localhost"). Esa IP puede
  // cambiar (otra red, el router la reasigna), por eso se pasa al compilar:
  //   flutter run --release --dart-define=API_BASE_URL=http://$(ipconfig getifaddr en0):8000
  // Si no se indica, se usa el valor por defecto de abajo.
  static const String baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://192.168.1.139:8000',
  );

  /// POST /auth/login. Si las credenciales son correctas, guarda los tokens
  /// de forma segura; si no, lanza ApiException con el mensaje del backend.
  Future<void> login(String usuario, String clave) async {
    // `await` espera la respuesta sin congelar la pantalla.
    final response = await http.post(
      Uri.parse('$baseUrl/auth/login'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'usuario': usuario, 'clave': clave}), // Map -> texto JSON
    );

    if (response.statusCode != 200) {
      throw ApiException(response.statusCode, _extractDetail(response.body));
    }

    final data = jsonDecode(response.body) as Map<String, dynamic>; // texto JSON -> Map
    await AuthStorage.instance.saveTokens(
      accessToken: data['access_token'] as String,
      refreshToken: data['refresh_token'] as String,
    );
  }

  /// GET /operadores/me/visitas-hoy — la agenda del día.
  Future<List<Visita>> fetchVisitasHoy() async {
    final body = await _authenticatedGet('/operadores/me/visitas-hoy');
    final data = jsonDecode(body) as List<dynamic>;
    // Convierte cada elemento del JSON en un objeto Visita.
    return data.map((item) => Visita.fromJson(item as Map<String, dynamic>)).toList();
  }

  /// Visitas completadas del operador, de la más reciente a la más antigua.
  /// `limit`/`offset` permiten pedirlas por páginas.
  Future<List<Visita>> fetchHistorial({int limit = 20, int offset = 0}) async {
    final body = await _authenticatedGet('/operadores/me/visitas-historial?limit=$limit&offset=$offset');
    final data = jsonDecode(body) as List<dynamic>;
    return data.map((item) => Visita.fromJson(item as Map<String, dynamic>)).toList();
  }

  /// GET /visitas/{id} — detalle de una visita.
  Future<Visita> fetchVisita(String visitaId) async {
    final body = await _authenticatedGet('/visitas/$visitaId');
    return Visita.fromJson(jsonDecode(body) as Map<String, dynamic>);
  }

  /// GET /croquis/{visita_id} — croquis de la visita con sus trampas.
  Future<Croquis> fetchCroquis(String visitaId) async {
    final body = await _authenticatedGet('/croquis/$visitaId');
    return Croquis.fromJson(jsonDecode(body) as Map<String, dynamic>);
  }

  /// Actualiza el estado y/o las notas de una visita (PATCH parcial: solo se
  /// envían los campos que se pasan). Devuelve la visita ya actualizada.
  Future<Visita> updateVisita(String visitaId, {String? estado, String? notas}) async {
    final body = await _authenticatedRequest(
      'PATCH',
      '/visitas/$visitaId',
      // `'estado': ?estado` solo agrega la clave si el valor no es null, así
      // no se manda "notas": null por error y se borran las notas.
      body: {
        'estado': ?estado,
        'notas': ?notas,
      },
    );
    return Visita.fromJson(jsonDecode(body) as Map<String, dynamic>);
  }

  /// Acción del operador sobre una trampa: 'confirmar', 'mover' (requiere
  /// lat/lng) o 'eliminar' (el backend solo la marca como retirada).
  Future<DispositivoTrampa> updateDispositivo(
    String dispositivoId,
    String accion, {
    double? lat,
    double? lng,
  }) async {
    final body = await _authenticatedRequest(
      'PATCH',
      '/dispositivos-trampa/$dispositivoId',
      body: {
        'accion': accion,
        'lat': ?lat,
        'lng': ?lng,
      },
    );
    return DispositivoTrampa.fromJson(jsonDecode(body) as Map<String, dynamic>);
  }

  /// Atajo para los GET autenticados.
  Future<String> _authenticatedGet(String path) => _authenticatedRequest('GET', path);

  /// Request autenticado con el access_token guardado. Centraliza el manejo
  /// de "sin sesión", del tiempo de espera y de los errores {"detail": "..."}
  /// para todos los endpoints protegidos.
  Future<String> _authenticatedRequest(String method, String path, {Map<String, dynamic>? body}) async {
    final token = await AuthStorage.instance.getAccessToken();
    if (token == null) {
      throw ApiException(401, 'No hay sesión activa');
    }

    // Arma el request con el token en el header Authorization, que es lo que
    // el backend revisa en dependencies.py (get_current_user).
    final request = http.Request(method, Uri.parse('$baseUrl$path'))
      ..headers['Authorization'] = 'Bearer $token';
    if (body != null) {
      request.headers['Content-Type'] = 'application/json';
      request.body = jsonEncode(body);
    }

    // Si el servidor no responde en 15 segundos, se corta con un error en vez
    // de dejar al operador esperando indefinidamente.
    final streamed = await request.send().timeout(const Duration(seconds: 15));
    final response = await http.Response.fromStream(streamed);

    if (response.statusCode != 200) {
      throw ApiException(response.statusCode, _extractDetail(response.body));
    }
    return response.body;
  }

  /// Saca el mensaje de error del JSON {"detail": "..."} del backend. Si la
  /// respuesta no tiene ese formato, devuelve un mensaje genérico.
  String _extractDetail(String body) {
    try {
      final decoded = jsonDecode(body) as Map<String, dynamic>;
      return decoded['detail'] as String? ?? 'Error inesperado (${body.length} bytes)';
    } catch (_) {
      return 'Error inesperado del servidor';
    }
  }
}
