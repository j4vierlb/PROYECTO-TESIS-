// =============================================================================
// screens/historial_screen.dart — Historial de visitas (pestaña "Historial")
// -----------------------------------------------------------------------------
// Lista las visitas que el operador ya completó (GET
// /operadores/me/visitas-historial). Las pide por páginas de 20 y muestra un
// botón "Cargar más" al final. Al tocar una se abre su detalle, y desde ahí
// su croquis en modo solo lectura.
// =============================================================================

import 'package:flutter/material.dart';

import '../models/visita.dart';
import '../services/api_client.dart';
import '../theme/app_theme.dart';
import '../utils/formato.dart';
import '../widgets/logout_button.dart';
import 'visita_detalle_screen.dart';

/// Registro de las visitas que el operador ya completó, de la más reciente a
/// la más antigua. Se cargan de a [_pageSize] y se piden más al final.
class HistorialScreen extends StatefulWidget {
  const HistorialScreen({super.key});

  @override
  State<HistorialScreen> createState() => _HistorialScreenState();
}

class _HistorialScreenState extends State<HistorialScreen> {
  static const int _pageSize = 20; // visitas por página

  final _apiClient = ApiClient();
  // Todas las visitas cargadas hasta ahora (se van sumando las páginas).
  final List<Visita> _visitas = [];

  bool _loading = true; // carga inicial (pantalla completa)
  bool _loadingMore = false; // cargando la página siguiente
  bool _hasMore = true; // ¿quedan más visitas por pedir?
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadFirstPage();
  }

  /// Carga (o recarga) la primera página y reemplaza la lista completa.
  Future<void> _loadFirstPage() async {
    setState(() => _error = null);
    try {
      final page = await _apiClient.fetchHistorial(limit: _pageSize);
      if (!mounted) return;
      setState(() {
        _visitas
          ..clear()
          ..addAll(page);
        // Si llegó una página completa, probablemente hay más; si llegó
        // incompleta, ya no queda nada.
        _hasMore = page.length == _pageSize;
      });
    } on ApiException catch (error) {
      if (mounted) setState(() => _error = error.message);
    } catch (_) {
      if (mounted) setState(() => _error = 'No se pudo cargar el historial');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  /// Pide la página siguiente y la agrega al final de la lista.
  Future<void> _loadMore() async {
    // Evita pedir dos veces la misma página si se toca el botón rápido.
    if (_loadingMore || !_hasMore) return;
    setState(() => _loadingMore = true);
    try {
      // offset = cuántas ya tenemos, así el backend entrega las que siguen.
      final page = await _apiClient.fetchHistorial(limit: _pageSize, offset: _visitas.length);
      if (!mounted) return;
      setState(() {
        _visitas.addAll(page);
        _hasMore = page.length == _pageSize;
      });
    } on ApiException catch (error) {
      _mostrarMensaje(error.message);
    } catch (_) {
      _mostrarMensaje('No se pudieron cargar más visitas');
    } finally {
      if (mounted) setState(() => _loadingMore = false);
    }
  }

  /// Muestra un mensaje breve en la parte inferior (SnackBar).
  void _mostrarMensaje(String texto) {
    if (!mounted) return;
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(content: Text(texto)));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Historial de visitas'),
        actions: const [LogoutButton()],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(onRefresh: _loadFirstPage, child: _buildContent(context)),
    );
  }

  Widget _buildContent(BuildContext context) {
    if (_error != null && _visitas.isEmpty) {
      return _ScrollableMessage(message: _error!);
    }
    if (_visitas.isEmpty) {
      return const _ScrollableMessage(message: 'Aún no tienes visitas completadas');
    }

    return ListView.builder(
      padding: const EdgeInsets.symmetric(vertical: 12),
      // Si quedan más visitas, se agrega un elemento extra al final: el botón
      // "Cargar más" (o la ruedita mientras carga).
      itemCount: _visitas.length + (_hasMore ? 1 : 0),
      itemBuilder: (context, index) {
        if (index == _visitas.length) {
          return Padding(
            padding: const EdgeInsets.all(16),
            child: _loadingMore
                ? const Center(child: CircularProgressIndicator())
                : OutlinedButton(onPressed: _loadMore, child: const Text('Cargar más')),
          );
        }
        return _HistorialCard(visita: _visitas[index]);
      },
    );
  }
}

/// Tarjeta de una visita completada: cliente, fecha, trampas y notas.
class _HistorialCard extends StatelessWidget {
  final Visita visita;

  const _HistorialCard({required this.visita});

  /// "1 trampa instalada" o "3 trampas instaladas" (singular/plural).
  String get _trampasTexto {
    final total = visita.dispositivosInstalados ?? 0;
    return total == 1 ? '1 trampa instalada' : '$total trampas instaladas';
  }

  @override
  Widget build(BuildContext context) {
    final notas = visita.notas;
    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        // Abre el detalle; como la visita está completada, el detalle y su
        // croquis se muestran en modo solo lectura.
        onTap: () {
          Navigator.of(context).push(
            MaterialPageRoute(builder: (_) => VisitaDetalleScreen(visitaId: visita.id)),
          );
        },
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Círculo verde con un check: "visita terminada".
              Container(
                width: 40,
                height: 40,
                decoration: const BoxDecoration(color: Color(0xFFDCEFDC), shape: BoxShape.circle),
                child: const Icon(Icons.check, color: Color(0xFF2E7D32), size: 22),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      visita.cliente.nombre,
                      style: Theme.of(context).textTheme.titleMedium,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 2),
                    Text(formatFechaHora(visita.fechaHora), style: Theme.of(context).textTheme.bodyMedium),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        const Icon(Icons.pest_control_outlined, size: 16, color: AppColors.textSecondary),
                        const SizedBox(width: 6),
                        Text(_trampasTexto, style: Theme.of(context).textTheme.bodyMedium),
                      ],
                    ),
                    // Las notas solo se muestran si existen, en máximo 2 líneas.
                    if (notas != null && notas.isNotEmpty) ...[
                      const SizedBox(height: 6),
                      Text(
                        notas,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                    ],
                  ],
                ),
              ),
              const Icon(Icons.chevron_right, color: AppColors.textSecondary),
            ],
          ),
        ),
      ),
    );
  }
}

/// Mensaje dentro de un ListView para que el pull-to-refresh funcione aunque
/// no haya visitas o haya fallado la carga.
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
