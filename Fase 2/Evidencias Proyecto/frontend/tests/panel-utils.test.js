import { describe, expect, it } from 'vitest'
import { addDays, chileDate, chileTime, chileDateTimeToUtc, clientLocation, clientPayload, visitPayload } from '../src/panel-utils.js'

describe('PANEL-HORA: fecha y hora de Chile, independiente del navegador', () => {
  it.each([
    ['2026-09-30T01:30:00Z', '2026-09-29', '22:30'],
    ['2026-07-16T01:30:00Z', '2026-07-15', '21:30'],
    ['2026-09-30T03:00:00Z', '2026-09-30', '00:00'],
    ['2026-09-29T10:00:00-03:00', '2026-09-29', '10:00'],
  ])('muestra %s en hora de Chile', (instant, day, hour) => {
    expect(chileDate(new Date(instant))).toBe(day)
    expect(chileTime(instant)).toBe(hour)
  })
  it.each([
    ['2026-09-29T10:00', '2026-09-29T13:00:00.000Z'],
    ['2026-07-15T10:00', '2026-07-15T14:00:00.000Z'],
    ['2026-09-29T23:30', '2026-09-30T02:30:00.000Z'],
    ['2026-09-06T01:00', '2026-09-06T04:00:00.000Z'],
  ])('guarda %s como UTC y conserva su hora local', (wall, utc) => {
    expect(chileDateTimeToUtc(wall)).toBe(utc)
    expect(chileTime(utc)).toBe(wall.slice(11))
  })
  it('rechaza una hora inexistente al adelantar el reloj', () => {
    expect(() => chileDateTimeToUtc('2026-09-06T00:30')).toThrow('no existe')
  })
  it('rechaza un formato inválido', () => {
    expect(() => chileDateTimeToUtc('')).toThrow('no válidas')
    expect(() => chileDateTimeToUtc('2026-02-31T10:00')).toThrow('no válidas')
  })
  it.each([
    ['2026-12-31', 1, '2027-01-01'],
    ['2026-03-01', -1, '2026-02-28'],
    ['2026-09-06', -1, '2026-09-05'],
    ['2026-04-04', 1, '2026-04-05'],
  ])('navega días sin saltos: %s %+i', (day, change, expected) => {
    expect(addDays(day, change)).toBe(expected)
  })
})

describe('PANEL-CLIENTES: ubicación opcional', () => {
  it.each([{ lat: null, lng: null }, {}, { lat: -33.4, lng: null }])('muestra marcador sin coordenadas: %j', client => {
    expect(clientLocation(client)).toBe('Sin coordenadas')
  })
  it('cero es una coordenada válida', () => {
    expect(clientLocation({ lat: 0, lng: 0 })).toBe('0.0000, 0.0000')
  })
  it('conserva null al editar un cliente sin ubicación ni dirección', () => {
    expect(clientPayload({ direccion: '', lat: '', lng: '' })).toEqual({ direccion: null, lat: null, lng: null })
  })
  it('convierte coordenadas del formulario sin perder cero', () => {
    expect(clientPayload({ direccion: ' Macul ', lat: '0', lng: '-70.6' })).toEqual({ direccion: 'Macul', lat: 0, lng: -70.6 })
  })
  it('rechaza una coordenada incompleta', () => {
    expect(() => clientPayload({ direccion: 'Macul', lat: '0', lng: '' })).toThrow('ambas coordenadas')
  })
})

describe('PANEL-ASIGNACION: contrato UUID o null', () => {
  it('Sin asignar envía null, no cadena vacía', () => {
    expect(visitPayload({ operador_id: '', fecha_hora: '2026-09-29T10:00' }).operador_id).toBeNull()
  })
  it('conserva un operador elegido', () => {
    const id = '44444444-4444-4444-4444-444444444444'
    expect(visitPayload({ operador_id: id, fecha_hora: '2026-09-29T10:00' }).operador_id).toBe(id)
  })
})
