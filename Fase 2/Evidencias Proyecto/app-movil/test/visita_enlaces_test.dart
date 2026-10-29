// Pantalla de detalle de la visita: tocar la dirección o el teléfono abre
// mapas, el marcador o WhatsApp. No se abre nada de verdad: la función que abre
// los enlaces se reemplaza por una que anota lo que se le pidió.

import 'package:app_movil/models/visita.dart';
import 'package:app_movil/screens/visita_detalle_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'support/offline_fakes.dart';

class Abridor {
  final List<Uri> abiertos = [];
  bool resultado = true;
  Future<bool> call(Uri uri) async {
    abiertos.add(uri);
    return resultado;
  }
}

/// `mapa` es quien abre el mapa (dentro de la app); si no se indica, el mismo
/// `abridor` anota también lo del mapa.
Future<void> abrirDetalle(WidgetTester tester, Entorno e, Abridor abridor, {Abridor? mapa}) async {
  await tester.runAsync(e.prepararDia);
  await tester.pumpWidget(MaterialApp(
    home: VisitaDetalleScreen(
      visitaId: visitaId,
      apiClient: e.client,
      abrirEnlace: abridor.call,
      abrirMapa: (mapa ?? abridor).call,
    ),
  ));
  await tester.pump();
  await tester.pump();
}

/// Cambia los datos del cliente de la visita en el servidor simulado.
void clienteConDatos(Entorno e, Map<String, dynamic> cambios, {String estado = 'agendada'}) {
  final json = visita(visitaId, estado: estado).toJson();
  (json['cliente'] as Map<String, dynamic>).addAll(cambios);
  e.remote.visitas[visitaId] = Visita.fromJson(json);
}

void main() {
  testWidgets('"Cómo llegar" abre la ruta a las coordenadas del cliente', (tester) async {
    final e = Entorno();
    final abridor = Abridor();
    await abrirDetalle(tester, e, abridor);

    await tester.tap(find.byTooltip('Cómo llegar'));
    await tester.pump();

    final uri = abridor.abiertos.single;
    expect(uri.host, 'www.google.com');
    expect(uri.queryParameters['destination'], '-33.48,-70.59');
  });

  testWidgets('tocar el texto de la dirección hace lo mismo', (tester) async {
    final e = Entorno();
    final abridor = Abridor();
    await abrirDetalle(tester, e, abridor);

    await tester.tap(find.text('Av. Macul 123'));
    await tester.pump();

    expect(abridor.abiertos.single.queryParameters['destination'], '-33.48,-70.59');
  });

  testWidgets('sin coordenadas navega a la dirección escrita', (tester) async {
    final e = Entorno();
    clienteConDatos(e, {'lat': null, 'lng': null, 'direccion': 'Avenida Libertad 1000, Viña del Mar'});
    final abridor = Abridor();
    await abrirDetalle(tester, e, abridor);

    await tester.tap(find.byTooltip('Cómo llegar'));
    await tester.pump();

    expect(abridor.abiertos.single.queryParameters['destination'], 'Avenida Libertad 1000, Viña del Mar');
  });

  testWidgets('"Llamar" abre el marcador con el teléfono del cliente', (tester) async {
    final e = Entorno();
    final abridor = Abridor();
    await abrirDetalle(tester, e, abridor);

    await tester.tap(find.byTooltip('Llamar'));
    await tester.pump();

    expect(abridor.abiertos.single.toString(), 'tel:+56911111111');
  });

  testWidgets('"Escribir por WhatsApp" abre el chat con el cliente', (tester) async {
    final e = Entorno();
    final abridor = Abridor();
    await abrirDetalle(tester, e, abridor);

    await tester.tap(find.byTooltip('Escribir por WhatsApp'));
    await tester.pump();

    expect(abridor.abiertos.single.toString(), 'https://wa.me/56911111111');
  });

  testWidgets('sin dirección ni ubicación avisa y no abre nada', (tester) async {
    final e = Entorno();
    clienteConDatos(e, {'lat': null, 'lng': null, 'direccion': null});
    final abridor = Abridor();
    await abrirDetalle(tester, e, abridor);

    await tester.tap(find.byTooltip('Cómo llegar'));
    await tester.pump();

    expect(abridor.abiertos, isEmpty);
    expect(find.text('Este cliente no tiene dirección ni ubicación registrada'), findsOneWidget);
  });

  testWidgets('un teléfono inválido avisa y no abre nada', (tester) async {
    final e = Entorno();
    clienteConDatos(e, {'telefono_whatsapp': '12'});
    final abridor = Abridor();
    await abrirDetalle(tester, e, abridor);

    await tester.tap(find.byTooltip('Llamar'));
    await tester.pump();

    expect(abridor.abiertos, isEmpty);
    expect(find.text('El teléfono del cliente no es válido'), findsOneWidget);
  });

  testWidgets('si el teléfono no puede abrir el enlace, se lo dice al técnico', (tester) async {
    final e = Entorno();
    final abridor = Abridor()..resultado = false;
    await abrirDetalle(tester, e, abridor);

    await tester.tap(find.byTooltip('Cómo llegar'));
    await tester.pump();
    expect(find.text('No se pudo abrir el mapa'), findsOneWidget);

    await tester.tap(find.byTooltip('Escribir por WhatsApp'));
    await tester.pump();
    expect(find.text('No se pudo abrir WhatsApp'), findsOneWidget);
  });

  testWidgets('el mapa se abre dentro de la app y la llamada y WhatsApp fuera de ella', (tester) async {
    final e = Entorno();
    final fuera = Abridor();
    final dentro = Abridor();
    await abrirDetalle(tester, e, fuera, mapa: dentro);

    await tester.tap(find.byTooltip('Cómo llegar'));
    await tester.pump();
    await tester.tap(find.text('Av. Macul 123'));
    await tester.pump();
    await tester.tap(find.byTooltip('Llamar'));
    await tester.pump();
    await tester.tap(find.byTooltip('Escribir por WhatsApp'));
    await tester.pump();

    // Las dos formas de pedir el mapa lo abren dentro de la app...
    expect(dentro.abiertos.length, 2);
    expect(dentro.abiertos.every((uri) => uri.host == 'www.google.com'), isTrue);
    // ...y solo la llamada y WhatsApp salen de ella.
    expect(fuera.abiertos.map((uri) => uri.scheme == 'tel' || uri.host == 'wa.me'), [true, true]);
  });

  testWidgets('en una visita completada los botones también funcionan', (tester) async {
    final e = Entorno();
    clienteConDatos(e, {}, estado: 'completada');
    final abridor = Abridor();
    await abrirDetalle(tester, e, abridor);

    await tester.tap(find.byTooltip('Llamar'));
    await tester.pump();

    expect(abridor.abiertos.single.scheme, 'tel');
  });
}
