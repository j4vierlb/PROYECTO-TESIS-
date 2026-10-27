import 'package:app_movil/theme/app_theme.dart';
import 'package:app_movil/widgets/company_brand.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('Conserva la paleta compartida con iOS', () {
    expect(AppColors.yellow, const Color(0xFFF5C518));
    expect(AppColors.black, const Color(0xFF1A1A1A));
    expect(AppColors.background, const Color(0xFFF7F7F4));
    expect(AppTheme.light.colorScheme.primary, AppColors.yellow);
    expect(AppTheme.light.appBarTheme.backgroundColor, AppColors.black);
  });

  testWidgets(
    'El logo usa el archivo original completo y un nombre accesible',
    (tester) async {
      final semantics = tester.ensureSemantics();
      try {
        await tester.pumpWidget(
          const MaterialApp(home: Scaffold(body: CompanyLogo(size: 140))),
        );
        await tester.pumpAndSettle();
        final image = tester.widget<Image>(find.byType(Image));
        expect((image.image as AssetImage).assetName, CompanyLogo.asset);
        expect(image.fit, BoxFit.contain);
        expect(find.bySemanticsLabel(CompanyLogo.label), findsOneWidget);
        expect(tester.takeException(), isNull);
      } finally {
        semantics.dispose();
      }
    },
  );

  for (final title in [
    'Agenda del día',
    'Historial de visitas',
    'Detalle de visita',
    'Croquis',
  ]) {
    testWidgets('Cabecera mantiene logo y título: $title', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.light,
          home: Scaffold(appBar: AppBar(title: CompanyTitle(title))),
        ),
      );
      await tester.pumpAndSettle();
      expect(find.text(title), findsOneWidget);
      expect(find.byType(CompanyLogo), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  }

  testWidgets(
    'Cabecera pequeña con texto grande no desborda ni tapa acciones',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(320, 640));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      var pressed = false;
      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.light,
          builder: (context, child) => MediaQuery(
            data: MediaQuery.of(context)
                .copyWith(textScaler: const TextScaler.linear(1.8)),
            child: child!,
          ),
          home: Scaffold(
            appBar: AppBar(
              leading: const BackButton(),
              title: const CompanyTitle('Historial de visitas'),
              actions: [
                IconButton(
                  tooltip: 'Cerrar sesión',
                  onPressed: () => pressed = true,
                  icon: const Icon(Icons.logout),
                ),
              ],
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
      await tester.tap(find.byTooltip('Cerrar sesión'));
      expect(pressed, isTrue);
    },
  );
}
