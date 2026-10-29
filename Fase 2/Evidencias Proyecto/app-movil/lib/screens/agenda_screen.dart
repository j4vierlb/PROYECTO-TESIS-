// =============================================================================
// screens/agenda_screen.dart — Agenda del día (pestaña "Hoy")
// -----------------------------------------------------------------------------
// Pide al backend las visitas de hoy del operador (GET
// /operadores/me/visitas-hoy) y las muestra como tarjetas. Al tocar una se
// abre su detalle. Tirando hacia abajo se recarga la lista.
// =============================================================================

import 'package:flutter/material.dart';

import '../models/visita.dart';
import '../offline/offline_api_client.dart';
import '../services/api_client.dart';
import '../utils/formato.dart';
import '../widgets/logout_button.dart';
import '../widgets/visita_card.dart';
import '../widgets/company_brand.dart';

class AgendaScreen extends StatefulWidget {
  const AgendaScreen({super.key});

  @override
  State<AgendaScreen> createState() => _AgendaScreenState();
}

class _AgendaScreenState extends State<AgendaScreen> {
  final _apiClient = OfflineApiClient.shared;
  // Un Future es un resultado que llegará más adelante (la respuesta del
  // backend). `late` = se asigna en initState, antes de usarse.
  late Future<List<Visita>> _visitasFuture;

  // initState se ejecuta una sola vez, al abrir la pantalla.
  @override
  void initState() {
    super.initState();
    _visitasFuture = _apiClient.fetchVisitasHoy();
    _apiClient.sync.status.addListener(_alCambiarConexion);
  }

  @override
  void dispose() {
    _apiClient.sync.status.removeListener(_alCambiarConexion);
    super.dispose();
  }

  // Estaba sin señal y volvió (o terminó de enviar lo pendiente): se recarga la
  // agenda sola para mostrar lo que quedó en el servidor.
  bool _estabaSinSenal = false;
  void _alCambiarConexion() {
    final estado = _apiClient.sync.status.value;
    final recuperada = _estabaSinSenal && !estado.offline && estado.pending == 0 && !estado.syncing;
    _estabaSinSenal = estado.offline || estado.pending > 0;
    if (recuperada && mounted) _refresh();
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
        title: const CompanyTitle('Agenda del día'),
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
              itemBuilder: (context, index) => VisitaCard(
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
