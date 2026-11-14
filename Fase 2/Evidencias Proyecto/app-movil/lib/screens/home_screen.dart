// =============================================================================
// screens/home_screen.dart — Pantalla principal (después del login)
// -----------------------------------------------------------------------------
// Solo contiene la barra inferior con tres pestañas y muestra la pantalla que
// corresponde: "Hoy" (AgendaScreen), "Próximas" (ProximasScreen) o
// "Historial" (HistorialScreen).
// =============================================================================

import 'package:flutter/material.dart';

import 'agenda_screen.dart';
import 'historial_screen.dart';
import 'proximas_screen.dart';

/// Pantalla principal después del login, con barra inferior para cambiar
/// entre la agenda de hoy y el historial. Cada pestaña se vuelve a construir
/// al seleccionarla, así siempre muestra datos frescos (por ejemplo, una
/// visita recién completada aparece de inmediato en el historial).
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  // Pestaña seleccionada: 0 = Hoy, 1 = Próximas, 2 = Historial.
  int _index = 0;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      // Cada pestaña es una pantalla completa, con su propia barra superior.
      body: switch (_index) {
        0 => const AgendaScreen(),
        1 => const ProximasScreen(),
        _ => const HistorialScreen(),
      },
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        // Al tocar una pestaña se guarda su número y se redibuja.
        onDestinationSelected: (index) => setState(() => _index = index),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.today_outlined),
            selectedIcon: Icon(Icons.today), // ícono relleno cuando está activa
            label: 'Hoy',
          ),
          NavigationDestination(
            icon: Icon(Icons.event_outlined),
            selectedIcon: Icon(Icons.event),
            label: 'Próximas',
          ),
          NavigationDestination(
            icon: Icon(Icons.history),
            label: 'Historial',
          ),
        ],
      ),
    );
  }
}
