// =============================================================================
// widgets/sync_banner.dart — Franja con el estado de la conexión
// -----------------------------------------------------------------------------
// Aparece arriba de cualquier pantalla solo cuando hay algo que decir:
//   - sin conexión (se trabaja con lo guardado en el teléfono)
//   - cambios guardados que todavía no se enviaron (con contador)
//   - enviando
//   - cambios que el servidor no aceptó (se muestran una vez y se descartan)
// =============================================================================

import 'package:flutter/material.dart';

import '../offline/sync_service.dart';
import '../theme/app_theme.dart';

class SyncBanner extends StatelessWidget {
  final SyncService? sync;

  const SyncBanner({super.key, this.sync});

  /// "1 cambio" / "3 cambios".
  static String cambios(int n) => n == 1 ? '1 cambio' : '$n cambios';

  @override
  Widget build(BuildContext context) {
    final service = sync ?? SyncService.shared;
    return ValueListenableBuilder<SyncStatus>(
      valueListenable: service.status,
      builder: (context, status, _) {
        if (!status.visible) return const SizedBox.shrink();
        return _contenido(context, service, status);
      },
    );
  }

  Widget _contenido(BuildContext context, SyncService service, SyncStatus status) {
    final hayConflictos = status.conflicts.isNotEmpty;
    final Color fondo = hayConflictos
        ? AppColors.error
        : status.offline
            ? AppColors.black
            : AppColors.yellow;
    final Color texto = hayConflictos || status.offline ? Colors.white : AppColors.black;

    String mensaje;
    if (hayConflictos) {
      mensaje = status.conflicts.join(' ');
    } else if (status.syncing) {
      mensaje = 'Enviando cambios…';
    } else if (status.offline) {
      mensaje = status.pending > 0
          ? 'Sin conexión · ${cambios(status.pending)} por enviar'
          : 'Sin conexión · usando los datos guardados';
    } else {
      mensaje = '${cambios(status.pending)} por enviar';
    }

    return Material(
      color: fondo,
      child: SafeArea(
        bottom: false,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: Row(
            children: [
              Icon(
                hayConflictos
                    ? Icons.error_outline
                    : status.offline
                        ? Icons.cloud_off_outlined
                        : Icons.sync,
                size: 18,
                color: texto,
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  mensaje,
                  style: TextStyle(color: texto, fontSize: 13, fontWeight: FontWeight.w600),
                ),
              ),
              if (hayConflictos)
                TextButton(
                  style: TextButton.styleFrom(foregroundColor: texto, visualDensity: VisualDensity.compact),
                  onPressed: service.dismissConflicts,
                  child: const Text('Entendido'),
                )
              else if (status.pending > 0 && !status.syncing)
                TextButton(
                  style: TextButton.styleFrom(foregroundColor: texto, visualDensity: VisualDensity.compact),
                  onPressed: () => service.flush(),
                  child: const Text('Enviar ahora'),
                ),
            ],
          ),
        ),
      ),
    );
  }
}
