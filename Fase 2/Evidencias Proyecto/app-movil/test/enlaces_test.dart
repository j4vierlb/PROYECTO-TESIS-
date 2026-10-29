// Pruebas de los enlaces que arma la app para abrir mapas, llamada y WhatsApp.

import 'package:app_movil/utils/enlaces.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('urlNavegacion', () {
    test('con coordenadas navega al punto exacto', () {
      final uri = urlNavegacion(lat: -33.48, lng: -70.59, direccion: 'Av. Macul 123')!;
      expect(uri.host, 'www.google.com');
      expect(uri.path, '/maps/dir/');
      expect(uri.queryParameters['api'], '1');
      expect(uri.queryParameters['destination'], '-33.48,-70.59');
    });

    test('sin coordenadas usa la dirección escrita, con tildes y espacios codificados', () {
      final uri = urlNavegacion(direccion: 'Avenida Libertad 1000, Viña del Mar')!;
      expect(uri.queryParameters['destination'], 'Avenida Libertad 1000, Viña del Mar');
      expect(uri.toString(), isNot(contains(' ')));
    });

    test('coordenadas inválidas se ignoran y se usa la dirección', () {
      for (final malas in [(double.nan, -70.0), (91.0, -70.0), (-33.0, 181.0), (null, -70.0)]) {
        final uri = urlNavegacion(lat: malas.$1, lng: malas.$2, direccion: 'Av. Macul 123');
        expect(uri!.queryParameters['destination'], 'Av. Macul 123', reason: '$malas');
      }
    });

    test('sin coordenadas ni dirección no hay a dónde ir', () {
      expect(urlNavegacion(), isNull);
      expect(urlNavegacion(direccion: '   '), isNull);
      expect(urlNavegacion(direccion: direccionVacia), isNull);
    });

    test('una dirección con símbolos no rompe la dirección', () {
      final uri = urlNavegacion(direccion: 'Pasaje 5 #123 & Los Aromos')!;
      expect(uri.queryParameters['destination'], 'Pasaje 5 #123 & Los Aromos');
    });
  });

  group('teléfono', () {
    test('llamada en formato internacional', () {
      expect(urlLlamada('+56926417357').toString(), 'tel:+56926417357');
    });

    test('quita espacios, guiones, paréntesis y el prefijo whatsapp:', () {
      expect(urlLlamada('+56 9 2641-7357').toString(), 'tel:+56926417357');
      expect(urlLlamada('whatsapp:+56926417357').toString(), 'tel:+56926417357');
      expect(urlWhatsapp('(+56) 9 2641 7357').toString(), 'https://wa.me/56926417357');
    });

    test('un celular chileno sin código de país se completa con el 56', () {
      expect(urlLlamada('926417357').toString(), 'tel:+56926417357');
      expect(urlWhatsapp('926417357').toString(), 'https://wa.me/56926417357');
    });

    test('WhatsApp usa solo dígitos', () {
      expect(urlWhatsapp('+56926417357').toString(), 'https://wa.me/56926417357');
    });

    test('un teléfono inservible no genera enlace', () {
      for (final malo in ['', '   ', 'sin teléfono', '123', '+1234567890123456789']) {
        expect(urlLlamada(malo), isNull, reason: malo);
        expect(urlWhatsapp(malo), isNull, reason: malo);
      }
    });
  });
}
