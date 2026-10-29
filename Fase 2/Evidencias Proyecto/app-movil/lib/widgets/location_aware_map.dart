import 'package:flutter/material.dart';

import '../theme/app_theme.dart';

/// No crea la vista nativa del mapa si no existe ningún punto real que mostrar.
class LocationAwareMap extends StatelessWidget {
  final bool clientLocated;
  final bool trapsLocated;
  final WidgetBuilder mapBuilder;

  const LocationAwareMap({
    super.key,
    required this.clientLocated,
    required this.trapsLocated,
    required this.mapBuilder,
  });

  @override
  Widget build(BuildContext context) {
    if (!clientLocated && !trapsLocated) {
      return Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: const Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.location_off_outlined,
                size: 48,
                color: AppColors.textSecondary,
              ),
              SizedBox(height: 16),
              Text(
                'Sin ubicación registrada',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
              ),
              SizedBox(height: 12),
              Text(
                'La ubicación del cliente está pendiente de confirmar y no hay trampas ubicadas. '
                'No se muestra un mapa para evitar indicar un lugar incorrecto.\n\n'
                'Corrige calle, número y comuna en el panel, guarda y vuelve a abrir esta visita con conexión.',
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      );
    }
    return Column(
      children: [
        if (!clientLocated)
          Semantics(
            liveRegion: true,
            child: Container(
              width: double.infinity,
              color: const Color(0xFFFFF5CE),
              padding: const EdgeInsets.all(12),
              child: const Text(
                'Ubicación del cliente pendiente de confirmar. '
                'El mapa muestra únicamente las trampas registradas, no la dirección del cliente.',
                style: TextStyle(color: Color(0xFF6B4E00)),
              ),
            ),
          ),
        Expanded(child: mapBuilder(context)),
      ],
    );
  }
}
