// =============================================================================
// test/widget_test.dart — Prueba de la pantalla de inicio
// -----------------------------------------------------------------------------
// Las pruebas se corren con: flutter test
// Dibujan la app en memoria (sin teléfono) y revisan que aparezca lo esperado.
// =============================================================================

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:app_movil/main.dart';

void main() {
  testWidgets('Muestra la pantalla de login al arrancar', (WidgetTester tester) async {
    // Dibuja la app completa, tal como se ve al abrirla.
    await tester.pumpWidget(const KillBichosApp());

    // expect(...) = "esto debe cumplirse"; si no, la prueba falla.
    expect(find.text('Iniciar sesión'), findsOneWidget);
    expect(find.widgetWithText(TextFormField, 'Usuario (email)'), findsOneWidget);
    expect(find.widgetWithText(TextFormField, 'Clave'), findsOneWidget);
    expect(find.text('Ingresar'), findsOneWidget);
  });
}
