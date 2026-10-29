// =============================================================================
// screens/proximas_screen.dart — Visitas de los próximos días (pestaña "Próximas")
// -----------------------------------------------------------------------------
// La agenda del día solo muestra hoy. Aquí el técnico ve las visitas pendientes
// de los días siguientes, agrupadas por día ("Mañana", "Pasado mañana", "Lunes 2
// de noviembre"...). Al tocar una se abre su detalle. Tirando hacia abajo se
// recarga la lista. Sin señal muestra la última lista guardada.
// =============================================================================

import 'package:flutter/material.dart';

import '../models/visita.dart';
import '../offline/offline_api_client.dart';
import '../services/api_client.dart';
import '../theme/app_theme.dart';
import '../utils/formato.dart';
import '../widgets/company_brand.dart';
import '../widgets/logout_button.dart';
import '../widgets/visita_card.dart';

class ProximasScreen extends StatefulWidget {
  // Solo para pruebas; en la app se usa el cliente con modo offline.
  final ApiClient? apiClient;
  // Solo para pruebas: qué día es "hoy" al poner las etiquetas.
  final DateTime? hoy;

  const ProximasScreen({super.key, this.apiClient, this.hoy});

  @override
  State<ProximasScreen> createState() => _ProximasScreenState();
}

class _ProximasScreenState extends State<ProximasScreen> {
  late final ApiClient _apiClient = widget.apiClient ?? OfflineApiClient.shared;
  late Future<List<Visita>> _visitasFuture;

  @override
  void initState() {
    super.initState();
    _visitasFuture = _apiClient.fetchVisitasProximas();
  }

  /// Vuelve a pedir la lista (pull-to-refresh o al volver con cambios).
  Future<void> _refresh() async {
    final future = _apiClient.fetchVisitasProximas();
    setState(() => _visitasFuture = future);
    await future;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const CompanyTitle('Próximas visitas'),
        actions: const [LogoutButton()],
      ),
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: FutureBuilder<List<Visita>>(
          future: _visitasFuture,
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snapshot.hasError) {
              final message = snapshot.error is ApiException
                  ? (snapshot.error as ApiException).message
                  : 'No se pudieron cargar las próximas visitas';
              return _ScrollableMessage(message: message);
            }
            final visitas = snapshot.data ?? const <Visita>[];
            if (visitas.isEmpty) {
              return const _ScrollableMessage(
                message: 'No tienes visitas agendadas para los próximos días',
              );
            }
            return ListView(
              padding: const EdgeInsets.symmetric(vertical: 12),
              children: _conEncabezados(visitas),
            );
          },
        ),
      ),
    );
  }

  /// Las visitas vienen ordenadas por fecha: cada vez que cambia el día se
  /// intercala un encabezado con su etiqueta.
  List<Widget> _conEncabezados(List<Visita> visitas) {
    final widgets = <Widget>[];
    String? diaAnterior;
    for (final visita in visitas) {
      final dia = etiquetaDia(visita.fechaHora, hoy: widget.hoy);
      if (dia != diaAnterior) {
        widgets.add(_EncabezadoDia(texto: dia));
        diaAnterior = dia;
      }
      widgets.add(VisitaCard(
        visita: visita,
        horaFormateada: formatHora(visita.fechaHora),
        onVolverConCambios: _refresh,
        apiClient: widget.apiClient,
      ));
    }
    return widgets;
  }
}

/// Título de cada grupo de visitas ("Mañana", "Lunes 2 de noviembre").
class _EncabezadoDia extends StatelessWidget {
  final String texto;

  const _EncabezadoDia({required this.texto});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 4),
      child: Text(
        texto,
        style: Theme.of(context).textTheme.titleSmall?.copyWith(
              color: AppColors.textSecondary,
              fontWeight: FontWeight.w700,
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
