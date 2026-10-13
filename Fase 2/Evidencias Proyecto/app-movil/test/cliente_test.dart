// =============================================================================
// test/cliente_test.dart — Clientes sin dirección ni coordenadas
// -----------------------------------------------------------------------------
// Un cliente que llega por WhatsApp se registra solo con su teléfono. La app
// debe leerlo sin caerse y mostrar un texto en vez de la dirección vacía.
// =============================================================================

import 'package:flutter_test/flutter_test.dart';

import 'package:app_movil/models/visita.dart';

void main() {
  test('Cliente de WhatsApp sin dirección ni coordenadas no rompe la app', () {
    final cliente = Cliente.fromJson({
      'id': 'c1',
      'nombre': 'Cliente WhatsApp +56999990000',
      'telefono_whatsapp': '+56999990000',
      'direccion': null,
      'lat': null,
      'lng': null,
    });
    expect(cliente.direccion, isNull);
    expect(cliente.lat, isNull);
    expect(cliente.lng, isNull);
    expect(cliente.direccionTexto, 'Sin dirección registrada');
  });

  test('Cliente con dirección pero todavía sin coordenadas', () {
    final cliente = Cliente.fromJson({
      'id': 'c2',
      'nombre': 'Cliente WhatsApp',
      'telefono_whatsapp': '+56999990001',
      'direccion': 'Av. Grecia 1234, Ñuñoa',
      'lat': null,
      'lng': null,
    });
    expect(cliente.direccionTexto, 'Av. Grecia 1234, Ñuñoa');
    expect(cliente.lat, isNull);
  });

  test('Cliente completo sigue funcionando igual', () {
    final cliente = Cliente.fromJson({
      'id': 'c3',
      'nombre': 'Restaurante Don José',
      'telefono_whatsapp': '+56911111111',
      'direccion': 'Av. Macul 1234, Macul',
      'lat': -33.4869,
      'lng': -70, // entero: también debe convertirse a decimal
    });
    expect(cliente.lat, -33.4869);
    expect(cliente.lng, -70.0);
    expect(cliente.direccionTexto, 'Av. Macul 1234, Macul');
  });
}
