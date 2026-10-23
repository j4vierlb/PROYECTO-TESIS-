import 'dart:async';

import 'package:app_movil/services/field_location.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter/foundation.dart';
import 'package:geolocator/geolocator.dart';

void main() {
  test('Android usa GPS nativo e iOS conserva el proveedor de plataforma', () {
    try {
      debugDefaultTargetPlatformOverride = TargetPlatform.android;
      final android = fieldLocationSettings() as AndroidSettings;
      expect(android.forceLocationManager, isTrue);
      expect(android.timeLimit, const Duration(seconds: 20));
      debugDefaultTargetPlatformOverride = TargetPlatform.iOS;
      expect(fieldLocationSettings(), isNot(isA<AndroidSettings>()));
    } finally {
      debugDefaultTargetPlatformOverride = null;
    }
  });
  test('Respaldo Android usa proveedor fusionado, precision media y 10 segundos', () {
    debugDefaultTargetPlatformOverride = TargetPlatform.android;
    try {
      final settings = fieldLocationSettings(networkFallback: true) as AndroidSettings;
      expect(settings.forceLocationManager, isFalse);
      expect(settings.accuracy, LocationAccuracy.medium);
      expect(settings.timeLimit, const Duration(seconds: 10));
    } finally {
      debugDefaultTargetPlatformOverride = null;
    }
  });
  final position = Position(
    longitude: -70.5989,
    latitude: -33.4869,
    timestamp: DateTime.utc(2026),
    accuracy: 3,
    altitude: 0,
    altitudeAccuracy: 0,
    heading: 0,
    headingAccuracy: 0,
    speed: 0,
    speedAccuracy: 0,
  );
  test('GPS desactivado ofrece ajustes y no consulta posicion', () async {
    final gps = FieldLocation(
      serviceEnabled: () async => false,
      locate: () => throw StateError('No debe llamarse'),
    );
    await expectLater(
      gps.current(),
      throwsA(
        isA<FieldLocationException>().having(
          (e) => e.settings,
          'ajustes',
          LocationSettingsTarget.device,
        ),
      ),
    );
  });
  for (final status in [
    LocationPermission.whileInUse,
    LocationPermission.always,
  ]) {
    test('GPS autorizado $status conserva las coordenadas', () async {
      final gps = FieldLocation(
        serviceEnabled: () async => true,
        permission: () async => status,
        locate: () async => position,
      );
      expect(await gps.current(), same(position));
    });
  }
  test(
    'Primera denegacion pide permiso y permite continuar al aceptar',
    () async {
      var requests = 0;
      final gps = FieldLocation(
        serviceEnabled: () async => true,
        permission: () async => LocationPermission.denied,
        requestPermission: () async {
          requests++;
          return LocationPermission.whileInUse;
        },
        locate: () async => position,
      );
      expect(await gps.current(), same(position));
      expect(requests, 1);
    },
  );
  test('Rechazar permiso no agrega una trampa', () async {
    final gps = FieldLocation(
      serviceEnabled: () async => true,
      permission: () async => LocationPermission.denied,
      requestPermission: () async => LocationPermission.denied,
      locate: () => throw StateError('No debe llamarse'),
    );
    await expectLater(gps.current(), throwsA(isA<FieldLocationException>()));
  });
  test('Denegacion permanente ofrece ajustes de aplicacion', () async {
    final gps = FieldLocation(
      serviceEnabled: () async => true,
      permission: () async => LocationPermission.deniedForever,
    );
    await expectLater(
      gps.current(),
      throwsA(
        isA<FieldLocationException>().having(
          (e) => e.settings,
          'ajustes',
          LocationSettingsTarget.application,
        ),
      ),
    );
  });
  test('Timeout GPS informa alternativa de marcar en mapa', () async {
    final gps = FieldLocation(
      serviceEnabled: () async => true,
      permission: () async => LocationPermission.whileInUse,
      locate: () => throw TimeoutException('GPS sin señal'),
    );
    await expectLater(
      gps.current(),
      throwsA(
        isA<FieldLocationException>().having(
          (e) => e.message,
          'alternativa',
          contains('mapa'),
        ),
      ),
    );
  });
  test('Fallo nativo ofrece respaldo pero no activa Google automaticamente', () async {
    var fallbackCalls = 0;
    debugDefaultTargetPlatformOverride = TargetPlatform.android;
    try {
      final gps = FieldLocation(
        serviceEnabled: () async => true,
        permission: () async => LocationPermission.whileInUse,
        locate: () => throw TimeoutException('GPS'),
        locateFallback: () async { fallbackCalls++; return position; },
      );
      await expectLater(gps.current(), throwsA(isA<FieldLocationException>().having((e) => e.canTryNetwork, 'opcion explicita', isTrue)));
      expect(fallbackCalls, 0);
      expect(await gps.current(networkFallback: true), same(position));
      expect(fallbackCalls, 1);
    } finally {
      debugDefaultTargetPlatformOverride = null;
    }
  });
  test('Rechazar permiso impide tambien consultar el respaldo por red', () async {
    final gps = FieldLocation(
      serviceEnabled: () async => true,
      permission: () async => LocationPermission.denied,
      requestPermission: () async => LocationPermission.denied,
      locateFallback: () => throw StateError('No se debe consultar'),
    );
    await expectLater(gps.current(networkFallback: true), throwsA(isA<FieldLocationException>()));
  });
  test('Si falla el respaldo no forma un bucle y ofrece mapa', () async {
    final gps = FieldLocation(
      serviceEnabled: () async => true,
      permission: () async => LocationPermission.whileInUse,
      locateFallback: () => throw TimeoutException('Red'),
    );
    await expectLater(gps.current(networkFallback: true), throwsA(isA<FieldLocationException>().having((e) => e.canTryNetwork, 'sin bucle', isFalse).having((e) => e.message, 'alternativa', contains('mapa'))));
  });
}
