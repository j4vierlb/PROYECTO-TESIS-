// =============================================================================
// screens/agenda_screen.dart — Agenda del día (pestaña "Hoy")
// -----------------------------------------------------------------------------
// Pide al backend las visitas de hoy del operador (GET
// /operadores/me/visitas-hoy) y las muestra como tarjetas. Al tocar una se
// abre su detalle. Tirando hacia abajo se recarga la lista.
// =============================================================================

import 'package:flutter/material.dart';

import '../models/visita.dart';
import '../services/api_client.dart';
import '../theme/app_theme.dart';
import '../utils/formato.dart';
import '../widgets/estado_badge.dart';
import '../widgets/logout_button.dart';
import 'visita_detalle_screen.dart';

class AgendaScreen extends StatefulWidget {
  const AgendaScreen({super.key});

  @override
  State<AgendaScreen> createState() => _AgendaScreenState();
}

class _AgendaScreenState extends State<AgendaScreen> {
  final _apiClient = ApiClient();
  // Un Future es un resultado que llegará más adelante (la respuesta del
  // backend). `late` = se asigna en initState, antes de usarse.
  late Future<List<Visita>> _visitasFuture;

  // initState se ejecuta una sola vez, al abrir la pantalla.
  @override
  void initState() {
    super.initState();
    _visitasFuture = _apiClient.fetchVisitasHoy();
  }

  /// Vuelve a pedir la agenda (pull-to-refresh o al volver con cambios).
  Future<void> _refresh() async {
    final future = _apiClient.fetchVisitasHoy();
    setState(() => _visitasFuture = future);
    await future;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Agenda del día'),
        actions: const [LogoutButton()],
      ),
      // RefreshIndicator = el gesto de "tirar hacia abajo para recargar".
      body: RefreshIndicator(
        onRefresh: _refresh,
        // FutureBuilder redibuja la pantalla según el estado del Future:
        // cargando, con error, o con los datos listos.
        child: FutureBuilder<List<Visita>>(
          future: _visitasFuture,
          builder: (context, snapshot) {
            // 1) Todavía esperando la respuesta: ruedita de carga.
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            }

            // 2) Falló: se muestra el mensaje del backend si lo hay.
            if (snapshot.hasError) {
              final message =
                  snapshot.error is ApiException ? (snapshot.error as ApiException).message : 'No se pudo cargar la agenda';
              return _ScrollableMessage(message: message);
            }

            // 3) Llegaron los datos (puede ser una lista vacía).
            final visitas = snapshot.data ?? const <Visita>[];
            if (visitas.isEmpty) {
              return const _ScrollableMessage(message: 'No tienes visitas agendadas para hoy');
            }

            // ListView.builder crea las tarjetas a medida que se ven en
            // pantalla (eficiente aunque haya muchas visitas).
            return ListView.builder(
              padding: const EdgeInsets.symmetric(vertical: 12),
              itemCount: visitas.length,
              itemBuilder: (context, index) => _VisitaCard(
                visita: visitas[index],
                horaFormateada: formatHora(visitas[index].fechaHora),
                onVolverConCambios: _refresh,
              ),
            );
          },
        ),
      ),
    );
  }
}

/// Tarjeta de una visita en la agenda: cliente, hora, dirección y estado.
class _VisitaCard extends StatelessWidget {
  final Visita visita;
  final String horaFormateada;
  // Función que la agenda le pasa para recargarse si hubo cambios.
  final Future<void> Function() onVolverConCambios;

  const _VisitaCard({
    required this.visita,
    required this.horaFormateada,
    required this.onVolverConCambios,
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
            MaterialPageRoute(builder: (_) => VisitaDetalleScreen(visitaId: visita.id)),
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

/// Mensaje centrado dentro de un ListView, para que RefreshIndicator
/// (pull-to-refresh) funcione incluso cuando la lista está vacía o hubo error.
class _ScrollableMessage extends StatelessWidget {
  final String message;

  const _ScrollableMessage({required this.message});

  @override
  Widget build(BuildContext context) {
    return ListView(
      children: [
        Padding(
          padding: const EdgeInsets.all(24),
          child: Text(message, textAlign: TextAlign.center),
        ),
      ],
    );
  }
}
