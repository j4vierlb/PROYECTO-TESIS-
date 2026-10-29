// =============================================================================
// widgets/visita_card.dart — Tarjeta de una visita en las listas
// =============================================================================

import 'package:flutter/material.dart';

import '../models/visita.dart';
import '../screens/visita_detalle_screen.dart';
import '../services/api_client.dart';
import '../theme/app_theme.dart';
import 'estado_badge.dart';

/// Tarjeta de una visita en las listas (hoy y próximas): cliente, hora,
/// dirección y estado. Al tocarla se abre el detalle.
class VisitaCard extends StatelessWidget {
  final Visita visita;
  final String horaFormateada;
  // Función que la lista le pasa para recargarse si hubo cambios.
  final Future<void> Function() onVolverConCambios;
  // Solo para pruebas: cliente de API que usará el detalle.
  final ApiClient? apiClient;

  const VisitaCard({
    super.key,
    required this.visita,
    required this.horaFormateada,
    required this.onVolverConCambios,
    this.apiClient,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      // InkWell hace que la tarjeta se pueda tocar (con efecto visual).
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: () async {
          // El detalle devuelve true si el operador cambió algo (estado o
          // notas); en ese caso se recarga la agenda.
          final huboCambios = await Navigator.of(context).push<bool>(
            MaterialPageRoute(
              builder: (_) => VisitaDetalleScreen(visitaId: visita.id, apiClient: apiClient),
            ),
          );
          if (huboCambios == true) {
            await onVolverConCambios();
          }
        },
        child: Padding(
          padding: const EdgeInsets.all(16),
          // Row = elementos uno al lado del otro; Column = uno debajo del otro.
          child: Row(
            children: [
              // Franja horaria destacada a la izquierda.
              Container(
                width: 4,
                height: 48,
                decoration: BoxDecoration(
                  color: AppColors.yellow,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
              const SizedBox(width: 14),
              // Expanded ocupa todo el ancho que sobra en la fila.
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            visita.cliente.nombre,
                            style: Theme.of(context).textTheme.titleMedium,
                            // Si el nombre es muy largo, termina en "...".
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        Text(
                          horaFormateada,
                          style: const TextStyle(fontWeight: FontWeight.w700, color: AppColors.textPrimary),
                        ),
                      ],
                    ),
                    const SizedBox(height: 4),
                    Text(
                      visita.cliente.direccionTexto,
                      style: Theme.of(context).textTheme.bodyMedium,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 10),
                    EstadoBadge(estado: visita.estado),
                  ],
                ),
              ),
              const SizedBox(width: 4),
              const Icon(Icons.chevron_right, color: AppColors.textSecondary),
            ],
          ),
        ),
      ),
    );
  }
}
