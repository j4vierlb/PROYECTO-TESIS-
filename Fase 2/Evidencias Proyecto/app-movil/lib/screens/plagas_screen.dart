// =============================================================================
// screens/plagas_screen.dart — Plagas que controla la empresa (pestaña "Plagas")
// -----------------------------------------------------------------------------
// Pantalla informativa y fija: le sirve al técnico para explicarle al cliente qué
// plagas se atienden, la garantía y la seguridad de los productos. No usa el
// servidor, por eso funciona igual sin señal.
// =============================================================================

import 'package:flutter/material.dart';

import '../models/plagas.dart';
import '../widgets/company_brand.dart';
import '../widgets/logout_button.dart';

class PlagasScreen extends StatelessWidget {
  const PlagasScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final textos = Theme.of(context).textTheme;
    return Scaffold(
      appBar: AppBar(
        title: const CompanyTitle('Plagas'),
        actions: const [LogoutButton()],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text('Qué plagas controlamos', style: textos.titleLarge),
          const SizedBox(height: 12),
          for (final grupo in gruposPlagas)
            Card(
              child: ListTile(
                title: Text(grupo.nombre, style: textos.titleMedium),
                subtitle: Text(grupo.ejemplos),
              ),
            ),
          const SizedBox(height: 16),
          Card(
            child: ListTile(
              leading: const Icon(Icons.verified_outlined),
              title: const Text(garantiaTitulo),
              subtitle: const Text(garantiaTexto),
            ),
          ),
          Card(
            child: ListTile(
              leading: const Icon(Icons.health_and_safety_outlined),
              title: const Text(seguridadTitulo),
              subtitle: const Text(seguridadTexto),
            ),
          ),
        ],
      ),
    );
  }
}
