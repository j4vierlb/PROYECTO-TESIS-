// =============================================================================
// screens/croquis_screen.dart — Croquis de una visita (trampas instaladas)
// -----------------------------------------------------------------------------
// Pide el croquis al backend (GET /croquis/{visita_id}) y muestra sus trampas:
//   - Lista: cada trampa con su estado y los botones Confirmar / Retirar.
//   - Mapa (opcional): pines de colores que se pueden arrastrar para mover una
//     trampa. Solo aparece si se compiló con MAPS_ENABLED=true (necesita la
//     API key de Google Maps; sin ella la app se cae al dibujar el mapa).
// Si la visita está completada (readOnly), todo es solo de consulta.
// =============================================================================

import 'package:flutter/material.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';

import '../config/app_config.dart';
import '../models/croquis.dart';
import '../services/api_client.dart';
import '../theme/app_theme.dart';

class CroquisScreen extends StatefulWidget {
  final String visitaId;
  // Coordenadas del cliente, usadas para centrar el mapa si el croquis
  // todavía no tiene dispositivos ubicados.
  final double? clienteLat;
  final double? clienteLng;
  // En una visita ya completada el croquis es solo de consulta: no se
  // pueden confirmar, mover ni retirar trampas.
  final bool readOnly;

  const CroquisScreen({
    super.key,
    required this.visitaId,
    this.clienteLat,
    this.clienteLng,
    this.readOnly = false,
  });

  @override
  State<CroquisScreen> createState() => _CroquisScreenState();
}

class _CroquisScreenState extends State<CroquisScreen> {
  final _apiClient = ApiClient();

  Croquis? _croquis; // null mientras no ha cargado
  String? _loadError;
  // true si el backend respondió 404: la visita todavía no tiene croquis
  // (pasa con las visitas agendadas por WhatsApp). No es un error de red,
  // así que no tiene sentido ofrecer "Reintentar".
  bool _sinCroquis = false;
  bool _loading = true;
  // Id del dispositivo que se está actualizando (para mostrar el progreso).
  String? _updatingId;
  bool _showMap = false; // false = pestaña Lista, true = pestaña Mapa
  // Se incrementa para reconstruir el mapa y devolver un pin a su lugar
  // si el operador cancela un movimiento.
  int _mapVersion = 0;

  @override
  void initState() {
    super.initState();
    _load();
  }

  /// Pide el croquis al backend.
  Future<void> _load() async {
    setState(() {
      _loading = true;
      _loadError = null;
      _sinCroquis = false;
    });
    try {
      final croquis = await _apiClient.fetchCroquis(widget.visitaId);
      if (!mounted) return;
      setState(() => _croquis = croquis);
    } on ApiException catch (error) {
      if (mounted) {
        setState(() {
          _loadError = error.message;
          _sinCroquis = error.statusCode == 404;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _loadError = 'No se pudo cargar el croquis');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  /// Ejecuta una acción sobre una trampa y reemplaza esa trampa en la lista
  /// con la versión actualizada que devuelve el backend.
  Future<void> _actualizarDispositivo(
    DispositivoTrampa dispositivo,
    String accion, {
    double? lat,
    double? lng,
    required String mensajeOk,
  }) async {
    setState(() => _updatingId = dispositivo.id);
    try {
      final actualizado = await _apiClient.updateDispositivo(dispositivo.id, accion, lat: lat, lng: lng);
      if (!mounted) return;
      final croquis = _croquis!;
      setState(() {
        // Nueva lista: igual a la anterior, pero con la trampa actualizada
        // en lugar de la vieja (se compara por id).
        _croquis = croquis.copyWithDispositivos([
          for (final item in croquis.dispositivos) item.id == actualizado.id ? actualizado : item,
        ]);
        _mapVersion++;
      });
      _mostrarMensaje(mensajeOk);
    } on ApiException catch (error) {
      _mostrarMensaje(error.message);
      // Redibuja el mapa para que un pin movido vuelva a su lugar original.
      if (mounted) setState(() => _mapVersion++);
    } catch (_) {
      _mostrarMensaje('No se pudo conectar con el servidor');
      if (mounted) setState(() => _mapVersion++);
    } finally {
      if (mounted) setState(() => _updatingId = null);
    }
  }

  /// El operador valida en terreno la ubicación que sugirió la IA.
  Future<void> _confirmar(DispositivoTrampa dispositivo) => _actualizarDispositivo(
        dispositivo,
        'confirmar',
        mensajeOk: '${dispositivo.codigo} confirmada',
      );

  /// Retira una trampa (el backend no la borra: la marca como "retirado").
  /// Pide confirmación antes.
  Future<void> _retirar(DispositivoTrampa dispositivo) async {
    final confirmado = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Retirar ${dispositivo.codigo}'),
        content: const Text('La trampa quedará marcada como retirada. ¿Continuar?'),
        actions: [
          TextButton(onPressed: () => Navigator.of(context).pop(false), child: const Text('Cancelar')),
          TextButton(onPressed: () => Navigator.of(context).pop(true), child: const Text('Retirar')),
        ],
      ),
    );
    if (confirmado == true) {
      // 'eliminar' es el nombre de la acción en la API.
      await _actualizarDispositivo(dispositivo, 'eliminar', mensajeOk: '${dispositivo.codigo} retirada');
    }
  }

  /// Se llama al soltar un pin arrastrado en el mapa: pide confirmación y,
  /// si el operador acepta, guarda la nueva posición.
  Future<void> _moverConfirmando(DispositivoTrampa dispositivo, LatLng nuevaPosicion) async {
    final confirmado = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Mover ${dispositivo.codigo}'),
        content: const Text('¿Guardar la nueva ubicación de esta trampa?'),
        actions: [
          TextButton(onPressed: () => Navigator.of(context).pop(false), child: const Text('Cancelar')),
          TextButton(onPressed: () => Navigator.of(context).pop(true), child: const Text('Guardar')),
        ],
      ),
    );
    if (confirmado == true) {
      await _actualizarDispositivo(
        dispositivo,
        'mover',
        lat: nuevaPosicion.latitude,
        lng: nuevaPosicion.longitude,
        mensajeOk: '${dispositivo.codigo} movida',
      );
    } else if (mounted) {
      // Canceló: se redibuja el mapa y el pin vuelve a su posición original.
      setState(() => _mapVersion++);
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
      appBar: AppBar(title: const Text('Croquis')),
      body: _buildBody(context),
    );
  }

  Widget _buildBody(BuildContext context) {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }
    final croquis = _croquis;
    // La visita todavía no tiene croquis (ej: agendada por WhatsApp).
    if (_sinCroquis) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.map_outlined, size: 48, color: AppColors.textSecondary),
              SizedBox(height: 12),
              Text(
                'Esta visita todavía no tiene croquis',
                textAlign: TextAlign.center,
                style: TextStyle(fontWeight: FontWeight.w700, fontSize: 16),
              ),
              SizedBox(height: 6),
              Text(
                'Suele pasar con las visitas agendadas por WhatsApp.',
                textAlign: TextAlign.center,
                style: TextStyle(color: AppColors.textSecondary),
              ),
            ],
          ),
        ),
      );
    }
    // Otro error de carga (sin red, servidor caído): mensaje y botón para
    // reintentar.
    if (_loadError != null || croquis == null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(_loadError ?? 'No se pudo cargar el croquis', textAlign: TextAlign.center),
              const SizedBox(height: 16),
              OutlinedButton(onPressed: _load, child: const Text('Reintentar')),
            ],
          ),
        ),
      );
    }

    return Column(
      children: [
        if (widget.readOnly)
          const _Aviso(texto: 'Visita completada: este croquis es solo de consulta.'),
        // Con mapa habilitado: selector Lista / Mapa. Sin mapa: un aviso.
        if (AppConfig.mapsEnabled)
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
            child: SegmentedButton<bool>(
              segments: const [
                ButtonSegment(value: false, label: Text('Lista'), icon: Icon(Icons.list)),
                ButtonSegment(value: true, label: Text('Mapa'), icon: Icon(Icons.map_outlined)),
              ],
              selected: {_showMap},
              onSelectionChanged: (selection) => setState(() => _showMap = selection.first),
            ),
          )
        else
          _Aviso(
            texto: widget.readOnly
                ? 'El mapa está desactivado (falta la API key de Google Maps).'
                : 'El mapa está desactivado (falta la API key de Google Maps). Puedes gestionar las trampas desde la lista.',
          ),
        // Expanded: la lista o el mapa ocupan todo el espacio restante.
        Expanded(
          child: (AppConfig.mapsEnabled && _showMap) ? _buildMap(croquis) : _buildList(croquis),
        ),
      ],
    );
  }

  /// Vista de lista: una tarjeta por trampa.
  Widget _buildList(Croquis croquis) {
    if (croquis.dispositivos.isEmpty) {
      return const Center(child: Text('Este croquis aún no tiene trampas'));
    }
    return ListView.builder(
      padding: const EdgeInsets.symmetric(vertical: 8),
      itemCount: croquis.dispositivos.length,
      itemBuilder: (context, index) {
        final dispositivo = croquis.dispositivos[index];
        return _DispositivoCard(
          dispositivo: dispositivo,
          tipoLabel: _tipoLabel(dispositivo.tipo),
          updating: _updatingId == dispositivo.id,
          readOnly: widget.readOnly,
          onConfirmar: () => _confirmar(dispositivo),
          onRetirar: () => _retirar(dispositivo),
        );
      },
    );
  }

  /// Vista de mapa: un pin por trampa (requiere la API key de Google Maps).
  Widget _buildMap(Croquis croquis) {
    return GoogleMap(
      // Cambiar la key obliga a Flutter a reconstruir el mapa desde cero.
      key: ValueKey(_mapVersion),
      // zoom 18 = nivel de detalle de calle/edificio.
      initialCameraPosition: CameraPosition(target: _centerFor(croquis.dispositivos), zoom: 18),
      markers: {
        for (final dispositivo in croquis.dispositivos)
          Marker(
            markerId: MarkerId(dispositivo.id),
            position: LatLng(dispositivo.lat, dispositivo.lng),
            icon: BitmapDescriptor.defaultMarkerWithHue(_markerHue(dispositivo)),
            // Solo se pueden mover las trampas que siguen activas.
            draggable: !widget.readOnly && dispositivo.estado != 'retirado',
            onDragEnd: (posicion) => _moverConfirmando(dispositivo, posicion),
            // Globo que aparece al tocar el pin.
            infoWindow: InfoWindow(
              title: '${dispositivo.codigo} · ${_tipoLabel(dispositivo.tipo)}',
              snippet: _estadoTexto(dispositivo),
            ),
          ),
      },
    );
  }

  /// Verde = confirmada por el operador, amarillo = sugerencia de la IA
  /// todavía sin confirmar, morado = retirada.
  double _markerHue(DispositivoTrampa dispositivo) {
    if (dispositivo.estado == 'retirado') return BitmapDescriptor.hueViolet;
    if (dispositivo.confirmado) return BitmapDescriptor.hueGreen;
    return BitmapDescriptor.hueYellow;
  }

  /// Texto del globo del pin según el estado de la trampa.
  String _estadoTexto(DispositivoTrampa dispositivo) {
    if (dispositivo.estado == 'retirado') return 'Retirada';
    return dispositivo.confirmado ? 'Confirmada' : 'Sugerida por IA · sin confirmar';
  }

  /// Nombre legible del tipo de trampa ("trampa_luz" -> "Trampa de luz").
  String _tipoLabel(String tipo) => switch (tipo) {
        'cebadero' => 'Cebadero',
        'trampa_pegamento' => 'Trampa de pegamento',
        'trampa_luz' => 'Trampa de luz',
        _ => 'Otro',
      };

  /// Punto donde se centra el mapa: el promedio de las trampas; si no hay,
  /// la ubicación del cliente; y si tampoco, un punto por defecto.
  LatLng _centerFor(List<DispositivoTrampa> dispositivos) {
    if (dispositivos.isNotEmpty) {
      final avgLat = dispositivos.map((d) => d.lat).reduce((a, b) => a + b) / dispositivos.length;
      final avgLng = dispositivos.map((d) => d.lng).reduce((a, b) => a + b) / dispositivos.length;
      return LatLng(avgLat, avgLng);
    }
    if (widget.clienteLat != null && widget.clienteLng != null) {
      return LatLng(widget.clienteLat!, widget.clienteLng!);
    }
    // Centro por defecto: Macul, Santiago (zona de operación de la empresa).
    return const LatLng(-33.4869, -70.5989);
  }
}

/// Tarjeta de una trampa en la vista de lista.
class _DispositivoCard extends StatelessWidget {
  final DispositivoTrampa dispositivo;
  final String tipoLabel;
  final bool updating; // true mientras se guarda un cambio de esta trampa
  final bool readOnly;
  // VoidCallback = función sin parámetros que se llama al tocar el botón.
  final VoidCallback onConfirmar;
  final VoidCallback onRetirar;

  const _DispositivoCard({
    required this.dispositivo,
    required this.tipoLabel,
    required this.updating,
    required this.readOnly,
    required this.onConfirmar,
    required this.onRetirar,
  });

  @override
  Widget build(BuildContext context) {
    final retirada = dispositivo.estado == 'retirado';
    // Etiqueta y colores del badge según el estado. Se asignan las tres
    // variables de una vez (un "record" de Dart).
    final (String etiqueta, Color fondo, Color texto) = retirada
        ? ('Retirada', const Color(0xFFECECE6), AppColors.textSecondary)
        : dispositivo.confirmado
            ? ('Confirmada', const Color(0xFFDCEFDC), const Color(0xFF2E7D32))
            : ('Sin confirmar', AppColors.yellow, AppColors.black);

    return Card(
      // Una trampa retirada se ve más tenue.
      child: Opacity(
        opacity: retirada ? 0.6 : 1,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      '${dispositivo.codigo} · $tipoLabel',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(color: fondo, borderRadius: BorderRadius.circular(20)),
                    child: Text(
                      etiqueta,
                      style: TextStyle(color: texto, fontWeight: FontWeight.w700, fontSize: 11),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 4),
              Text(
                dispositivo.sugeridoPorIa ? 'Ubicación sugerida por la IA' : 'Ubicación definida por el operador',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              // Botones solo si la trampa sigue activa y la visita no está
              // completada.
              if (!retirada && !readOnly) ...[
                const SizedBox(height: 12),
                if (updating)
                  const Center(
                    child: SizedBox(width: 24, height: 24, child: CircularProgressIndicator(strokeWidth: 2)),
                  )
                else
                  Row(
                    children: [
                      // "Confirmar" solo aparece si aún no está confirmada.
                      if (!dispositivo.confirmado)
                        Expanded(
                          child: FilledButton.icon(
                            onPressed: onConfirmar,
                            icon: const Icon(Icons.check, size: 18),
                            label: const Text('Confirmar'),
                            style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(44)),
                          ),
                        ),
                      if (!dispositivo.confirmado) const SizedBox(width: 10),
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: onRetirar,
                          icon: const Icon(Icons.delete_outline, size: 18),
                          label: const Text('Retirar'),
                          style: OutlinedButton.styleFrom(minimumSize: const Size.fromHeight(44)),
                        ),
                      ),
                    ],
                  ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

/// Franja informativa amarilla suave, usada para los avisos del croquis.
class _Aviso extends StatelessWidget {
  final String texto;

  const _Aviso({required this.texto});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.fromLTRB(16, 12, 16, 4),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.yellow.withValues(alpha: 0.18),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Text(texto, style: const TextStyle(fontSize: 13)),
    );
  }
}
