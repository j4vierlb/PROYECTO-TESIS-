// =============================================================================
// test/historial_test.dart — Pruebas del historial de visitas
// -----------------------------------------------------------------------------
// Revisa que el modelo lea bien los datos del historial y que la barra
// inferior cambie entre "Hoy" e "Historial".
// =============================================================================

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:app_movil/models/visita.dart';
import 'package:app_movil/theme/app_theme.dart';
import 'package:app_movil/screens/home_screen.dart';

/// JSON de ejemplo igual al que entrega el backend. Si se pasa
/// `dispositivos`, se agrega el campo del historial (dispositivos_instalados).
Map<String, dynamic> _visitaJson({int? dispositivos}) => {
      'id': '99999999-0000-0000-0000-000000000001',
      'cliente': {
        'id': '55555555-5555-5555-5555-555555555555',
        'nombre': 'Bodega Central Ltda.',
        'telefono_whatsapp': '+56922222222',
        'direccion': 'Av. Departamental 567, Macul',
        'lat': -33.4905,
        'lng': -70.602,
      },
      'operador_id': '33333333-3333-3333-3333-333333333333',
      'fecha_hora': '2026-09-19T14:00:00Z',
      'estado': 'completada',
      'origen_agendamiento': 'whatsapp_ia',
      'notas': 'Instalación inicial',
      'dispositivos_instalados': ?dispositivos,
    };

void main() {
  test('Visita.fromJson lee dispositivos_instalados del historial', () {
    final visita = Visita.fromJson(_visitaJson(dispositivos: 3));
    expect(visita.dispositivosInstalados, 3);
    // La fecha con "Z" al final debe interpretarse como UTC.
    expect(visita.fechaHora.isUtc, isTrue);
  });

  test('Visita.fromJson funciona sin dispositivos_instalados (agenda)', () {
    // La agenda no manda ese campo: debe quedar en null sin fallar.
    final visita = Visita.fromJson(_visitaJson());
    expect(visita.dispositivosInstalados, isNull);
  });

  testWidgets('La barra inferior cambia de Hoy a Historial', (tester) async {
    await tester.pumpWidget(MaterialApp(theme: AppTheme.light, home: const HomeScreen()));

    // Al abrir se ve la agenda.
    expect(find.text('Agenda del día'), findsOneWidget);

    // Toca la pestaña "Historial" y redibuja (pump).
    await tester.tap(find.text('Historial'));
    await tester.pump();

    expect(find.text('Historial de visitas'), findsOneWidget);
    expect(find.text('Agenda del día'), findsNothing);
  });
}
