import 'package:app_movil/utils/client_map_marker.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';

void main() {
  test(
    'El cliente tiene un pin rojo fijo en su punto exacto y con su dirección',
    () {
      final marker = clientMapMarker(
        lat: -33.4290994,
        lng: -70.621161,
        name: '  Cliente QA  ',
        address: '  Providencia 1208, Providencia  ',
      )!;
      expect(marker.markerId, const MarkerId('client-location'));
      expect(marker.position, const LatLng(-33.4290994, -70.621161));
      expect(
        marker.icon.toJson(),
        BitmapDescriptor.defaultMarkerWithHue(BitmapDescriptor.hueRed).toJson(),
      );
      expect(marker.draggable, isFalse);
      expect(marker.onDragEnd, isNull);
      expect(marker.zIndexInt, 10);
      expect(marker.infoWindow.title, 'Cliente QA');
      expect(marker.infoWindow.snippet, 'Providencia 1208, Providencia');
    },
  );

  test('Sin nombre o dirección no inventa datos en la etiqueta', () {
    final marker = clientMapMarker(
      lat: -33.4,
      lng: -70.6,
      name: ' ',
      address: ' ',
    )!;
    expect(marker.infoWindow.title, 'Ubicación del cliente');
    expect(marker.infoWindow.snippet, isNull);
  });

  test('No coloca pin en el centro por defecto si faltan coordenadas', () {
    expect(clientMapMarker(lat: null, lng: null), isNull);
    expect(clientMapMarker(lat: null, lng: -70.6), isNull);
    expect(clientMapMarker(lat: -33.4, lng: null), isNull);
  });

  test('Rechaza coordenadas no finitas o fuera del rango geográfico', () {
    for (final point in [
      (double.nan, -70.6),
      (-33.4, double.nan),
      (double.infinity, -70.6),
      (-33.4, double.negativeInfinity),
      (90.1, -70.6),
      (-90.1, -70.6),
      (-33.4, 180.1),
      (-33.4, -180.1),
    ]) {
      expect(clientMapMarker(lat: point.$1, lng: point.$2), isNull);
    }
  });

  test('Cero es una coordenada válida, no un dato ausente', () {
    expect(clientMapMarker(lat: 0, lng: 0)!.position, const LatLng(0, 0));
  });

  test('El pin no cambia de identidad cuando se corrige la dirección', () {
    final before = clientMapMarker(lat: -33.4, lng: -70.6)!;
    final after = clientMapMarker(lat: -33.5, lng: -70.7)!;
    expect(before.markerId, after.markerId);
    expect(before.position, isNot(after.position));
  });
}
