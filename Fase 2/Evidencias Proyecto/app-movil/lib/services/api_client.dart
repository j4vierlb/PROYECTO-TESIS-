// =============================================================================
// services/api_client.dart — Comunicación con el backend
// -----------------------------------------------------------------------------
// Todas las llamadas HTTP de la app pasan por aquí. Las pantallas nunca usan
// `http` directamente: llaman a estos métodos y reciben objetos ya
// convertidos (Visita, Croquis...) o una ApiException si algo falla.
// =============================================================================

import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';

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

  /// Se llama cuando la sesión ya no se puede renovar (pasaron más de 30
  /// días o la cuenta fue desactivada). main.dart la usa para volver al login.
  static void Function()? onSesionVencida;

  // Si varias pantallas detectan a la vez el token vencido, todas esperan la
  // MISMA renovación en vez de pedir una cada una.
  static Future<bool>? _renovando;

  /// POST /auth/refresh — pide tokens nuevos con el refresh_token guardado.
  /// true si se renovó; false si el backend lo rechazó (sesión vencida), y en
  /// ese caso borra los tokens. Sin internet lanza la excepción de red.
  Future<bool> refreshSession() {
    return _renovando ??= _pedirRenovacion().whenComplete(() => _renovando = null);
  }

  Future<bool> _pedirRenovacion() async {
    final refreshToken = await AuthStorage.instance.getRefreshToken();
    if (refreshToken == null) return false;
    final response = await http
        .post(
          Uri.parse('$baseUrl/auth/refresh'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({'refresh_token': refreshToken}),
        )
        .timeout(const Duration(seconds: 15));
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      await AuthStorage.instance.saveTokens(
        accessToken: data['access_token'] as String,
        refreshToken: data['refresh_token'] as String,
      );
      return true;
    }
    if (response.statusCode == 401) {
      await AuthStorage.instance.clear();
      return false;
    }
    // Otro error (servidor caído, 500...): no se borra la sesión.
    throw ApiException(response.statusCode, _extractDetail(response.body));
  }

  /// Ante un 401 en una petición: intenta renovar la sesión una vez. Si no se
  /// puede, avisa a la app (vuelve al login) y lanza el error.
  Future<void> _renovarOCerrarSesion() async {
    if (await refreshSession()) return;
    onSesionVencida?.call();
    throw ApiException(401, 'Tu sesión venció. Vuelve a iniciar sesión.');
  }

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

  /// POST /croquis/{visita_id} — crea el croquis de la visita si todavía no
  /// tiene (trae copiadas las trampas activas de la visita anterior del
  /// cliente). Si ya existía, el backend lo devuelve sin duplicarlo.
  Future<Croquis> createCroquis(String visitaId) async {
    final body = await _authenticatedRequest('POST', '/croquis/$visitaId');
    return Croquis.fromJson(jsonDecode(body) as Map<String, dynamic>);
  }

  /// POST /croquis/{visita_id}/dispositivos — agrega una trampa instalada en
  /// terreno. El backend le asigna el código (T-01, T-02...).
  Future<DispositivoTrampa> addDispositivo(
    String visitaId, {
    required String tipo,
    required double lat,
    required double lng,
  }) async {
    final body = await _authenticatedRequest(
      'POST',
      '/croquis/$visitaId/dispositivos',
      body: {'tipo': tipo, 'lat': lat, 'lng': lng},
    );
    return DispositivoTrampa.fromJson(jsonDecode(body) as Map<String, dynamic>);
  }

  /// POST /dispositivos-trampa/{id}/foto — sube la foto de referencia de la
  /// trampa (archivo JPEG tomado con la cámara). Devuelve la trampa con su
  /// nueva `fotoUrl`.
  Future<DispositivoTrampa> uploadFoto(String dispositivoId, String rutaArchivo, {bool reintento = false}) async {
    final token = await AuthStorage.instance.getAccessToken();
    if (token == null) {
      throw ApiException(401, 'No hay sesión activa');
    }
    // Formulario "multipart": la forma estándar de enviar un archivo por HTTP.
    final request = http.MultipartRequest('POST', Uri.parse('$baseUrl/dispositivos-trampa/$dispositivoId/foto'))
      ..headers['Authorization'] = 'Bearer $token'
      ..files.add(await http.MultipartFile.fromPath('foto', rutaArchivo, contentType: MediaType('image', 'jpeg')));
    // Subir una foto por datos móviles puede tardar más que una petición normal.
    final streamed = await request.send().timeout(const Duration(seconds: 60));
    final response = await http.Response.fromStream(streamed);
    // Token vencido: se renueva y se sube otra vez (una sola vez).
    if (response.statusCode == 401 && !reintento) {
      await _renovarOCerrarSesion();
      return uploadFoto(dispositivoId, rutaArchivo, reintento: true);
    }
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw ApiException(response.statusCode, _extractDetail(response.body));
    }
    return DispositivoTrampa.fromJson(jsonDecode(response.body) as Map<String, dynamic>);
  }

  /// Dirección completa de una foto (fotoUrl viene relativa) y el header con
  /// el token, porque las fotos no son públicas: Image.network los necesita.
  String fotoUrlCompleta(String fotoUrl) => '$baseUrl$fotoUrl';

  Future<Map<String, String>> authHeaders() async {
    final token = await AuthStorage.instance.getAccessToken();
    return {if (token != null) 'Authorization': 'Bearer $token'};
  }

  /// Atajo para los GET autenticados.
  Future<String> _authenticatedGet(String path) => _authenticatedRequest('GET', path);

  /// Request autenticado con el access_token guardado. Centraliza el manejo
  /// de "sin sesión", del tiempo de espera y de los errores {"detail": "..."}
  /// para todos los endpoints protegidos.
  Future<String> _authenticatedRequest(
    String method,
    String path, {
    Map<String, dynamic>? body,
    bool reintento = false,
  }) async {
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

    // 401 = el access_token venció (dura 8 horas): se renueva con el
    // refresh_token y se repite la misma petición una sola vez.
    if (response.statusCode == 401 && !reintento) {
      await _renovarOCerrarSesion();
      return _authenticatedRequest(method, path, body: body, reintento: true);
    }

    // Cualquier 2xx es éxito (200 OK, 201 creado).
    if (response.statusCode < 200 || response.statusCode >= 300) {
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
