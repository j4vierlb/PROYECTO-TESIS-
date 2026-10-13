// =============================================================================
// screens/visita_detalle_screen.dart — Detalle de una visita
// -----------------------------------------------------------------------------
// Muestra los datos de la visita (cliente, dirección, hora, notas) y las
// acciones del operador según el estado:
//   agendada   -> botón "Iniciar visita"   (pasa a en_curso)
//   en_curso   -> botón "Completar visita" (pasa a completada, con confirmación)
//   completada -> solo consulta: sin editar notas y con el croquis en lectura
// Además: "Editar notas" y "Ver croquis".
// =============================================================================

import 'package:flutter/material.dart';

import '../models/visita.dart';
import '../services/api_client.dart';
import '../theme/app_theme.dart';
import '../utils/formato.dart';
import '../widgets/estado_badge.dart';
import 'croquis_screen.dart';

class VisitaDetalleScreen extends StatefulWidget {
  // Id de la visita a mostrar; la pantalla la pide al backend al abrirse.
  final String visitaId;

  const VisitaDetalleScreen({super.key, required this.visitaId});

  @override
  State<VisitaDetalleScreen> createState() => _VisitaDetalleScreenState();
}

class _VisitaDetalleScreenState extends State<VisitaDetalleScreen> {
  final _apiClient = ApiClient();

  Visita? _visita; // null mientras no ha cargado
  String? _loadError;
  bool _loading = true; // cargando la visita
  bool _saving = false; // guardando un cambio (estado o notas)
  // Si algo cambió, al volver la agenda se recarga.
  bool _changed = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  /// Pide la visita al backend (GET /visitas/{id}).
  Future<void> _load() async {
    setState(() {
      _loading = true;
      _loadError = null;
    });
    try {
      final visita = await _apiClient.fetchVisita(widget.visitaId);
      if (!mounted) return;
      setState(() => _visita = visita);
    } on ApiException catch (error) {
      if (mounted) setState(() => _loadError = error.message);
    } catch (_) {
      if (mounted) setState(() => _loadError = 'No se pudo cargar la visita');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  /// Envía un cambio al backend (PATCH /visitas/{id}) y actualiza la pantalla
  /// con la visita que devuelve. Lo usan iniciar, completar y editar notas.
  Future<void> _guardar({String? estado, String? notas, String? mensajeOk}) async {
    setState(() => _saving = true);
    try {
      final actualizada = await _apiClient.updateVisita(widget.visitaId, estado: estado, notas: notas);
      if (!mounted) return;
      setState(() {
        _visita = actualizada;
        _changed = true;
      });
      _mostrarMensaje(mensajeOk ?? 'Cambios guardados');
    } on ApiException catch (error) {
      _mostrarMensaje(error.message);
    } catch (_) {
      _mostrarMensaje('No se pudo conectar con el servidor');
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  /// Muestra un mensaje breve en la parte inferior (SnackBar).
  void _mostrarMensaje(String texto) {
    if (!mounted) return;
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(content: Text(texto)));
  }

  Future<void> _iniciarVisita() => _guardar(estado: 'en_curso', mensajeOk: 'Visita iniciada');

  /// Pide confirmación antes de completar, porque una visita completada ya
  /// no se puede editar desde la app.
  Future<void> _completarVisita() async {
    // showDialog abre una ventana emergente y espera la respuesta:
    // true = "Completar", false = "Cancelar", null = cerrada sin elegir.
    final confirmado = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Completar visita'),
        content: const Text('¿Marcar esta visita como completada?'),
        actions: [
          TextButton(onPressed: () => Navigator.of(context).pop(false), child: const Text('Cancelar')),
          TextButton(onPressed: () => Navigator.of(context).pop(true), child: const Text('Completar')),
        ],
      ),
    );
    if (confirmado == true) {
      await _guardar(estado: 'completada', mensajeOk: 'Visita completada');
    }
  }

  /// Abre el diálogo de notas y solo guarda si el texto realmente cambió.
  Future<void> _editarNotas() async {
    final nuevasNotas = await showDialog<String>(
      context: context,
      builder: (context) => _NotasDialog(notasIniciales: _visita?.notas ?? ''),
    );
    if (nuevasNotas != null && nuevasNotas != (_visita?.notas ?? '')) {
      await _guardar(notas: nuevasNotas, mensajeOk: 'Notas guardadas');
    }
  }

  @override
  Widget build(BuildContext context) {
    // PopScope intercepta el botón "atrás" para devolverle a la agenda si
    // hubo cambios (_changed); así la agenda sabe si debe recargarse.
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, result) {
        if (didPop) return;
        Navigator.of(context).pop(_changed);
      },
      child: Scaffold(
        appBar: AppBar(title: const Text('Detalle de visita')),
        body: _buildBody(context),
      ),
    );
  }

  Widget _buildBody(BuildContext context) {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }
    final visita = _visita;
    // Error de carga: mensaje y botón para reintentar.
    if (_loadError != null || visita == null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(_loadError ?? 'No se pudo cargar la visita', textAlign: TextAlign.center),
              const SizedBox(height: 16),
              OutlinedButton(onPressed: _load, child: const Text('Reintentar')),
            ],
          ),
        ),
      );
    }

    final completada = visita.estado == 'completada';

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Tarjeta con los datos de la visita.
          Card(
            margin: EdgeInsets.zero,
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Expanded(
                        child: Text(visita.cliente.nombre, style: Theme.of(context).textTheme.titleLarge),
                      ),
                      EstadoBadge(estado: visita.estado),
                    ],
                  ),
                  const SizedBox(height: 12),
                  _InfoRow(icon: Icons.location_on_outlined, text: visita.cliente.direccionTexto),
                  const SizedBox(height: 8),
                  _InfoRow(icon: Icons.schedule_outlined, text: formatFechaHora(visita.fechaHora)),
                  const SizedBox(height: 8),
                  _InfoRow(icon: Icons.phone_outlined, text: visita.cliente.telefonoWhatsapp),
                  const SizedBox(height: 16),
                  const Divider(),
                  const SizedBox(height: 12),
                  Text('Notas', style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 4),
                  // Sin notas: texto gris "Sin notas"; con notas: texto normal.
                  Text(
                    (visita.notas == null || visita.notas!.isEmpty) ? 'Sin notas' : visita.notas!,
                    style: (visita.notas == null || visita.notas!.isEmpty)
                        ? Theme.of(context).textTheme.bodyMedium
                        : Theme.of(context).textTheme.bodyLarge,
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          // El botón principal depende del estado de la visita. Mientras se
          // guarda (_saving) los botones quedan desactivados.
          if (visita.estado == 'agendada')
            FilledButton.icon(
              onPressed: _saving ? null : _iniciarVisita,
              icon: const Icon(Icons.play_arrow),
              label: const Text('Iniciar visita'),
            ),
          if (visita.estado == 'en_curso')
            FilledButton.icon(
              onPressed: _saving ? null : _completarVisita,
              icon: const Icon(Icons.check),
              label: const Text('Completar visita'),
            ),
          if (visita.estado == 'completada')
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 8),
              child: Text(
                'Esta visita ya está completada',
                textAlign: TextAlign.center,
                style: TextStyle(color: AppColors.textSecondary),
              ),
            ),
          const SizedBox(height: 10),
          // Una visita completada queda como registro: ya no se editan sus notas.
          if (!completada) ...[
            OutlinedButton.icon(
              onPressed: _saving ? null : _editarNotas,
              icon: const Icon(Icons.edit_note),
              label: const Text('Editar notas'),
            ),
            const SizedBox(height: 10),
          ],
          OutlinedButton.icon(
            onPressed: () {
              Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) => CroquisScreen(
                    visitaId: visita.id,
                    clienteLat: visita.cliente.lat,
                    clienteLng: visita.cliente.lng,
                    // Visita completada = croquis solo de consulta.
                    readOnly: completada,
                  ),
                ),
              );
            },
            icon: const Icon(Icons.map_outlined),
            label: const Text('Ver croquis'),
          ),
          if (_saving)
            const Padding(
              padding: EdgeInsets.only(top: 16),
              child: Center(child: CircularProgressIndicator()),
            ),
        ],
      ),
    );
  }
}

/// Fila con un ícono gris y un texto (dirección, hora, teléfono).
class _InfoRow extends StatelessWidget {
  final IconData icon;
  final String text;

  const _InfoRow({required this.icon, required this.text});

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, size: 20, color: AppColors.textSecondary),
        const SizedBox(width: 10),
        Expanded(child: Text(text, style: Theme.of(context).textTheme.bodyLarge)),
      ],
    );
  }
}

/// Diálogo para editar las notas. Tiene su propio controller para liberarlo
/// correctamente al cerrarse.
class _NotasDialog extends StatefulWidget {
  final String notasIniciales;

  const _NotasDialog({required this.notasIniciales});

  @override
  State<_NotasDialog> createState() => _NotasDialogState();
}

class _NotasDialogState extends State<_NotasDialog> {
  // El campo empieza con las notas actuales para poder editarlas.
  late final TextEditingController _controller = TextEditingController(text: widget.notasIniciales);

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Notas de la visita'),
      content: TextField(
        controller: _controller,
        autofocus: true, // abre el teclado de inmediato
        minLines: 3,
        maxLines: 6,
        textCapitalization: TextCapitalization.sentences, // mayúscula al empezar
        decoration: const InputDecoration(hintText: 'Escribe tus observaciones'),
      ),
      actions: [
        // Cancelar devuelve null (no se guarda nada).
        TextButton(onPressed: () => Navigator.of(context).pop(), child: const Text('Cancelar')),
        // Guardar devuelve el texto, sin espacios sobrantes al inicio o al final.
        TextButton(
          onPressed: () => Navigator.of(context).pop(_controller.text.trim()),
          child: const Text('Guardar'),
        ),
      ],
    );
  }
}
