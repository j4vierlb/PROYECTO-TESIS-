import 'package:app_movil/widgets/location_aware_map.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets(
    'Sin cliente ni trampas no construye un mapa ni inventa un centro',
    (tester) async {
      var builds = 0;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: LocationAwareMap(
              clientLocated: false,
              trapsLocated: false,
              mapBuilder: (_) {
                builds++;
                return const Text('Mapa nativo');
              },
            ),
          ),
        ),
      );
      expect(builds, 0);
      expect(find.text('Sin ubicación registrada'), findsOneWidget);
      expect(
        find.textContaining('Corrige calle, número y comuna'),
        findsOneWidget,
      );
      expect(find.text('Mapa nativo'), findsNothing);
    },
  );

  testWidgets('Si solo hay trampas muestra su mapa con aviso persistente', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: LocationAwareMap(
            clientLocated: false,
            trapsLocated: true,
            mapBuilder: (_) => const Text('Mapa de trampas'),
          ),
        ),
      ),
    );
    expect(find.text('Mapa de trampas'), findsOneWidget);
    expect(
      find.textContaining('únicamente las trampas registradas'),
      findsOneWidget,
    );
    expect(find.text('Sin ubicación registrada'), findsNothing);
    expect(find.byType(TextButton), findsNothing);
  });

  for (final traps in [false, true]) {
    testWidgets(
      'Con cliente ubicado conserva el mapa sin advertencia: trampas=$traps',
      (tester) async {
        await tester.pumpWidget(
          MaterialApp(
            home: Scaffold(
              body: LocationAwareMap(
                clientLocated: true,
                trapsLocated: traps,
                mapBuilder: (_) => const Text('Mapa del cliente'),
              ),
            ),
          ),
        );
        expect(find.text('Mapa del cliente'), findsOneWidget);
        expect(find.textContaining('pendiente de confirmar'), findsNothing);
        expect(find.text('Sin ubicación registrada'), findsNothing);
      },
    );
  }

  testWidgets('El aviso sin mapa se adapta a pantalla pequeña y texto grande', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(320, 240));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(
      MaterialApp(
        builder: (context, child) => MediaQuery(
          data: MediaQuery.of(context)
              .copyWith(textScaler: const TextScaler.linear(2)),
          child: child!,
        ),
        home: Scaffold(
          body: LocationAwareMap(
            clientLocated: false,
            trapsLocated: false,
            mapBuilder: (_) => const Text('No debe aparecer'),
          ),
        ),
      ),
    );
    expect(tester.takeException(), isNull);
    expect(find.byType(SingleChildScrollView), findsOneWidget);
  });
}
