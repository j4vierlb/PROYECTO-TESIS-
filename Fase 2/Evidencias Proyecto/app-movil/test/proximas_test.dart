// Pestaña "Próximas": cliente de la API, modo offline y pantalla.

import 'dart:convert';

import 'package:app_movil/models/visita.dart';
import 'package:app_movil/screens/home_screen.dart';
import 'package:app_movil/screens/proximas_screen.dart';
import 'package:app_movil/services/api_client.dart';
import 'package:app_movil/theme/app_theme.dart';
import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'support/offline_fakes.dart';

/// "Hoy" de las pruebas de pantalla: martes 27 de octubre de 2026.
final hoy = DateTime(2026, 10, 27, 12);

/// Visita de `cliente` el día/hora local indicados (se entrega en UTC).
Visita enDia(String id, String cliente, int dia, int hora, {int mes = 10}) {
  final json = visita(id).toJson();
  json['fecha_hora'] = DateTime(2026, mes, dia, hora).toUtc().toIso8601String();
  (json['cliente'] as Map<String, dynamic>)['nombre'] = cliente;
  return Visita.fromJson(json);
}

String tokenDePrueba() {
  final payload = base64Url
      .encode(utf8.encode(jsonEncode({
        'sub': 'tecnico-1',
        'exp': DateTime.now().add(const Duration(hours: 8)).millisecondsSinceEpoch ~/ 1000,
      })))
      .replaceAll('=', '');
  return 'eyJhbGciOiJIUzI1NiJ9.$payload.firma';
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('Cliente de la API', () {
    setUp(() {
      FlutterSecureStorage.setMockInitialValues({'access_token': tokenDePrueba(), 'refresh_token': 'r'});
    });

    test('pide /visitas-proximas con los días y convierte la respuesta', () async {
      late Uri pedida;
      final api = ApiClient(
        client: MockClient((request) async {
          pedida = request.url;
          return http.Response(jsonEncode([enDia('v-1', 'Cliente A', 28, 10).toJson()]), 200);
        }),
      );
      final visitas = await api.fetchVisitasProximas(dias: 30);
      expect(pedida.path, '/operadores/me/visitas-proximas');
      expect(pedida.queryParameters['dias'], '30');
      expect(visitas.single.cliente.nombre, 'Cliente A');
    });

    test('por defecto mira 14 días', () async {
      late Uri pedida;
      final api = ApiClient(
        client: MockClient((request) async {
          pedida = request.url;
          return http.Response('[]', 200);
        }),
      );
      expect(await api.fetchVisitasProximas(), isEmpty);
      expect(pedida.queryParameters['dias'], '14');
    });
  });

  group('Modo offline', () {
    test('con señal guarda la lista; sin señal entrega la última guardada', () async {
      final e = Entorno();
      e.remote.proximas.addAll([enDia('v-1', 'Cliente A', 28, 10), enDia('v-2', 'Cliente B', 29, 11)]);

      expect((await e.client.fetchVisitasProximas()).length, 2);
      e.remote.online = false;
      final guardada = await e.client.fetchVisitasProximas();

      expect(guardada.map((v) => v.cliente.nombre), ['Cliente A', 'Cliente B']);
      expect(e.sync.status.value.offline, isTrue);
    });

    test('sin señal y sin nada guardado el error llega a la pantalla', () async {
      final e = Entorno();
      e.remote.online = false;
      await expectLater(e.client.fetchVisitasProximas(), throwsA(isA<Exception>()));
    });

    test('abrir una visita de la lista funciona sin señal', () async {
      final e = Entorno();
      e.remote.proximas.add(enDia('v-1', 'Cliente A', 28, 10));
      await e.client.fetchVisitasProximas();
      e.remote.online = false;
      expect((await e.client.fetchVisita('v-1')).cliente.nombre, 'Cliente A');
    });

    test('un cambio hecho sin señal se ve en la lista de próximas', () async {
      final e = Entorno();
      final cercana = enDia(visitaId, 'Cliente A', 28, 10);
      e.remote.visitas[visitaId] = cercana;
      e.remote.proximas.add(cercana);
      await e.client.fetchVisitasProximas();
      e.remote.online = false;

      await e.client.updateVisita(visitaId, notas: 'Llevar escalera');
      final lista = await e.client.fetchVisitasProximas();

      expect(lista.single.notas, 'Llevar escalera');
    });

    test('al cambiar de cuenta no se ve la lista de la anterior', () async {
      final e = Entorno();
      e.remote.proximas.add(enDia('v-1', 'Cliente A', 28, 10));
      await e.client.fetchVisitasProximas();

      e.owner = 'tecnico-2';
      e.remote.online = false;
      await expectLater(e.client.fetchVisitasProximas(), throwsA(isA<Exception>()));
    });
  });

  group('Pantalla', () {
    Future<void> abrir(WidgetTester tester, Entorno e) async {
      await tester.pumpWidget(MaterialApp(
        theme: AppTheme.light,
        home: ProximasScreen(apiClient: e.client, hoy: hoy),
      ));
      await tester.pump();
      await tester.pump();
    }

    testWidgets('agrupa por día con su encabezado', (tester) async {
      final e = Entorno();
      e.remote.proximas.addAll([
        enDia('v-1', 'Cliente A', 28, 9),
        enDia('v-2', 'Cliente B', 28, 15),
        enDia('v-3', 'Cliente C', 29, 10),
        enDia('v-4', 'Cliente D', 30, 10),
      ]);
      await abrir(tester, e);

      expect(find.text('Próximas visitas'), findsOneWidget);
      expect(find.text('Mañana'), findsOneWidget); // un solo encabezado para dos visitas
      expect(find.text('Pasado mañana'), findsOneWidget);
      expect(find.text('Viernes 30 de octubre'), findsOneWidget);
      for (final cliente in ['Cliente A', 'Cliente B', 'Cliente C', 'Cliente D']) {
        expect(find.text(cliente), findsOneWidget);
      }
      expect(find.text('09:00'), findsOneWidget);
      expect(find.text('15:00'), findsOneWidget);
    });

    testWidgets('el orden de la lista es el de las visitas', (tester) async {
      final e = Entorno();
      e.remote.proximas.addAll([enDia('v-1', 'Cliente A', 28, 9), enDia('v-2', 'Cliente B', 29, 10)]);
      await abrir(tester, e);

      final a = tester.getTopLeft(find.text('Cliente A')).dy;
      final b = tester.getTopLeft(find.text('Cliente B')).dy;
      expect(a, lessThan(b));
      expect(tester.getTopLeft(find.text('Mañana')).dy, lessThan(a));
    });

    testWidgets('sin visitas muestra un mensaje', (tester) async {
      final e = Entorno();
      await abrir(tester, e);
      expect(find.text('No tienes visitas agendadas para los próximos días'), findsOneWidget);
    });

    testWidgets('si falla la carga y no hay copia, avisa', (tester) async {
      final e = Entorno();
      e.remote.failWithStatus = 400;
      await abrir(tester, e);
      expect(find.text('Error 400'), findsOneWidget);
    });

    testWidgets('sin señal muestra la última lista guardada', (tester) async {
      final e = Entorno();
      e.remote.proximas.add(enDia('v-1', 'Cliente A', 28, 10));
      await e.client.fetchVisitasProximas();
      e.remote.online = false;
      await abrir(tester, e);
      expect(find.text('Cliente A'), findsOneWidget);
    });

    testWidgets('tocar una visita abre su detalle', (tester) async {
      final e = Entorno();
      final v = enDia(visitaId, 'Cliente A', 28, 10);
      e.remote.visitas[visitaId] = v;
      e.remote.proximas.add(v);
      await tester.runAsync(() => e.client.fetchVisitasProximas());
      await abrir(tester, e);

      await tester.tap(find.text('Cliente A'));
      await tester.pump();
      await tester.pump();
      await tester.pump();

      expect(find.text('Detalle de visita'), findsOneWidget);
    });
  });

  group('Barra inferior', () {
    testWidgets('la pestaña "Próximas" muestra su pantalla y se puede volver a "Hoy"', (tester) async {
      await tester.pumpWidget(MaterialApp(theme: AppTheme.light, home: const HomeScreen()));
      expect(find.text('Agenda del día'), findsOneWidget);
      expect(find.text('Próximas'), findsOneWidget); // la etiqueta de la pestaña

      await tester.tap(find.text('Próximas'));
      await tester.pump();
      expect(find.text('Próximas visitas'), findsOneWidget);
      expect(find.text('Agenda del día'), findsNothing);

      await tester.tap(find.text('Hoy'));
      await tester.pump();
      expect(find.text('Agenda del día'), findsOneWidget);
    });
  });
}
