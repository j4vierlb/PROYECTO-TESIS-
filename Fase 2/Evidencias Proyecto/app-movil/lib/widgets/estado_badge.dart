// =============================================================================
// widgets/estado_badge.dart — Etiqueta de color con el estado de una visita
// =============================================================================

import 'package:flutter/material.dart';

import '../theme/app_theme.dart';

/// Badge de estado de una visita (agendada/en_curso/completada/...),
/// reutilizado en la agenda y en el detalle de la visita.
class EstadoBadge extends StatelessWidget {
  final String estado;

  const EstadoBadge({super.key, required this.estado});

  @override
  Widget build(BuildContext context) {
    // Una "píldora" (esquinas muy redondeadas) con el color según el estado,
    // tomado de EstadoColors en app_theme.dart.
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: EstadoColors.background(estado),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text(
        EstadoColors.label(estado), // "en_curso" se muestra como "En curso"
        style: TextStyle(
          color: EstadoColors.foreground(estado),
          fontWeight: FontWeight.w700,
          fontSize: 11,
        ),
      ),
    );
  }
}
