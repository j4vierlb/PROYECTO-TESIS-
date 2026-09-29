// =============================================================================
// screens/login_screen.dart — Pantalla de inicio de sesión
// -----------------------------------------------------------------------------
// Primera pantalla de la app: logo, usuario y clave. Al tocar "Ingresar"
// llama al backend (POST /auth/login) y, si todo está bien, abre la pantalla
// principal con la agenda del día.
//
// Conceptos de Flutter que aparecen en las pantallas:
//   StatefulWidget  pantalla que cambia con el tiempo (cargando, error...).
//                   Sus datos viven en la clase State (_LoginScreenState).
//   setState(...)   avisa a Flutter que algo cambió y que redibuje.
//   build(...)      describe cómo se ve la pantalla según su estado actual.
// =============================================================================

import 'package:flutter/material.dart';

import '../services/api_client.dart';
import '../theme/app_theme.dart';
import 'home_screen.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  // Llave del formulario: permite validar todos los campos a la vez.
  final _formKey = GlobalKey<FormState>();
  // Precargados con el usuario de prueba real del backend, para agilizar
  // las pruebas durante el desarrollo.
  final _usuarioController = TextEditingController(text: 'tecnico1@killbichos.cl');
  final _claveController = TextEditingController(text: 'demo1234');
  final _apiClient = ApiClient();

  bool _loading = false; // true mientras se espera la respuesta del backend
  String? _errorMessage; // mensaje rojo bajo el formulario (null = sin error)

  Future<void> _handleLogin() async {
    // Si algún campo no pasa su validación, se muestran los errores y se para.
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _loading = true;
      _errorMessage = null;
    });

    try {
      await _apiClient.login(_usuarioController.text.trim(), _claveController.text);
      // `mounted` = la pantalla sigue abierta (el usuario pudo salir mientras
      // esperaba). Si ya no está, no se puede navegar desde ella.
      if (!mounted) return;
      // pushReplacement reemplaza el login: con "atrás" no se vuelve a él.
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(builder: (_) => const HomeScreen()),
      );
    } on ApiException catch (error) {
      // El backend respondió con un error (ej: "Usuario o clave incorrectos").
      setState(() => _errorMessage = error.message);
    } catch (_) {
      // No hubo respuesta: sin red, backend apagado o IP equivocada.
      setState(() => _errorMessage = 'No se pudo conectar con el servidor');
    } finally {
      // `finally` se ejecuta siempre, haya salido bien o mal.
      if (mounted) setState(() => _loading = false);
    }
  }

  // dispose se ejecuta al cerrar la pantalla: libera los controladores de
  // texto para no dejar memoria ocupada.
  @override
  void dispose() {
    _usuarioController.dispose();
    _claveController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      // SafeArea evita que el contenido quede bajo el notch o la barra de estado.
      body: SafeArea(
        child: Center(
          // Permite hacer scroll cuando el teclado tapa parte de la pantalla.
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
            // Ancho máximo, para que en tablets o navegador no se estire.
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 380),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  _Brand(),
                  const SizedBox(height: 32),
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.fromLTRB(24, 28, 24, 24),
                      child: Form(
                        key: _formKey,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            Text(
                              'Iniciar sesión',
                              style: Theme.of(context).textTheme.headlineMedium,
                              textAlign: TextAlign.center,
                            ),
                            const SizedBox(height: 4),
                            Text(
                              'Ingresa con tu cuenta de operador',
                              style: Theme.of(context).textTheme.bodyMedium,
                              textAlign: TextAlign.center,
                            ),
                            const SizedBox(height: 28),
                            // Campo de usuario. `validator` devuelve el texto
                            // del error, o null si el valor es válido.
                            TextFormField(
                              controller: _usuarioController,
                              decoration: const InputDecoration(
                                labelText: 'Usuario (email)',
                                prefixIcon: Icon(Icons.person_outline),
                              ),
                              keyboardType: TextInputType.emailAddress,
                              validator: (value) =>
                                  (value == null || value.trim().length < 3) ? 'Ingresa tu usuario' : null,
                            ),
                            const SizedBox(height: 14),
                            // Campo de clave: obscureText la muestra como puntos.
                            TextFormField(
                              controller: _claveController,
                              decoration: const InputDecoration(
                                labelText: 'Clave',
                                prefixIcon: Icon(Icons.lock_outline),
                              ),
                              obscureText: true,
                              validator: (value) => (value == null || value.isEmpty) ? 'Ingresa tu clave' : null,
                            ),
                            const SizedBox(height: 20),
                            // Banner de error: solo aparece si hay mensaje.
                            if (_errorMessage != null)
                              Container(
                                width: double.infinity,
                                margin: const EdgeInsets.only(bottom: 16),
                                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                                decoration: BoxDecoration(
                                  color: const Color(0xFFF6D9D9),
                                  borderRadius: BorderRadius.circular(10),
                                ),
                                child: Row(
                                  children: [
                                    const Icon(Icons.error_outline, color: AppColors.error, size: 20),
                                    const SizedBox(width: 10),
                                    Expanded(
                                      child: Text(
                                        _errorMessage!,
                                        style: const TextStyle(color: AppColors.error),
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            // Mientras carga, el botón se desactiva (onPressed
                            // null) y muestra una ruedita en vez del texto, para
                            // evitar enviar el login dos veces.
                            FilledButton(
                              onPressed: _loading ? null : _handleLogin,
                              child: _loading
                                  ? const SizedBox(
                                      width: 20,
                                      height: 20,
                                      child: CircularProgressIndicator(
                                        strokeWidth: 2,
                                        color: AppColors.black,
                                      ),
                                    )
                                  : const Text('Ingresar'),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// Logo real de la marca (ya trae el wordmark "Kill Bichos / Control de
/// plagas" dibujado en la imagen, así que no se repite el texto debajo).
class _Brand extends StatelessWidget {
  const _Brand();

  @override
  Widget build(BuildContext context) {
    // ClipRRect recorta la imagen con esquinas redondeadas; el Container le
    // agrega una sombra suave.
    return ClipRRect(
      borderRadius: BorderRadius.circular(20),
      child: Container(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(20),
          boxShadow: [
            BoxShadow(
              color: AppColors.black.withValues(alpha: 0.12),
              blurRadius: 16,
              offset: const Offset(0, 6),
            ),
          ],
        ),
        // La imagen está registrada en pubspec.yaml (sección assets).
        child: Image.asset(
          'assets/images/logo.png',
          width: 140,
          height: 140,
          fit: BoxFit.cover,
        ),
      ),
    );
  }
}
