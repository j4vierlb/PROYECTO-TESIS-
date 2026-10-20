import { importLibrary, setOptions } from '@googlemaps/js-api-loader'

export function coordinates(item) {
  if (typeof item?.lat !== 'number' || typeof item?.lng !== 'number' ||
      !Number.isFinite(item.lat) || !Number.isFinite(item.lng) ||
      Math.abs(item.lat) > 90 || Math.abs(item.lng) > 180) return null
  return { lat: item.lat, lng: item.lng }
}

export function trapAppearance(device) {
  if (device.estado === 'retirado') return { tone: 'retired', color: '#6b7280', opacity: 0.45, label: 'Retirada' }
  if (device.sugerido_por_ia && !device.confirmado) return { tone: 'suggested', color: '#ca8a04', opacity: 1, label: 'Sugerida por IA · sin confirmar' }
  if (device.estado === 'revisar') return { tone: 'review', color: '#c2410c', opacity: 1, label: 'Requiere revisión' }
  if (device.confirmado) return { tone: 'confirmed', color: '#15803d', opacity: 1, label: 'Confirmada' }
  return { tone: 'unconfirmed', color: '#2563eb', opacity: 1, label: 'Sin confirmar' }
}

let loaderReady = false
export async function loadMaps() {
  const key = import.meta.env.VITE_GOOGLE_MAPS_API_KEY
  if (!key) throw new Error('Falta configurar la clave web de Google Maps. Puedes consultar las trampas y sus fotos en el listado.')
  if (!loaderReady) { setOptions({ key, v: 'quarterly', language: 'es', region: 'CL' }); loaderReady = true }
  await importLibrary('maps')
  return window.google.maps
}

// La capa Data dibuja puntos no editables, sin necesitar un Map ID adicional.
export function drawCroquis(maps, element, devices, client, onSelect) {
  const located = devices.filter(coordinates)
  const center = coordinates(located[0]) || coordinates(client)
  if (!center) throw new Error('No hay coordenadas válidas para mostrar este croquis en el mapa.')
  const map = new maps.Map(element, {
    center, zoom: 19, mapTypeId: 'hybrid', streetViewControl: false,
    fullscreenControl: false, mapTypeControl: true, gestureHandling: 'cooperative',
  })
  const features = map.data.addGeoJson({ type: 'FeatureCollection', features: located.map(device => ({
    type: 'Feature', id: device.id, properties: { ...trapAppearance(device), codigo: device.codigo },
    geometry: { type: 'Point', coordinates: [device.lng, device.lat] },
  })) })
  map.data.setStyle(feature => ({
    title: `${feature.getProperty('codigo')} · ${feature.getProperty('label')}`,
    clickable: true, draggable: false, editable: false,
    icon: { path: maps.SymbolPath.CIRCLE, scale: 9, fillColor: feature.getProperty('color'),
      fillOpacity: feature.getProperty('opacity'), strokeColor: '#ffffff', strokeWeight: 2,
      strokeOpacity: feature.getProperty('opacity') },
  }))
  const click = map.data.addListener('click', event => onSelect(String(event.feature.getId())))
  const bounds = new maps.LatLngBounds()
  located.forEach(device => bounds.extend(coordinates(device)))
  if (located.length > 1) map.fitBounds(bounds, 48)
  return {
    select(id) {
      const device = located.find(item => item.id === id)
      map.data.revertStyle()
      const feature = features.find(item => String(item.getId()) === id)
      if (feature) map.data.overrideStyle(feature, { zIndex: 10, icon: {
        path: maps.SymbolPath.CIRCLE, scale: 12, fillColor: trapAppearance(device).color,
        fillOpacity: trapAppearance(device).opacity, strokeColor: '#111827', strokeWeight: 3,
      } })
      if (device) map.panTo(coordinates(device))
    },
    destroy() { click.remove(); map.data.forEach(feature => map.data.remove(feature)); maps.event.clearInstanceListeners(map); element.replaceChildren() },
  }
}
