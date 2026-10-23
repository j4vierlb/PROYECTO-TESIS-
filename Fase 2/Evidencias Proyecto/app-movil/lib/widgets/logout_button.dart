// =============================================================================
// widgets/logout_button.dart — Botón "Cerrar sesión" de la barra superior
// =============================================================================

import 'package:flutter/material.dart';

import '../screens/login_screen.dart';
import '../services/auth_storage.dart';
import '../services/pending_photo.dart';

/// Botón de la barra superior que borra los tokens guardados y vuelve al
/// login, sin dejar pantallas anteriores en el historial de navegación.
class LogoutButton extends StatelessWidget {
  const LogoutButton({super.key});

  Future<void> _logout(BuildContext context) async {
    try {
      final pending = await PendingPhotoStore.instance.read();
      if (!context.mounted) return;
      if (pending != null) {
        final confirmed = await showDialog<bool>(
          context: context,
          builder: (dialogContext) => AlertDialog(
            title: const Text('Foto sin enviar'),
            content: const Text(
              'Cerrar sesión descartará el envío pendiente, no la imagen original. Puedes volver al croquis para reintentarlo.',
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(dialogContext, false),
                child: const Text('Volver'),
              ),
              TextButton(
                onPressed: () => Navigator.pop(dialogContext, true),
                child: const Text('Salir y descartar'),
              ),
            ],
          ),
        );
        if (confirmed != true) return;
      }
      await AuthStorage.instance.clear(manualLogout: true);
    } catch (_) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('No se pudo cerrar sesión. Reintenta.')),
        );
      }
      return;
    }
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
