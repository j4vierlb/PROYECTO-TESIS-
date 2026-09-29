// =============================================================================
// widgets/logout_button.dart — Botón "Cerrar sesión" de la barra superior
// =============================================================================

import 'package:flutter/material.dart';

import '../screens/login_screen.dart';
import '../services/auth_storage.dart';

/// Botón de la barra superior que borra los tokens guardados y vuelve al
/// login, sin dejar pantallas anteriores en el historial de navegación.
class LogoutButton extends StatelessWidget {
  const LogoutButton({super.key});

  Future<void> _logout(BuildContext context) async {
    await AuthStorage.instance.clear();
    // Tras un `await` la pantalla podría haberse cerrado; si es así, no se
    // puede navegar desde ella.
    if (!context.mounted) return;
    // pushAndRemoveUntil con (route) => false borra todas las pantallas
    // anteriores: con el botón "atrás" no se puede volver a la agenda.
    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute(builder: (_) => const LoginScreen()),
      (route) => false,
    );
  }

  @override
  Widget build(BuildContext context) {
    return IconButton(
      onPressed: () => _logout(context),
      icon: const Icon(Icons.logout),
      tooltip: 'Cerrar sesión',
    );
  }
}
