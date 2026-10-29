import React from 'react'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { CroquisViewer } from '../src/CroquisViewer.jsx'
import { App } from '../src/main.jsx'
import { drawCroquis, loadMaps } from '../src/croquis-map.js'

vi.mock('../src/croquis-map.js', async original => ({ ...await original(), loadMaps: vi.fn(), drawCroquis: vi.fn() }))
const visit = { id: '33333333-3333-3333-3333-333333333333', fecha_hora: '2026-10-19T13:00:00Z', estado: 'completada', cliente: { nombre: 'Cliente QA', lat: -33.45, lng: -70.66 }, operador_id: null }
const trap = (changes = {}) => ({ id: '11111111-1111-1111-1111-111111111111', codigo: 'T-01', tipo: 'cebadero', lat: -33.45, lng: -70.66, estado: 'activo', confirmado: true, sugerido_por_ia: false, foto_url: null, ...changes })
const data = (dispositivos = [trap()]) => ({ visita_id: visit.id, version: 2, validado_por_operador: true, dispositivos })
let body, photoStatus, map

beforeEach(() => {
  localStorage.token = 'token-croquis-qa'
  body = data(); photoStatus = 200
  map = { select: vi.fn(), destroy: vi.fn() }
  vi.mocked(loadMaps).mockReset().mockResolvedValue({})
  vi.mocked(drawCroquis).mockReset().mockReturnValue(map)
  vi.stubGlobal('fetch', vi.fn(async (url, options = {}) => {
    const path = new URL(url).pathname
    if (path.includes('/foto')) return photoStatus === 200 ? new Response(new Blob(['png'], { type: 'image/png' }), { headers: { 'Content-Type': 'image/png' } }) : new Response('{}', { status: photoStatus })
    return new Response(JSON.stringify(body))
  }))
  URL.createObjectURL = vi.fn(() => 'blob:foto-qa')
  URL.revokeObjectURL = vi.fn()
})
afterEach(() => { vi.unstubAllGlobals() })

describe('CRW visor de croquis de solo lectura', () => {
  it('CRW01 carga únicamente con GET y no ofrece acciones de modificación', async () => {
    render(<CroquisViewer visit={visit} />)
    expect(await screen.findByRole('button', { name: /T-01/ })).toBeVisible()
    expect(screen.getByText(/Solo lectura/)).toBeVisible()
    expect(fetch.mock.calls.every(([, options]) => options.method === 'GET')).toBe(true)
    expect(screen.queryByRole('button', { name: /crear|mover|retirar|confirmar|guardar/i })).toBeNull()
    expect(fetch.mock.calls[0][1].headers.Authorization).toBe('Bearer token-croquis-qa')
  })
  it('CRW02 conserva retiradas y distingue propuestas IA', async () => {
    body = data([trap({ estado: 'retirado', sugerido_por_ia: true, confirmado: false }), trap({ id: '22222222-2222-2222-2222-222222222222', codigo: 'T-02', sugerido_por_ia: true, confirmado: false })])
    render(<CroquisViewer visit={visit} />)
    expect(await screen.findByRole('button', { name: /T-01/ })).toHaveClass('retired')
    expect(screen.getByRole('button', { name: /T-02/ })).toHaveClass('suggested')
  })
  it('CRW03 croquis inexistente no se crea automáticamente', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response('{}', { status: 404 })))
    render(<CroquisViewer visit={visit} />)
    expect(await screen.findByText(/La visita no tiene un croquis/)).toBeVisible()
    expect(fetch).toHaveBeenCalledOnce()
    expect(fetch.mock.calls[0][1].method).toBe('GET')
  })
  it('CRW04 informa permisos insuficientes sin mostrar trampas', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response('{}', { status: 403 })))
    render(<CroquisViewer visit={visit} />)
    expect(await screen.findByRole('alert')).toHaveTextContent('No tienes permiso')
    expect(screen.queryByText('T-01')).toBeNull()
  })
  it('CRW05 maneja un croquis vacío', async () => {
    body = data([])
    render(<CroquisViewer visit={visit} />)
    expect(await screen.findByText(/aún no tiene trampas/)).toBeVisible()
    expect(screen.queryByLabelText(/Detalle de/)).toBeNull()
  })
  it('CRW06 mantiene el listado y fotos si Google Maps falla', async () => {
    vi.mocked(loadMaps).mockRejectedValue(new Error('sin clave'))
    render(<CroquisViewer visit={visit} />)
    expect(await screen.findByText(/Falta configurar la clave/)).toBeVisible()
    expect(screen.getByRole('button', { name: /T-01/ })).toBeVisible()
    expect(screen.getByText('Sin foto registrada.')).toBeVisible()
  })
  it('CRW07 no inventa ubicaciones ni carga Maps sin coordenadas', async () => {
    body = data([trap({ lat: null, lng: null })])
    render(<CroquisViewer visit={{ ...visit, cliente: { nombre: 'Sin GPS' } }} />)
    expect(await screen.findByText(/No hay coordenadas válidas/)).toBeVisible()
    expect(loadMaps).not.toHaveBeenCalled()
    expect(screen.getByText('Sin coordenadas válidas')).toBeVisible()
  })
  it('CRW08 muestra una foto autenticada como blob y la libera al cerrar', async () => {
    body = data([trap({ foto_url: `/dispositivos-trampa/${trap().id}/foto?v=abc123` })])
    const { unmount } = render(<CroquisViewer visit={visit} />)
    expect(await screen.findByRole('img', { name: /Foto de la trampa T-01/ })).toHaveAttribute('src', 'blob:foto-qa')
    const [url, options] = fetch.mock.calls.find(([url]) => url.includes('/foto'))
    expect(url).not.toContain('token')
    expect(options.headers.Authorization).toBe('Bearer token-croquis-qa')
    expect(options.redirect).toBe('error')
    unmount()
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:foto-qa')
    expect(map.destroy).toHaveBeenCalledOnce()
  })
  it.each([[403, 'No tienes permiso para ver esta foto'], [404, 'La foto ya no está disponible']])('CRW09 foto responde %s', async (status, message) => {
    photoStatus = status; body = data([trap({ foto_url: `/dispositivos-trampa/${trap().id}/foto` })])
    render(<CroquisViewer visit={visit} />)
    expect(await screen.findByRole('alert')).toHaveTextContent(message)
    expect(screen.queryByRole('img')).toBeNull()
  })
  it('CRW10 sincroniza selección en listado y mapa', async () => {
    body = data([trap(), trap({ id: '22222222-2222-2222-2222-222222222222', codigo: 'T-02' })])
    const user = userEvent.setup()
    render(<CroquisViewer visit={visit} />)
    await user.click(await screen.findByRole('button', { name: /T-02/ }))
    expect(screen.getByRole('region', { name: 'Detalle de T-02' })).toBeVisible()
    expect(map.select).toHaveBeenLastCalledWith(body.dispositivos[1].id)
    const onMapSelect = vi.mocked(drawCroquis).mock.calls[0][4]
    const { act } = await import('@testing-library/react')
    act(() => onMapSelect(trap().id))
    expect(screen.getByRole('button', { name: /T-01/ })).toHaveAttribute('aria-pressed', 'true')
  })
  it('CRW11 actualizar vuelve a leer sin escribir', async () => {
    const user = userEvent.setup()
    render(<CroquisViewer visit={visit} />)
    await user.click(await screen.findByRole('button', { name: 'Actualizar croquis' }))
    await screen.findByRole('button', { name: /T-01/ })
    expect(fetch).toHaveBeenCalledTimes(2)
    expect(fetch.mock.calls.every(([, options]) => options.method === 'GET')).toBe(true)
  })
  it('CRW12 aborta cargas antiguas al cambiar de visita', async () => {
    let resolve
    vi.stubGlobal('fetch', vi.fn(() => new Promise(done => { resolve = done })))
    const { rerender } = render(<CroquisViewer visit={visit} />)
    const oldSignal = fetch.mock.calls[0][1].signal
    const oldResolve = resolve
    rerender(<CroquisViewer visit={{ ...visit, id: 'otra-visita' }} />)
    oldResolve(new Response(JSON.stringify(data())))
    expect(oldSignal.aborted).toBe(true)
    expect(screen.queryByText('T-01')).toBeNull()
  })
  it('CRW13 rechaza respuestas de otra visita', async () => {
    body = { ...data(), visita_id: 'otra-visita' }
    render(<CroquisViewer visit={visit} />)
    expect(await screen.findByRole('alert')).toHaveTextContent('croquis inválido')
    expect(screen.queryByText('T-01')).toBeNull()
  })
  it('CRW14 sesión vencida en una foto expira la sesión del panel', async () => {
    photoStatus = 401; body = data([trap({ foto_url: `/dispositivos-trampa/${trap().id}/foto` })])
    render(<CroquisViewer visit={visit} />)
    await waitFor(() => expect(localStorage.token).toBeUndefined())
  })
  it('CRW15 abre croquis desde una visita completada y cierra con Escape', async () => {
    const original = fetch
    vi.stubGlobal('fetch', vi.fn((url, options) => {
      const path = new URL(url).pathname
      const result = { '/panel/visitas': [visit], '/panel/operadores': [], '/panel/stats': {}, '/clientes': [visit.cliente] }[path]
      return result ? Promise.resolve(new Response(JSON.stringify(result))) : original(url, options)
    }))
    const user = userEvent.setup()
    render(<App />)
    await user.click(screen.getByRole('button', { name: 'Ingresar', exact: true }))
    const trigger = await screen.findByRole('button', { name: /Ver croquis de Cliente QA/ })
    await user.click(trigger)
    expect(await screen.findByRole('dialog', { name: 'Croquis de la visita' })).toBeVisible()
    fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' })
    expect(screen.queryByRole('dialog')).toBeNull()
    expect(trigger).toHaveFocus()
  })
})
