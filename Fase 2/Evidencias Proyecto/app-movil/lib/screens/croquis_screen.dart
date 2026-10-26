// =============================================================================
// screens/croquis_screen.dart — Croquis de una visita (trampas instaladas)
// -----------------------------------------------------------------------------
// Pide el croquis al backend (GET /croquis/{visita_id}) y muestra sus trampas.
// Si la visita todavía no tiene croquis, lo crea (POST /croquis/{visita_id}),
// trayendo las trampas activas de la visita anterior del mismo cliente.
//   - Lista: cada trampa con su estado, su foto y los botones Confirmar /
//     Retirar / Foto.
//   - Mapa (opcional): vista satelital con pines de colores que se pueden
//     arrastrar para mover una trampa. Solo aparece si se compiló con
//     MAPS_ENABLED=true (necesita la API key de Google Maps).
//   - "＋ Agregar trampa": el técnico registra una trampa que instaló, con su
//     ubicación GPS o tocando el mapa, y luego le puede sacar una foto.
//   - "Sugerir con IA" (botón de la barra): la IA mira la foto satelital del
//     predio y propone trampas nuevas, que quedan sin confirmar hasta que el
//     técnico las revise (POST /croquis/{visita_id}/sugerencia).
// Si la visita está completada (readOnly), todo es solo de consulta.
// =============================================================================

import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import 'package:image_picker/image_picker.dart';

import '../config/app_config.dart';
import '../models/croquis.dart';
import '../services/api_client.dart';
import '../services/field_location.dart';
import '../services/pending_photo.dart';
import '../services/pending_photo_files.dart';
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
  final ApiClient? apiClient;
  final PendingPhotoStore? photoStore;

  const CroquisScreen({
    super.key,
    required this.visitaId,
    this.clienteLat,
    this.clienteLng,
    this.readOnly = false,
    this.apiClient,
    this.photoStore,
  });

  @override
  State<CroquisScreen> createState() => _CroquisScreenState();
}

class _CroquisScreenState extends State<CroquisScreen> {
  late final _apiClient = widget.apiClient ?? ApiClient();
  late final _photos = widget.photoStore ?? PendingPhotoStore.instance;
  PendingPhoto? _pendingPhoto;

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
  // true mientras el operador debe tocar el mapa para ubicar una trampa nueva.
  bool _modoAgregar = false;
  // true mientras se guarda una trampa nueva (GPS o mapa).
  bool _agregando = false;
  // true mientras la IA prepara la sugerencia de trampas.
  bool _sugiriendo = false;
  // true si el usuario dio permiso de ubicación: el mapa muestra el punto azul.
  bool _ubicacionPermitida = false;
  // Header con el token para descargar las fotos (no son públicas).
  Map<String, String> _fotoHeaders = const {};

  @override
  void initState() {
    super.initState();
    _load();
    _apiClient
        .authHeaders()
        .then<void>((headers) {
          if (mounted) setState(() => _fotoHeaders = headers);
        })
        .catchError((Object _) {
          // _load informa el error sin una excepción asíncrona no controlada.
        });
    Geolocator.checkPermission()
        .then<void>((permiso) {
          if (mounted) {
            setState(() => _ubicacionPermitida = _permisoOk(permiso));
          }
        })
        .catchError((Object _) {
          // El permiso se vuelve a comprobar al solicitar una ubicación.
        });
  }

  bool _permisoOk(LocationPermission permiso) =>
      permiso == LocationPermission.always ||
      permiso == LocationPermission.whileInUse;

  /// Pide el croquis al backend.
  Future<void> _load() async {
    setState(() {
      _loading = true;
      _loadError = null;
      _sinCroquis = false;
    });
    try {
      Croquis croquis;
      try {
        croquis = await _apiClient.fetchCroquis(widget.visitaId);
      } on ApiException catch (error) {
        // 404 = la visita todavía no tiene croquis. Si la visita sigue
        // abierta, se crea ahora; si está completada, solo se informa.
        if (error.statusCode != 404 || widget.readOnly) rethrow;
        croquis = await _apiClient.createCroquis(widget.visitaId);
      }
      if (!mounted) return;
      setState(() => _croquis = croquis);
      // Si la sesión se renovó al cargar, las fotos deben pedirse con el
      // token nuevo.
      final headers = await _apiClient.authHeaders();
      if (mounted) setState(() => _fotoHeaders = headers);
      final pending = await _photos.readForCurrentAccount();
      if (mounted) {
        setState(
          () => _pendingPhoto = pending?.visitId == widget.visitaId
              ? pending
              : null,
        );
      }
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
      final actualizado = await _apiClient.updateDispositivo(
        dispositivo.id,
        accion,
        lat: lat,
        lng: lng,
      );
      if (!mounted) return;
      final croquis = _croquis!;
      setState(() {
        // Nueva lista: igual a la anterior, pero con la trampa actualizada
        // en lugar de la vieja (se compara por id).
        _croquis = croquis.copyWithDispositivos([
          for (final item in croquis.dispositivos)
            item.id == actualizado.id ? actualizado : item,
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
  Future<void> _confirmar(DispositivoTrampa dispositivo) =>
      _actualizarDispositivo(
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
        content: const Text(
          'La trampa quedará marcada como retirada. ¿Continuar?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancelar'),
          ),
          TextButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Retirar'),
          ),
        ],
      ),
    );
    if (confirmado == true) {
      // 'eliminar' es el nombre de la acción en la API.
      await _actualizarDispositivo(
        dispositivo,
        'eliminar',
        mensajeOk: '${dispositivo.codigo} retirada',
      );
    }
  }

  /// Se llama al soltar un pin arrastrado en el mapa: pide confirmación y,
  /// si el operador acepta, guarda la nueva posición.
  Future<void> _moverConfirmando(
    DispositivoTrampa dispositivo,
    LatLng nuevaPosicion,
  ) async {
    final confirmado = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Mover ${dispositivo.codigo}'),
        content: const Text('¿Guardar la nueva ubicación de esta trampa?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancelar'),
          ),
          TextButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Guardar'),
          ),
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

  /// Reemplaza una trampa de la lista por su versión actualizada.
  void _reemplazar(DispositivoTrampa actualizado) {
    final croquis = _croquis!;
    setState(() {
      _croquis = croquis.copyWithDispositivos([
        for (final item in croquis.dispositivos)
          item.id == actualizado.id ? actualizado : item,
      ]);
      _mapVersion++;
    });
  }

  /// "＋ Agregar trampa": el operador elige cómo ubicarla.
  Future<void> _elegirComoAgregar() async {
    final opcion = await showModalBottomSheet<String>(
      context: context,
      builder: (context) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const ListTile(
              title: Text(
                '¿Dónde instalaste la trampa?',
                style: TextStyle(fontWeight: FontWeight.w700),
              ),
            ),
            ListTile(
              leading: const Icon(Icons.my_location),
              title: const Text('Aquí, donde estoy parado'),
              subtitle: const Text('Usa la ubicación GPS del teléfono'),
              onTap: () => Navigator.of(context).pop('gps'),
            ),
            if (AppConfig.mapsEnabled)
              ListTile(
                leading: const Icon(Icons.touch_app_outlined),
                title: const Text('Marcarla en el mapa'),
                subtitle: const Text('Toca el lugar en la vista satelital'),
                onTap: () => Navigator.of(context).pop('mapa'),
              ),
          ],
        ),
      ),
    );
    if (!mounted || opcion == null) return;
    if (opcion == 'gps') {
      await _agregarConGps();
    } else {
      setState(() {
        _showMap = true;
        _modoAgregar = true;
      });
    }
  }

  /// Pide permiso de ubicación (si hace falta) y agrega la trampa en la
  /// posición actual del teléfono.
  Future<void> _agregarConGps({bool networkFallback = false}) async {
    if (_agregando || widget.readOnly) return;
    setState(() => _agregando = true);
    Position posicion;
    try {
      posicion = await FieldLocation().current(
        networkFallback: networkFallback,
      );
      if (mounted) setState(() => _ubicacionPermitida = true);
    } on FieldLocationException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(error.message),
            duration: const Duration(seconds: 10),
            action: error.canTryNetwork
                ? SnackBarAction(
                    label: 'Por red',
                    onPressed: () => _agregarConGps(networkFallback: true),
                  )
                : error.settings == null
                ? null
                : SnackBarAction(
                    label: 'Ajustes',
                    onPressed: () {
                      if (error.settings == LocationSettingsTarget.device) {
                        Geolocator.openLocationSettings();
                      } else {
                        Geolocator.openAppSettings();
                      }
                    },
                  ),
          ),
        );
      }
      return;
    } catch (_) {
      _mostrarMensaje(
        'No se pudo consultar el permiso de ubicación. Reintenta.',
      );
      return;
    } finally {
      if (mounted) setState(() => _agregando = false);
    }
    if (!mounted) return;
    setState(() => _agregando = false);
    // Con poca precisión (bajo techo) se avisa, pero se deja continuar.
    final aviso = networkFallback
        ? 'Ubicación aproximada (respaldo por red), precisión ±${posicion.accuracy.round()} m. Revisa la posición en el mapa.'
        : posicion.accuracy > 25
        ? 'GPS con precisión de ±${posicion.accuracy.round()} m'
        : '';
    await _agregarEn(
      LatLng(posicion.latitude, posicion.longitude),
      aviso: aviso,
    );
  }

  /// Pide el tipo de trampa y la guarda en `posicion`. Después ofrece sacarle
  /// una foto de referencia.
  Future<void> _agregarEn(LatLng posicion, {String aviso = ''}) async {
    final tipo = await showModalBottomSheet<String>(
      context: context,
      builder: (context) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              title: const Text(
                '¿Qué instalaste?',
                style: TextStyle(fontWeight: FontWeight.w700),
              ),
              subtitle: aviso.isEmpty ? null : Text(aviso),
            ),
            for (final tipo in const [
              'cebadero',
              'trampa_pegamento',
              'trampa_luz',
              'otro',
            ])
              ListTile(
                leading: const Icon(Icons.pest_control_outlined),
                title: Text(_tipoLabel(tipo)),
                onTap: () => Navigator.of(context).pop(tipo),
              ),
          ],
        ),
      ),
    );
    if (!mounted || tipo == null) return;

    setState(() => _agregando = true);
    try {
      final nueva = await _apiClient.addDispositivo(
        widget.visitaId,
        tipo: tipo,
        lat: posicion.latitude,
        lng: posicion.longitude,
      );
      if (!mounted) return;
      final croquis = _croquis!;
      setState(() {
        _croquis = croquis.copyWithDispositivos([
          ...croquis.dispositivos,
          nueva,
        ]);
        _mapVersion++;
        _agregando = false;
      });
      final sacarFoto = await showDialog<bool>(
        context: context,
        builder: (context) => AlertDialog(
          title: Text('${nueva.codigo} agregada'),
          content: const Text('¿Le sacas una foto de referencia ahora?'),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: const Text('Después'),
            ),
            FilledButton(
              onPressed: () => Navigator.of(context).pop(true),
              child: const Text('Sacar foto'),
            ),
          ],
        ),
      );
      if (sacarFoto == true) {
        await _tomarFoto(nueva, origen: ImageSource.camera);
      }
    } on ApiException catch (error) {
      _mostrarMensaje(error.message);
    } catch (_) {
      _mostrarMensaje('No se pudo conectar con el servidor');
    } finally {
      if (mounted) setState(() => _agregando = false);
    }
  }

  /// Saca (o elige) una foto y la sube como referencia de la trampa. Si no se
  /// indica `origen`, pregunta si usar la cámara o la galería.
  Future<void> _tomarFoto(
    DispositivoTrampa dispositivo, {
    ImageSource? origen,
  }) async {
    if (widget.readOnly || _updatingId != null) return;
    if (await _photos.read() != null) {
      final owned = await _photos.readForCurrentAccount();
      if (!mounted) return;
      if (owned != null) {
        _mostrarMensaje(
          'Reintenta o descarta primero la foto pendiente en su visita original',
        );
        return;
      }
      // No se muestra ni se reasigna la foto ajena. El envío se descarta
      // únicamente tras una decisión explícita antes de abrir el selector.
      final discard = await showDialog<bool>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('Foto pendiente de otra cuenta'),
          content: const Text(
            'Hay un envío pendiente de otra cuenta o de una sesión anterior. '
            'Para tomar una foto nueva debes descartar ese envío. '
            'La otra cuenta ya no podrá reintentarlo desde la app. '
            'No se borra la imagen original.',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Volver'),
            ),
            TextButton(
              onPressed: () => Navigator.pop(context, true),
              child: const Text('Descartar y continuar'),
            ),
          ],
        ),
      );
      if (discard != true || !mounted) return;
      await _photos.clear();
    }
    if (!mounted) return;
    origen ??= await showModalBottomSheet<ImageSource>(
      context: context,
      builder: (context) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: const Icon(Icons.photo_camera_outlined),
              title: const Text('Sacar foto'),
              onTap: () => Navigator.of(context).pop(ImageSource.camera),
            ),
            ListTile(
              leading: const Icon(Icons.photo_library_outlined),
              title: const Text('Elegir de la galería'),
              onTap: () => Navigator.of(context).pop(ImageSource.gallery),
            ),
          ],
        ),
      ),
    );
    if (!mounted || origen == null) return;

    // Se reduce la foto (ancho máx. 1600 px, calidad 70%) para que suba
    // rápido por datos móviles y no supere el límite de 5 MB del backend.
    final PendingPhoto? foto;
    try {
      foto = await _photos.capture(widget.visitaId, dispositivo.id, origen);
    } on PendingPhotoStorageException catch (error) {
      final pending = await _photos.readForCurrentAccount();
      if (!mounted) return;
      setState(() => _pendingPhoto = pending);
      _mostrarMensaje(error.message);
      return;
    } on StateError catch (error) {
      // Un conflicto de pendientes o de sesión no es un fallo de permisos.
      _mostrarMensaje(error.message.toString());
      return;
    } catch (_) {
      _mostrarMensaje(
        'No se pudo abrir la cámara o galería. Revisa sus permisos en Ajustes.',
      );
      return;
    }
    if (foto == null || !mounted) return; // canceló
    setState(() => _pendingPhoto = foto);
    await _subirFotoPendiente();
  }

  Future<void> _subirFotoPendiente() async {
    final foto = _pendingPhoto;
    if (foto == null ||
        foto.path == null ||
        widget.readOnly ||
        _updatingId != null) {
      return;
    }
    final owned = await _photos.readForCurrentAccount();
    if (!mounted) return;
    if (owned == null ||
        owned.deviceId != foto.deviceId ||
        owned.visitId != foto.visitId) {
      _mostrarMensaje(
        'Inicia sesión con la cuenta original para reintentar la foto',
      );
      return;
    }
    final dispositivos = _croquis?.dispositivos
        .where((item) => item.id == foto.deviceId)
        .toList();
    if (foto.visitId != widget.visitaId ||
        dispositivos == null ||
        dispositivos.isEmpty) {
      _mostrarMensaje(
        'La foto pendiente no pertenece a una trampa de esta visita',
      );
      return;
    }
    setState(() => _updatingId = foto.deviceId);
    try {
      final persistent = await _photos.prepareForUpload();
      if (persistent == null || persistent.path == null || persistent.visitId != foto.visitId ||
          persistent.deviceId != foto.deviceId) {
        _mostrarMensaje('Inicia sesión con la cuenta original para reintentar la foto');
        return;
      }
      if (!mounted) return;
      setState(() => _pendingPhoto = persistent);
      final actualizado = await _apiClient.uploadFoto(
        foto.deviceId,
        persistent.path!,
      );
      await _photos.clear();
      if (!mounted) return;
      setState(() => _pendingPhoto = null);
      _reemplazar(actualizado);
      _mostrarMensaje('Foto de ${actualizado.codigo} guardada');
    } on PendingPhotoStorageException catch (error) {
      _mostrarMensaje(error.message);
    } on ApiException catch (error) {
      _mostrarMensaje(error.message);
    } catch (_) {
      _mostrarMensaje(
        'No se pudo subir la foto. Se conserva para reintentar al recuperar conexión.',
      );
    } finally {
      if (mounted) setState(() => _updatingId = null);
    }
  }

  Future<void> _descartarFotoPendiente() async {
    final descartar = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Descartar envío pendiente'),
        content: const Text(
          'Se quitará el envío pendiente. No se borra la imagen original de la galería.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Volver'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Descartar'),
          ),
        ],
      ),
    );
    if (descartar != true) return;
    await _photos.clear();
    if (mounted) setState(() => _pendingPhoto = null);
  }

  /// Muestra la foto en pantalla completa (se puede hacer zoom).
  Future<void> _verFoto(DispositivoTrampa dispositivo) async {
    final fotoUrl = _apiClient.fotoUrlCompleta(dispositivo.fotoUrl);
    if (fotoUrl == null) return;
    try {
      final headers = await _apiClient.authHeaders();
      if (!mounted) return;
      setState(() => _fotoHeaders = headers);
    } catch (_) {
      _mostrarMensaje(
        'No se pudo autorizar la foto. Revisa la conexión y reintenta.',
      );
      return;
    }
    if (!mounted) return;
    showDialog<void>(
      context: context,
      builder: (context) => Dialog(
        insetPadding: const EdgeInsets.all(12),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              title: Text(
                '${dispositivo.codigo} · ${_tipoLabel(dispositivo.tipo)}',
              ),
              trailing: IconButton(
                icon: const Icon(Icons.close),
                onPressed: () => Navigator.of(context).pop(),
              ),
            ),
            Flexible(
              child: InteractiveViewer(
                child: Image.network(
                  fotoUrl,
                  headers: _fotoHeaders,
                  errorBuilder: (_, _, _) => const Padding(
                    padding: EdgeInsets.all(32),
                    child: Text('No se pudo cargar la foto'),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// "Sugerir con IA": pide los datos del predio, llama a la IA y agrega al
  /// croquis las trampas que propone (sin confirmar). Al final muestra el
  /// resumen y las advertencias de la IA.
  Future<void> _sugerirConIa() async {
    final datos = await showDialog<_DatosSugerencia>(
      context: context,
      builder: (context) => const _SugerenciaDialog(),
    );
    if (!mounted || datos == null) return;

    final antes = _croquis?.dispositivos.length ?? 0;
    setState(() => _sugiriendo = true);
    try {
      final sugerencia = await _apiClient.sugerirTrampas(
        widget.visitaId,
        tipoRecinto: datos.tipoRecinto,
        plaga: datos.plaga,
        superficieM2: datos.superficieM2,
        notas: datos.notas,
      );
      if (!mounted) return;
      setState(() {
        _croquis = sugerencia.croquis;
        _mapVersion++;
      });
      final nuevas = sugerencia.croquis.dispositivos.length - antes;
      await showDialog<void>(
        context: context,
        builder: (context) => AlertDialog(
          title: Text(
            nuevas > 0 ? '$nuevas trampas sugeridas' : 'Sin trampas nuevas',
          ),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (sugerencia.origen == 'reglas')
                  const Padding(
                    padding: EdgeInsets.only(bottom: 8),
                    child: Text(
                      'La IA no estaba disponible: se usó una ubicación por reglas.',
                      style: TextStyle(fontWeight: FontWeight.w700),
                    ),
                  ),
                if (sugerencia.resumen != null) Text(sugerencia.resumen!),
                for (final advertencia in sugerencia.advertencias)
                  Padding(
                    padding: const EdgeInsets.only(top: 8),
                    child: Text(
                      '⚠ $advertencia',
                      style: const TextStyle(color: AppColors.textSecondary),
                    ),
                  ),
                const SizedBox(height: 12),
                const Text(
                  'Revisa cada trampa en terreno: confírmala, muévela o retírala.',
                  style: TextStyle(fontWeight: FontWeight.w600),
                ),
              ],
            ),
          ),
          actions: [
            FilledButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Entendido'),
            ),
          ],
        ),
      );
    } on ApiException catch (error) {
      _mostrarMensaje(error.message);
    } catch (_) {
      _mostrarMensaje('No se pudo obtener la sugerencia. Revisa la conexión.');
    } finally {
      if (mounted) setState(() => _sugiriendo = false);
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
    // El botón "Agregar trampa" solo aparece con el croquis cargado y la
    // visita abierta (ni en modo lectura ni mientras se marca en el mapa).
    final puedeAgregar = _croquis != null && !widget.readOnly && !_modoAgregar;
    return Scaffold(
      appBar: AppBar(
        title: const Text('Croquis'),
        actions: [
          if (puedeAgregar)
            _sugiriendo
                ? const Padding(
                    padding: EdgeInsets.all(16),
                    child: SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    ),
                  )
                : IconButton(
                    onPressed: _agregando ? null : _sugerirConIa,
                    tooltip: 'Sugerir trampas con IA',
                    icon: const Icon(Icons.auto_awesome),
                  ),
        ],
      ),
      body: _buildBody(context),
      floatingActionButton: puedeAgregar
          ? FloatingActionButton.extended(
              onPressed: _agregando ? null : _elegirComoAgregar,
              icon: _agregando
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.add_location_alt_outlined),
              label: Text(_agregando ? 'Guardando…' : 'Agregar trampa'),
            )
          : null,
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
              Icon(
                Icons.map_outlined,
                size: 48,
                color: AppColors.textSecondary,
              ),
              SizedBox(height: 12),
              Text(
                'Esta visita no tiene croquis',
                textAlign: TextAlign.center,
                style: TextStyle(fontWeight: FontWeight.w700, fontSize: 16),
              ),
              SizedBox(height: 6),
              Text(
                'No se registraron trampas en esta visita.',
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
              Text(
                _loadError ?? 'No se pudo cargar el croquis',
                textAlign: TextAlign.center,
              ),
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
          const _Aviso(
            texto: 'Visita completada: este croquis es solo de consulta.',
          ),
        if (_pendingPhoto != null)
          Card(
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                children: [
                  const Text('Hay una foto pendiente de envío en esta visita'),
                  Wrap(
                    spacing: 8,
                    children: [
                      if (!widget.readOnly)
                        TextButton(
                          onPressed: _updatingId == null
                              ? _subirFotoPendiente
                              : null,
                          child: const Text('Reintentar envío'),
                        ),
                      TextButton(
                        onPressed: _updatingId == null
                            ? _descartarFotoPendiente
                            : null,
                        child: const Text('Descartar'),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        // Con mapa habilitado: selector Lista / Mapa. Sin mapa: un aviso.
        if (AppConfig.mapsEnabled)
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
            child: SegmentedButton<bool>(
              segments: const [
                ButtonSegment(
                  value: false,
                  label: Text('Lista'),
                  icon: Icon(Icons.list),
                ),
                ButtonSegment(
                  value: true,
                  label: Text('Mapa'),
                  icon: Icon(Icons.map_outlined),
                ),
              ],
              selected: {_showMap},
              onSelectionChanged: (selection) => setState(() {
                _showMap = selection.first;
                if (!_showMap) _modoAgregar = false;
              }),
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
          child: (AppConfig.mapsEnabled && _showMap)
              ? _buildMap(croquis)
              : _buildList(croquis),
        ),
      ],
    );
  }

  /// Vista de lista: una tarjeta por trampa.
  Widget _buildList(Croquis croquis) {
    if (croquis.dispositivos.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Text(
            widget.readOnly ? 'Este croquis no tiene trampas' : 'Aún no hay trampas.\nToca ✨ para que la IA sugiera dónde ponerlas,\no "Agregar trampa" cuando instales una.',
            textAlign: TextAlign.center,
          ),
        ),
      );
    }
    return ListView.builder(
      // Espacio abajo para que el botón flotante no tape la última tarjeta.
      padding: const EdgeInsets.fromLTRB(0, 8, 0, 96),
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
          onFoto: () => _tomarFoto(dispositivo),
          onVerFoto: () => _verFoto(dispositivo),
          fotoUrl: _apiClient.fotoUrlCompleta(dispositivo.fotoUrl),
          fotoHeaders: _fotoHeaders,
        );
      },
    );
  }

  /// Vista de mapa: un pin por trampa (requiere la API key de Google Maps).
  Widget _buildMap(Croquis croquis) {
    final mapa = GoogleMap(
      // Cambiar la key obliga a Flutter a reconstruir el mapa desde cero.
      key: ValueKey(_mapVersion),
      // Satelital con nombres de calles: se ven techos, patios y muros.
      mapType: MapType.hybrid,
      // zoom 19 = nivel de detalle de casa/patio.
      initialCameraPosition: CameraPosition(
        target: _centerFor(croquis.dispositivos),
        zoom: 19,
      ),
      // Punto azul con la posición del técnico (si dio permiso de ubicación).
      myLocationEnabled: _ubicacionPermitida,
      myLocationButtonEnabled: _ubicacionPermitida,
      // En modo agregar, tocar el mapa ubica la trampa nueva.
      onTap: _modoAgregar
          ? (posicion) {
              setState(() => _modoAgregar = false);
              _agregarEn(posicion);
            }
          : null,
      markers: {
        for (final dispositivo in croquis.dispositivos)
          Marker(
            markerId: MarkerId(dispositivo.id),
            position: LatLng(dispositivo.lat, dispositivo.lng),
            icon: BitmapDescriptor.defaultMarkerWithHue(
              _markerHue(dispositivo),
            ),
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
    if (!_modoAgregar) return mapa;
    // Instrucción encima del mapa mientras se espera el toque.
    return Stack(
      children: [
        mapa,
        Positioned(
          top: 12,
          left: 12,
          right: 12,
          child: Material(
            elevation: 3,
            borderRadius: BorderRadius.circular(10),
            color: AppColors.yellow,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(14, 6, 6, 6),
              child: Row(
                children: [
                  const Expanded(
                    child: Text(
                      'Toca el mapa donde instalaste la trampa',
                      style: TextStyle(
                        fontWeight: FontWeight.w700,
                        color: AppColors.black,
                      ),
                    ),
                  ),
                  TextButton(
                    onPressed: () => setState(() => _modoAgregar = false),
                    child: const Text(
                      'Cancelar',
                      style: TextStyle(color: AppColors.black),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ],
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
    if (dispositivo.confirmado) return 'Confirmada';
    return dispositivo.sugeridoPorIa
        ? 'Sugerida por IA · sin confirmar'
        : 'De la visita anterior · revisar';
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
      final avgLat =
          dispositivos.map((d) => d.lat).reduce((a, b) => a + b) /
          dispositivos.length;
      final avgLng =
          dispositivos.map((d) => d.lng).reduce((a, b) => a + b) /
          dispositivos.length;
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
  final VoidCallback onFoto; // sacar o cambiar la foto de referencia
  final VoidCallback onVerFoto; // abrir la foto en grande
  final String? fotoUrl; // dirección completa de la foto, o null
  final Map<String, String> fotoHeaders; // token para descargar la foto

  const _DispositivoCard({
    required this.dispositivo,
    required this.tipoLabel,
    required this.updating,
    required this.readOnly,
    required this.onConfirmar,
    required this.onRetirar,
    required this.onFoto,
    required this.onVerFoto,
    required this.fotoUrl,
    required this.fotoHeaders,
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
                    padding: const EdgeInsets.symmetric(
                      horizontal: 10,
                      vertical: 4,
                    ),
                    decoration: BoxDecoration(
                      color: fondo,
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Text(
                      etiqueta,
                      style: TextStyle(
                        color: texto,
                        fontWeight: FontWeight.w700,
                        fontSize: 11,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 4),
              Text(
                dispositivo.sugeridoPorIa
                    ? 'Ubicación sugerida por la IA'
                    : 'Ubicación definida por el operador',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              // Miniatura de la foto de referencia; al tocarla se ve en grande.
              if (fotoUrl != null) ...[
                const SizedBox(height: 10),
                GestureDetector(
                  onTap: onVerFoto,
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(8),
                    child: Image.network(
                      fotoUrl!,
                      headers: fotoHeaders,
                      height: 140,
                      width: double.infinity,
                      fit: BoxFit.cover,
                      errorBuilder: (_, _, _) => Container(
                        height: 60,
                        alignment: Alignment.center,
                        color: const Color(0xFFECECE6),
                        child: const Text('No se pudo cargar la foto'),
                      ),
                    ),
                  ),
                ),
              ],
              // Botones solo si la trampa sigue activa y la visita no está
              // completada.
              if (!retirada && !readOnly) ...[
                const SizedBox(height: 12),
                if (updating)
                  const Center(
                    child: SizedBox(
                      width: 24,
                      height: 24,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    ),
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
                            style: FilledButton.styleFrom(
                              minimumSize: const Size.fromHeight(44),
                            ),
                          ),
                        ),
                      if (!dispositivo.confirmado) const SizedBox(width: 10),
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: onRetirar,
                          icon: const Icon(Icons.delete_outline, size: 18),
                          label: const Text('Retirar'),
                          style: OutlinedButton.styleFrom(
                            minimumSize: const Size.fromHeight(44),
                          ),
                        ),
                      ),
                      const SizedBox(width: 10),
                      // Foto de referencia: sacar una nueva o reemplazar la actual.
                      IconButton.outlined(
                        onPressed: onFoto,
                        tooltip: fotoUrl == null
                            ? 'Sacar foto'
                            : 'Cambiar foto',
                        icon: const Icon(Icons.photo_camera_outlined),
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

/// Datos del predio que el técnico entrega para pedir la sugerencia.
class _DatosSugerencia {
  final String tipoRecinto;
  final String plaga;
  final double? superficieM2;
  final String? notas;

  const _DatosSugerencia({
    required this.tipoRecinto,
    required this.plaga,
    this.superficieM2,
    this.notas,
  });
}

/// Formulario corto antes de llamar a la IA. Los valores coinciden con los
/// Enum TipoRecinto y Plaga del backend (schemas.py).
class _SugerenciaDialog extends StatefulWidget {
  const _SugerenciaDialog();

  @override
  State<_SugerenciaDialog> createState() => _SugerenciaDialogState();
}

class _SugerenciaDialogState extends State<_SugerenciaDialog> {
  static const _recintos = {
    'casa': 'Casa',
    'restaurante': 'Restaurante',
    'bodega': 'Bodega',
    'local_comercial': 'Local comercial',
    'industria': 'Industria',
  };
  static const _plagas = {
    'roedores': 'Roedores',
    'cucarachas': 'Cucarachas',
    'moscas': 'Moscas',
    'otra': 'Otra',
  };

  String _tipoRecinto = 'casa';
  String _plaga = 'roedores';
  final _superficie = TextEditingController();
  final _notas = TextEditingController();

  @override
  void dispose() {
    _superficie.dispose();
    _notas.dispose();
    super.dispose();
  }

  void _enviar() {
    // Acepta "180" o "180,5"; si no es un número válido, se envía sin superficie.
    final superficie = double.tryParse(
      _superficie.text.trim().replaceAll(',', '.'),
    );
    final notas = _notas.text.trim();
    Navigator.of(context).pop(
      _DatosSugerencia(
        tipoRecinto: _tipoRecinto,
        plaga: _plaga,
        superficieM2: (superficie != null && superficie > 0)
            ? superficie
            : null,
        notas: notas.isEmpty ? null : notas,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Sugerir trampas con IA'),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            DropdownButtonFormField<String>(
              initialValue: _tipoRecinto,
              decoration: const InputDecoration(labelText: 'Tipo de recinto'),
              items: [
                for (final entry in _recintos.entries)
                  DropdownMenuItem(value: entry.key, child: Text(entry.value)),
              ],
              onChanged: (valor) =>
                  setState(() => _tipoRecinto = valor ?? _tipoRecinto),
            ),
            const SizedBox(height: 12),
            DropdownButtonFormField<String>(
              initialValue: _plaga,
              decoration: const InputDecoration(labelText: 'Plaga'),
              items: [
                for (final entry in _plagas.entries)
                  DropdownMenuItem(value: entry.key, child: Text(entry.value)),
              ],
              onChanged: (valor) => setState(() => _plaga = valor ?? _plaga),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _superficie,
              keyboardType: const TextInputType.numberWithOptions(
                decimal: true,
              ),
              decoration: const InputDecoration(
                labelText: 'Superficie aprox. (m²)',
                hintText: 'Opcional',
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _notas,
              maxLength: 500,
              maxLines: 2,
              decoration: const InputDecoration(
                labelText: 'Notas',
                hintText: 'Ej: basura en el patio trasero',
              ),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Cancelar'),
        ),
        FilledButton.icon(
          onPressed: _enviar,
          icon: const Icon(Icons.auto_awesome, size: 18),
          label: const Text('Sugerir'),
        ),
      ],
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
