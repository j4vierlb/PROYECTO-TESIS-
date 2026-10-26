import 'package:flutter/foundation.dart';
import 'package:geolocator/geolocator.dart';

LocationSettings fieldLocationSettings({bool networkFallback = false}) {
  // GPS nativo: no exige activar el servicio adicional Google Location Accuracy.
  if (!kIsWeb && defaultTargetPlatform == TargetPlatform.android) {
    return AndroidSettings(
      forceLocationManager: !networkFallback,
      accuracy: networkFallback
          ? LocationAccuracy.medium
          : LocationAccuracy.high,
      timeLimit: Duration(seconds: networkFallback ? 10 : 20),
    );
  }
  return const LocationSettings(
    accuracy: LocationAccuracy.high,
    timeLimit: Duration(seconds: 20),
  );
}

enum LocationSettingsTarget { device, application }

class FieldLocationException implements Exception {
  final String message;
  final LocationSettingsTarget? settings;
  final bool canTryNetwork;
  const FieldLocationException(
    this.message, {
    this.settings,
    this.canTryNetwork = false,
  });
}

/// Misma política para Android e iOS; callbacks reemplazables en pruebas.
class FieldLocation {
  final Future<bool> Function() serviceEnabled;
  final Future<LocationPermission> Function() permission;
  final Future<LocationPermission> Function() requestPermission;
  final Future<Position> Function() locate;
  final Future<Position> Function() locateFallback;

  FieldLocation({
    Future<bool> Function()? serviceEnabled,
    Future<LocationPermission> Function()? permission,
    Future<LocationPermission> Function()? requestPermission,
    Future<Position> Function()? locate,
    Future<Position> Function()? locateFallback,
  }) : serviceEnabled = serviceEnabled ?? Geolocator.isLocationServiceEnabled,
       permission = permission ?? Geolocator.checkPermission,
       requestPermission = requestPermission ?? Geolocator.requestPermission,
       locate =
           locate ??
           (() => Geolocator.getCurrentPosition(
             locationSettings: fieldLocationSettings(),
           )),
       locateFallback =
           locateFallback ??
           (() => Geolocator.getCurrentPosition(
             locationSettings: fieldLocationSettings(networkFallback: true),
           ));

  Future<Position> current({bool networkFallback = false}) async {
    if (!await serviceEnabled()) {
      throw const FieldLocationException(
        'Activa la ubicación (GPS) del teléfono',
        settings: LocationSettingsTarget.device,
      );
    }
    var status = await permission();
    if (status == LocationPermission.denied) status = await requestPermission();
    if (status == LocationPermission.deniedForever) {
      throw const FieldLocationException(
        'Activa el permiso de ubicación en Ajustes',
        settings: LocationSettingsTarget.application,
      );
    }
    if (status != LocationPermission.always &&
        status != LocationPermission.whileInUse) {
      throw const FieldLocationException(
        'Sin permiso de ubicación no se puede usar el GPS',
      );
    }
    try {
      return await (networkFallback ? locateFallback() : locate());
    } catch (_) {
      final offerNetwork =
          !networkFallback &&
          !kIsWeb &&
          defaultTargetPlatform == TargetPlatform.android;
      throw FieldLocationException(
        offerNetwork
            ? 'No se obtuvo ubicación (límite 20 s). Puedes intentar por red (Google puede solicitar activar su precisión) o marcarla en el mapa.'
            : 'No se pudo obtener la ubicación. Prueba al aire libre o márcala en el mapa.',
        canTryNetwork: offerNetwork,
      );
    }
  }
}
