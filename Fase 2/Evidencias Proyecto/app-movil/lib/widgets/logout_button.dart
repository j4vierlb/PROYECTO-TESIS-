// =============================================================================
// widgets/logout_button.dart — Botón "Cerrar sesión" de la barra superior
// =============================================================================

import 'package:flutter/material.dart';

import '../screens/login_screen.dart';
import '../offline/sync_service.dart';
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
      // Cambios hechos sin señal que todavía no llegaron al servidor: no se
      // pierden al salir, pero solo se envían al volver a entrar con la misma
      // cuenta, así que se avisa antes.
      final enCola = await SyncService.shared.pendingCount();
      if (!context.mounted) return;
      if (enCola > 0) {
        final salir = await showDialog<bool>(
          context: context,
          builder: (dialogContext) => AlertDialog(
            title: const Text('Cambios sin enviar'),
            content: Text(
              enCola == 1
                  ? 'Tienes 1 cambio guardado en el teléfono que aún no se envía. '
                      'Se conserva y se enviará cuando vuelvas a iniciar sesión con esta cuenta y haya señal.'
                  : 'Tienes $enCola cambios guardados en el teléfono que aún no se envían. '
                      'Se conservan y se enviarán cuando vuelvas a iniciar sesión con esta cuenta y haya señal.',
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(dialogContext, false),
                child: const Text('Volver'),
              ),
              TextButton(
                onPressed: () => Navigator.pop(dialogContext, true),
                child: const Text('Salir de todos modos'),
              ),
            ],
          ),
        );
        if (salir != true) return;
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
