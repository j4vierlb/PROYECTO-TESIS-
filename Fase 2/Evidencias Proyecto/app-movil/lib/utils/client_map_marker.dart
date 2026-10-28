import 'package:google_maps_flutter/google_maps_flutter.dart';

/// Referencia del cliente, no una trampa ni la posición GPS del teléfono.
/// Nunca representa el punto por defecto del mapa como una ubicación real.
Marker? clientMapMarker({
  required double? lat,
  required double? lng,
  String? name,
  String? address,
}) {
  if (lat == null ||
      lng == null ||
      !lat.isFinite ||
      !lng.isFinite ||
      lat < -90 ||
      lat > 90 ||
      lng < -180 ||
      lng > 180) {
    return null;
  }
  final title = (name ?? '').trim();
  final streetAddress = (address ?? '').trim();
  return Marker(
    markerId: const MarkerId('client-location'),
    position: LatLng(lat, lng),
    icon: BitmapDescriptor.defaultMarkerWithHue(BitmapDescriptor.hueRed),
    draggable: false,
    zIndexInt: 10,
    infoWindow: InfoWindow(
      title: title.isEmpty ? 'Ubicación del cliente' : title,
      snippet: streetAddress.isEmpty ? null : streetAddress,
    ),
  );
}
