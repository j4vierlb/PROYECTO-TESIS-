import { afterEach, describe, expect, it, vi } from 'vitest'
import { coordinates, drawCroquis, loadMaps, trapAppearance } from '../src/croquis-map.js'
import { importLibrary, setOptions } from '@googlemaps/js-api-loader'
vi.mock('@googlemaps/js-api-loader', () => ({ importLibrary: vi.fn().mockResolvedValue({}), setOptions: vi.fn() }))
afterEach(() => { vi.unstubAllEnvs(); vi.unstubAllGlobals() })

describe('CRM modelo y adaptador de mapa', () => {
  it.each([{ lat: null, lng: null }, { lat: 91, lng: 0 }, { lat: 0, lng: -181 }, { lat: NaN, lng: 0 }, { lat: '0', lng: 0 }])('CRM01 descarta coordenadas inválidas %j', value => expect(coordinates(value)).toBeNull())
  it('CRM02 acepta coordenadas cero', () => expect(coordinates({ lat: 0, lng: 0 })).toEqual({ lat: 0, lng: 0 }))
  it.each([
    [{ estado: 'retirado', sugerido_por_ia: true }, 'retired'],
    [{ sugerido_por_ia: true, confirmado: false }, 'suggested'],
    [{ estado: 'revisar', confirmado: true }, 'review'],
    [{ confirmado: true }, 'confirmed'], [{}, 'unconfirmed'],
  ])('CRM03 apariencia %s', (device, tone) => expect(trapAppearance(device).tone).toBe(tone))
  it('CRM04 falta de clave no solicita el SDK', async () => {
    vi.stubEnv('VITE_GOOGLE_MAPS_API_KEY', '')
    await expect(loadMaps()).rejects.toThrow('Falta configurar')
    expect(setOptions).not.toHaveBeenCalled()
    expect(importLibrary).not.toHaveBeenCalled()
  })
  it('CRM05 dibuja puntos inmutables, selecciona y elimina listeners al cerrar', () => {
    const remove = vi.fn(), clear = vi.fn(), pan = vi.fn(), fit = vi.fn(), override = vi.fn()
    let click, style
    const device = { id: 'a', codigo: 'T-01', lat: -33.45, lng: -70.66, estado: 'retirado' }
    const feature = { getId: () => 'a', getProperty: key => ({ codigo: 'T-01', ...trapAppearance(device) })[key] }
    const data = { addGeoJson: vi.fn(() => [feature]), setStyle: fn => { style = fn }, addListener: (event, fn) => { click = fn; return { remove } }, revertStyle: vi.fn(), overrideStyle: override, forEach: fn => fn(feature), remove: vi.fn() }
    const options = []
    const maps = {
      Map: class { constructor(el, opts) { options.push(opts); this.data = data; this.panTo = pan; this.fitBounds = fit } },
      LatLngBounds: class { extend() {} }, SymbolPath: { CIRCLE: 'circle' }, event: { clearInstanceListeners: clear },
    }
    const select = vi.fn(), element = document.createElement('div')
    const view = drawCroquis(maps, element, [device, { ...device, id: 'b', lat: -33.46 }], null, select)
    expect(options[0].mapTypeId).toBe('hybrid')
    expect(data.addGeoJson.mock.calls[0][0].features[0].geometry.coordinates).toEqual([-70.66, -33.45])
    expect(style(feature)).toMatchObject({ draggable: false, editable: false, icon: { fillOpacity: 0.45, fillColor: '#6b7280' } })
    expect(fit).toHaveBeenCalledOnce()
    click({ feature }); expect(select).toHaveBeenCalledWith('a')
    view.select('a'); expect(pan).toHaveBeenCalledWith({ lat: -33.45, lng: -70.66 }); expect(override).toHaveBeenCalledOnce()
    view.destroy(); expect(remove).toHaveBeenCalledOnce(); expect(clear).toHaveBeenCalledOnce(); expect(data.remove).toHaveBeenCalledWith(feature)
  })
  it('CRM06 no crea mapas sin posición válida', () => {
    expect(() => drawCroquis({}, document.createElement('div'), [], null, vi.fn())).toThrow('No hay coordenadas')
  })
})
