// =============================================================================
// utils/enlaces.dart — Enlaces para abrir otras apps (mapas, llamada, WhatsApp)
// -----------------------------------------------------------------------------
// El técnico toca la dirección del cliente para ir hasta allá, o su teléfono
// para llamarlo o escribirle. Aquí solo se arman las direcciones (URI); abrirlas
// es trabajo de url_launcher. Devuelven null cuando el dato no alcanza para
// armar un enlace válido, y la pantalla deja ese botón desactivado.
// =============================================================================

import 'package:url_launcher/url_launcher.dart';

/// Texto que muestra la app cuando el cliente no tiene dirección (ver
/// Cliente.direccionTexto). No es una dirección real, así que no se navega a ella.
const String direccionVacia = 'Sin dirección registrada';

bool _coordenadasValidas(double? lat, double? lng) =>
    lat != null &&
    lng != null &&
    lat.isFinite &&
    lng.isFinite &&
    lat >= -90 &&
    lat <= 90 &&
    lng >= -180 &&
    lng <= 180;

/// Ruta hasta el cliente en Google Maps. Funciona en iPhone y Android: abre la
/// app de mapas si está instalada y, si no, el navegador. Prefiere las
/// coordenadas (exactas) y, si no hay, usa la dirección escrita.
Uri? urlNavegacion({double? lat, double? lng, String? direccion}) {
  final String destino;
  if (_coordenadasValidas(lat, lng)) {
    destino = '$lat,$lng';
  } else {
    final texto = (direccion ?? '').trim();
    if (texto.isEmpty || texto == direccionVacia) return null;
    destino = texto;
  }
  return Uri.https('www.google.com', '/maps/dir/', {'api': '1', 'destination': destino});
}

/// Solo los dígitos de un teléfono ("+56 9 2641 7357" -> "56926417357"),
/// quitando también un prefijo "whatsapp:".
String _digitos(String telefono) => telefono.replaceAll(RegExp(r'\D'), '');

/// Teléfono en formato internacional sin "+". Un celular chileno escrito sin el
/// código de país (9 dígitos que empiezan con 9) se completa con el 56.
String? _internacional(String telefono) {
  var digitos = _digitos(telefono);
  if (digitos.length == 9 && digitos.startsWith('9')) digitos = '56$digitos';
  return digitos.length >= 8 && digitos.length <= 15 ? digitos : null;
}

/// Llamada telefónica al cliente (abre el marcador con el número listo).
Uri? urlLlamada(String telefono) {
  final numero = _internacional(telefono);
  return numero == null ? null : Uri(scheme: 'tel', path: '+$numero');
}

/// Chat de WhatsApp con el cliente.
Uri? urlWhatsapp(String telefono) {
  final numero = _internacional(telefono);
  return numero == null ? null : Uri.https('wa.me', '/$numero');
}

/// Función que abre una dirección en otra app. Las pantallas reciben una por
/// parámetro para poder probarlas sin abrir nada de verdad.
typedef AbrirEnlace = Future<bool> Function(Uri uri);

/// Abre el enlace en la app correspondiente (teléfono, WhatsApp o navegador).
/// Devuelve false si el teléfono no puede abrirlo.
Future<bool> abrirEnlaceExterno(Uri uri) async {
  try {
    return await launchUrl(uri, mode: LaunchMode.externalApplication);
  } catch (_) {
    return false;
  }
}

/// Abre la página DENTRO de la app, en una vista con un botón para cerrar
/// ("Listo" en iPhone, la X en Android) que devuelve al técnico a la visita.
/// Se usa para el mapa: abrir la app de Google Maps lo sacaba de Kill Bichos y
/// no había un botón para volver. Si el teléfono no puede mostrarla así, se
/// abre fuera de la app como último recurso.
Future<bool> abrirEnlaceEnApp(Uri uri) async {
  try {
    if (await launchUrl(uri, mode: LaunchMode.inAppBrowserView)) return true;
  } catch (_) {
    // Sigue con el plan B.
  }
  return abrirEnlaceExterno(uri);
}
