// =============================================================================
// test/widget_test.dart — Prueba de la pantalla de inicio
// -----------------------------------------------------------------------------
// Las pruebas se corren con: flutter test
// Dibujan la app en memoria (sin teléfono) y revisan que aparezca lo esperado.
// =============================================================================

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:app_movil/main.dart';
import 'package:app_movil/screens/home_screen.dart';

void main() {
  testWidgets('Sin sesión guardada muestra la pantalla de login al arrancar', (WidgetTester tester) async {
    // Dibuja la app completa, tal como se ve al abrirla, simulando que no hay
    // ninguna sesión guardada en el teléfono.
    await tester.pumpWidget(KillBichosApp(restaurarSesion: () async => false));
    await tester.pumpAndSettle(); // espera a que termine de revisar la sesión

    // expect(...) = "esto debe cumplirse"; si no, la prueba falla.
    expect(find.text('Iniciar sesión'), findsOneWidget);
    expect(find.widgetWithText(TextFormField, 'Usuario (email)'), findsOneWidget);
    expect(find.widgetWithText(TextFormField, 'Clave'), findsOneWidget);
    expect(find.text('Ingresar'), findsOneWidget);
  });

  testWidgets('Con sesión guardada entra directo a la agenda, sin pedir la clave', (WidgetTester tester) async {
    await tester.pumpWidget(KillBichosApp(restaurarSesion: () async => true));
    await tester.pump(); // termina de revisar la sesión
    await tester.pump(); // dibuja la pantalla siguiente
    expect(find.byType(HomeScreen), findsOneWidget);
    expect(find.text('Ingresar'), findsNothing);
  });
}
