// =============================================================================
// test/croquis_test.dart — Trampas con y sin foto de referencia
// -----------------------------------------------------------------------------
// El backend manda "foto_url" solo cuando la trampa tiene foto. La app debe
// leer ambos casos, y al actualizar una trampa conservar el resto del croquis.
// =============================================================================

import 'package:flutter_test/flutter_test.dart';

import 'package:app_movil/models/croquis.dart';

Map<String, dynamic> _trampaJson({String id = 'd1', String codigo = 'T-01', String? fotoUrl}) => {
  'id': id,
  'codigo': codigo,
  'tipo': 'cebadero',
  'lat': -33.4869,
  'lng': -70.5989,
  'sugerido_por_ia': false,
  'confirmado': true,
  'estado': 'activo',
  'foto_url': fotoUrl,
};

void main() {
  test('Trampa con foto guarda la dirección relativa de la foto', () {
    final trampa = DispositivoTrampa.fromJson(_trampaJson(fotoUrl: '/dispositivos-trampa/d1/foto?v=abc12345'));
    expect(trampa.fotoUrl, '/dispositivos-trampa/d1/foto?v=abc12345');
  });

  test('Trampa sin foto (o de un backend antiguo sin el campo) no rompe la app', () {
    expect(DispositivoTrampa.fromJson(_trampaJson()).fotoUrl, isNull);
    final sinCampo = _trampaJson()..remove('foto_url');
    expect(DispositivoTrampa.fromJson(sinCampo).fotoUrl, isNull);
  });

  test('Croquis recién creado sin trampas', () {
    final croquis = Croquis.fromJson({
      'id': 'k1',
      'visita_id': 'v1',
      'cliente_id': 'c1',
      'version': 1,
      'imagen_satelital_url': null,
      'sugerido_por_ia': false,
      'validado_por_operador': false,
      'dispositivos': <dynamic>[],
    });
    expect(croquis.dispositivos, isEmpty);
  });

  test('Agregar una trampa al croquis conserva las anteriores', () {
    final croquis = Croquis.fromJson({
      'id': 'k1',
      'visita_id': 'v1',
      'cliente_id': 'c1',
      'version': 2,
      'imagen_satelital_url': null,
      'sugerido_por_ia': false,
      'validado_por_operador': false,
      'dispositivos': [_trampaJson()],
    });
    final nueva = DispositivoTrampa.fromJson(_trampaJson(id: 'd2', codigo: 'T-02'));
    final actualizado = croquis.copyWithDispositivos([...croquis.dispositivos, nueva]);
    expect(actualizado.dispositivos.map((d) => d.codigo), ['T-01', 'T-02']);
    expect(actualizado.version, 2);
    expect(croquis.dispositivos, hasLength(1)); // el original no cambia
  });

  test('Sugerencia de la IA trae el croquis, el resumen y las advertencias', () {
    final sugerencia = SugerenciaCroquis.fromJson({
      'id': 'k1',
      'visita_id': 'v1',
      'cliente_id': 'c1',
      'version': 1,
      'imagen_satelital_url': 'https://server.arcgisonline.com/x',
      'sugerido_por_ia': true,
      'validado_por_operador': false,
      'dispositivos': [
        {..._trampaJson(), 'sugerido_por_ia': true, 'confirmado': false},
      ],
      'origen': 'ia',
      'resumen': 'Cebaderos en el perímetro.',
      'advertencias': ['No se ve la bodega.'],
    });
    expect(sugerencia.origen, 'ia');
    expect(sugerencia.resumen, 'Cebaderos en el perímetro.');
    expect(sugerencia.advertencias, ['No se ve la bodega.']);
    expect(sugerencia.croquis.dispositivos.single.confirmado, isFalse);
  });

  test('Sugerencia por reglas sin resumen ni advertencias', () {
    final sugerencia = SugerenciaCroquis.fromJson({
      'id': 'k1',
      'visita_id': 'v1',
      'cliente_id': 'c1',
      'version': 1,
      'imagen_satelital_url': null,
      'sugerido_por_ia': true,
      'validado_por_operador': false,
      'dispositivos': <dynamic>[],
      'origen': 'reglas',
      'resumen': null,
    });
    expect(sugerencia.resumen, isNull);
    expect(sugerencia.advertencias, isEmpty);
  });
}
