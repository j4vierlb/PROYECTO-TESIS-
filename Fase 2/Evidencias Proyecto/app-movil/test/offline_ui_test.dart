// Pruebas de pantalla del modo offline: la franja de conexión y el mensaje al
// guardar un cambio sin señal.

import 'package:app_movil/offline/sync_service.dart';
import 'package:app_movil/screens/visita_detalle_screen.dart';
import 'package:app_movil/widgets/sync_banner.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'support/offline_fakes.dart';

Widget conBanner(SyncService sync) => MaterialApp(home: Scaffold(body: Column(children: [SyncBanner(sync: sync)])));

void main() {
  group('Franja de conexión', () {
    testWidgets('no aparece cuando todo está en orden', (tester) async {
      final e = Entorno();
      await tester.pumpWidget(conBanner(e.sync));
      expect(find.textContaining('Sin conexión'), findsNothing);
      expect(find.textContaining('por enviar'), findsNothing);
    });

    testWidgets('sin señal muestra el contador y, al volver, "Enviar ahora" lo vacía', (tester) async {
      final e = Entorno();
      await tester.runAsync(e.prepararDia);
      await tester.pumpWidget(conBanner(e.sync));

      e.remote.online = false;
      await tester.runAsync(() => e.client.updateVisita(visitaId, estado: 'en_curso'));
      await tester.pump();
      expect(find.text('Sin conexión · 1 cambio por enviar'), findsOneWidget);
      expect(find.text('Enviar ahora'), findsOneWidget);

      e.remote.online = true;
      await tester.tap(find.text('Enviar ahora'));
      await tester.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 50)));
      await tester.pump();

      expect(e.visitaServidor.estado, 'en_curso');
      expect(find.textContaining('por enviar'), findsNothing);
      expect(find.textContaining('Sin conexión'), findsNothing);
    });

    testWidgets('varios cambios se cuentan en plural', (tester) async {
      final e = Entorno();
      await tester.runAsync(e.prepararDia);
      await tester.pumpWidget(conBanner(e.sync));
      e.remote.online = false;
      await tester.runAsync(() async {
        await e.client.updateVisita(visitaId, estado: 'en_curso');
        await e.client.updateVisita(visitaId, notas: 'x');
      });
      await tester.pump();
      expect(find.text('Sin conexión · 2 cambios por enviar'), findsOneWidget);
    });

    testWidgets('un cambio descartado por conflicto se avisa y se puede cerrar', (tester) async {
      final e = Entorno();
      await tester.runAsync(e.prepararDia);
      await tester.pumpWidget(conBanner(e.sync));
      e.remote.online = false;
      await tester.runAsync(() => e.client.updateVisita(visitaId, estado: 'en_curso'));
      e.remote.visitas[visitaId] = visita(visitaId, estado: 'cancelada');
      e.remote.online = true;
      await tester.runAsync(e.sync.flush);
      await tester.pump();

      expect(find.textContaining('No se pudo iniciar la visita'), findsOneWidget);
      await tester.tap(find.text('Entendido'));
      await tester.pump();
      expect(find.textContaining('No se pudo iniciar la visita'), findsNothing);
    });
  });

  group('Detalle de la visita sin señal', () {
    testWidgets('iniciar visita sin señal lo muestra en curso y avisa que quedó en el teléfono', (tester) async {
      final e = Entorno();
      await tester.runAsync(e.prepararDia);
      e.remote.online = false;

      await tester.pumpWidget(MaterialApp(home: VisitaDetalleScreen(visitaId: visitaId, apiClient: e.client)));
      await tester.pump();
      await tester.pump();
      expect(find.text('Restaurante Don José'), findsOneWidget); // viene de la copia guardada

      await tester.runAsync(() async {
        await tester.tap(find.text('Iniciar visita'));
        await Future<void>.delayed(const Duration(milliseconds: 50));
      });
      await tester.pump();
      await tester.pump();

      expect(find.text('Guardado en el teléfono. Se enviará cuando haya señal.'), findsOneWidget);
      expect(find.text('Completar visita'), findsOneWidget); // ya está en curso
      expect(e.visitaServidor.estado, 'agendada');
      expect(e.sync.status.value.pending, 1);
    });

    testWidgets('con señal el mensaje es el normal, sin hablar del teléfono', (tester) async {
      final e = Entorno();
      await tester.runAsync(e.prepararDia);

      await tester.pumpWidget(MaterialApp(home: VisitaDetalleScreen(visitaId: visitaId, apiClient: e.client)));
      await tester.pump();
      await tester.pump();
      await tester.runAsync(() async {
        await tester.tap(find.text('Iniciar visita'));
        await Future<void>.delayed(const Duration(milliseconds: 50));
      });
      await tester.pump();
      await tester.pump();

      expect(find.text('Visita iniciada'), findsOneWidget);
      expect(find.textContaining('Guardado en el teléfono'), findsNothing);
      expect(e.visitaServidor.estado, 'en_curso');
    });
  });
}
