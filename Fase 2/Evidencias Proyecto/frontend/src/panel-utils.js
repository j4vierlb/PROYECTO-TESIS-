const CHILE_ZONE = 'America/Santiago'

export const chileDate = (value = new Date()) => value.toLocaleDateString('sv-SE', { timeZone: CHILE_ZONE })

export function addDays(value, days) {
  const [year, month, day] = value.split('-').map(Number)
  return new Date(Date.UTC(year, month - 1, day + days)).toLocaleDateString('sv-SE', { timeZone: 'UTC' })
}

export function chileTime(value) {
  return new Intl.DateTimeFormat('es-CL', {
    timeZone: CHILE_ZONE, hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
  }).format(new Date(value))
}

export function clientLocation(client) {
  return Number.isFinite(client.lat) && Number.isFinite(client.lng)
    ? `${client.lat.toFixed(4)}, ${client.lng.toFixed(4)}`
    : 'Sin coordenadas'
}

export function visitPayload(form) {
  return { ...form, operador_id: form.operador_id || null, fecha_hora: chileDateTimeToUtc(form.fecha_hora) }
}

// datetime-local no incluye zona. Resolver America/Santiago explícitamente
// evita depender de la zona del navegador y del horario de verano/invierno.
export function chileDateTimeToUtc(value) {
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})$/.exec(value)
  if (!match) throw new Error('Fecha y hora no válidas')
  const [, year, month, day, hour, minute] = match.map(Number)
  const desired = Date.UTC(year, month - 1, day, hour, minute)
  if (new Date(desired).toISOString().slice(0, 16) !== value) throw new Error('Fecha y hora no válidas')
  const formatter = new Intl.DateTimeFormat('sv-SE', {
    timeZone: CHILE_ZONE, year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23',
  })
  const wallTime = timestamp => {
    const parts = Object.fromEntries(formatter.formatToParts(new Date(timestamp)).map(p => [p.type, p.value]))
    return Date.UTC(+parts.year, +parts.month - 1, +parts.day, +parts.hour, +parts.minute, +parts.second)
  }
  let instant = desired
  for (let attempt = 0; attempt < 3; attempt++) {
    const difference = desired - wallTime(instant)
    if (!difference) return new Date(instant).toISOString()
    instant += difference
  }
  // La hora saltada al iniciar el horario de verano no existe en Chile.
  throw new Error('Esta hora no existe en Chile por el cambio de horario. Elige otra hora.')
}

export function clientPayload(form) {
  const missingLat = form.lat === '' || form.lat == null
  const missingLng = form.lng === '' || form.lng == null
  if (missingLat !== missingLng) throw new Error('Completa ambas coordenadas o deja ambas vacías')
  return { ...form, direccion: form.direccion.trim() || null, lat: missingLat ? null : Number(form.lat), lng: missingLng ? null : Number(form.lng) }
}
