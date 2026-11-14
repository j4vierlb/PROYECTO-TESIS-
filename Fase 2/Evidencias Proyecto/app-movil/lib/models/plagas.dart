// =============================================================================
// models/plagas.dart — Plagas que controla Kill Bichos
// -----------------------------------------------------------------------------
// Datos fijos tomados del sitio de la empresa (https://killbichos.cl/, 14 de
// noviembre de 2026). Son los mismos del panel web (frontend/src/public-site-config.js):
// si cambian allá, cambiarlos aquí. No vienen del servidor, así que se ven también sin señal.
// =============================================================================

class GrupoPlaga {
  final String nombre;
  final String ejemplos;

  const GrupoPlaga(this.nombre, this.ejemplos);
}

const List<GrupoPlaga> gruposPlagas = [
  GrupoPlaga('Voladores', 'Moscas, mosquitos, polillas y otros insectos voladores.'),
  GrupoPlaga('Rastreros', 'Cucarachas, pulgas, hormigas, tijeretas y similares.'),
  GrupoPlaga('Arácnidos', 'Arañas, garrapatas y ácaros.'),
];

const String garantiaTitulo = 'Garantía de 30 días';
const String garantiaTexto =
    'Las plagas rastreras y los arácnidos deben desaparecer casi al 100 %, y las voladoras '
    'bajan su población considerablemente. Si el cliente no queda satisfecho, puede pedir '
    'reforzar una zona particular o una re-aplicación total.';

const String seguridadTitulo = 'Productos seguros';
const String seguridadTexto =
    'Los productos son seguros para las personas, las mascotas y las plantas, y no manchan los muros.';
