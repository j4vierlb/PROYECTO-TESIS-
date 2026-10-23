import 'package:flutter/foundation.dart';
import 'package:geolocator/geolocator.dart';

LocationSettings fieldLocationSettings() {
  // GPS nativo: no exige activar el servicio adicional Google Location Accuracy.
  if (!kIsWeb && defaultTargetPlatform == TargetPlatform.android) {
    return AndroidSettings(
      forceLocationManager: true,
      accuracy: LocationAccuracy.high,
      timeLimit: const Duration(seconds: 20),
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
  const FieldLocationException(this.message, {this.settings});
}

/// Misma política para Android e iOS; callbacks reemplazables en pruebas.
class FieldLocation {
  final Future<bool> Function() serviceEnabled;
  final Future<LocationPermission> Function() permission;
  final Future<LocationPermission> Function() requestPermission;
  final Future<Position> Function() locate;

  FieldLocation({
    Future<bool> Function()? serviceEnabled,
    Future<LocationPermission> Function()? permission,
    Future<LocationPermission> Function()? requestPermission,
    Future<Position> Function()? locate,
  }) : serviceEnabled = serviceEnabled ?? Geolocator.isLocationServiceEnabled,
       permission = permission ?? Geolocator.checkPermission,
       requestPermission = requestPermission ?? Geolocator.requestPermission,
       locate =
           locate ??
           (() => Geolocator.getCurrentPosition(
             locationSettings: fieldLocationSettings(),
           ));

  Future<Position> current() async {
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
      return await locate();
    } catch (_) {
      throw const FieldLocationException(
        'No se pudo obtener la ubicación. Prueba al aire libre o márcala en el mapa.',
      );
    }
  }
}
