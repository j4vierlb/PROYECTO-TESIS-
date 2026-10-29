// Etiquetas de día de la lista de próximas visitas.

import 'package:app_movil/utils/formato.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  // "Hoy" para estas pruebas: martes 27 de octubre de 2026, a mediodía.
  final hoy = DateTime(2026, 10, 27, 12);

  // Una visita el día indicado, a las 10:00 hora local, entregada en UTC como
  // la entrega el backend.
  DateTime visita(int mes, int dia, [int hora = 10]) => DateTime(2026, mes, dia, hora).toUtc();

  test('hoy, mañana y pasado mañana tienen nombre propio', () {
    expect(etiquetaDia(visita(10, 27), hoy: hoy), 'Hoy');
    expect(etiquetaDia(visita(10, 28), hoy: hoy), 'Mañana');
    expect(etiquetaDia(visita(10, 29), hoy: hoy), 'Pasado mañana');
  });

  test('más adelante se usa el día de la semana y la fecha', () {
    expect(etiquetaDia(visita(10, 30), hoy: hoy), 'Viernes 30 de octubre');
    expect(etiquetaDia(visita(11, 2), hoy: hoy), 'Lunes 2 de noviembre');
    expect(etiquetaDia(visita(12, 25), hoy: hoy), 'Viernes 25 de diciembre');
  });

  test('la hora de la visita no cambia el día', () {
    expect(etiquetaDia(visita(10, 28, 0), hoy: hoy), 'Mañana');
    expect(etiquetaDia(visita(10, 28, 23), hoy: hoy), 'Mañana');
  });

  test('la hora de "hoy" tampoco cambia la comparación', () {
    final madrugada = DateTime(2026, 10, 27, 0, 5);
    final noche = DateTime(2026, 10, 27, 23, 55);
    expect(etiquetaDia(visita(10, 28), hoy: madrugada), 'Mañana');
    expect(etiquetaDia(visita(10, 28), hoy: noche), 'Mañana');
  });

  test('funciona al cruzar fin de mes y de año', () {
    final finDeAnio = DateTime(2026, 12, 31, 18);
    expect(etiquetaDia(DateTime(2027, 1, 1, 9).toUtc(), hoy: finDeAnio), 'Mañana');
    expect(etiquetaDia(DateTime(2027, 1, 2, 9).toUtc(), hoy: finDeAnio), 'Pasado mañana');
    expect(etiquetaDia(DateTime(2027, 1, 4, 9).toUtc(), hoy: finDeAnio), 'Lunes 4 de enero');
  });

  test('funciona en el cambio de horario (el día no se corre una hora)', () {
    // Primer domingo de septiembre en Chile: el reloj adelanta una hora.
    final antes = DateTime(2026, 9, 5, 20);
    expect(etiquetaDia(DateTime(2026, 9, 6, 10).toUtc(), hoy: antes), 'Mañana');
    expect(etiquetaDia(DateTime(2026, 9, 7, 10).toUtc(), hoy: antes), 'Pasado mañana');
  });
}
