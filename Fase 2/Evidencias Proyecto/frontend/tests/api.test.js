import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { request, requestPhoto, SESSION_EXPIRED } from '../src/api.js'

beforeEach(() => { localStorage.token = 'token-prueba' })
afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals() })

describe('HTTP del panel', () => {
  it('envía el token y acepta respuestas sin contenido', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(null, { status: 204 }))
    vi.stubGlobal('fetch', fetcher)
    expect(await request('/clientes/id', { method: 'DELETE' })).toBeNull()
    expect(fetcher.mock.calls[0][1].headers.Authorization).toBe('Bearer token-prueba')
  })
  it('traduce los errores de validación sin mostrar objetos', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: [{ loc: ['body', 'operador_id'], type: 'uuid_parsing', msg: 'Input should be a valid UUID' }] }), { status: 422 })))
    await expect(request('/panel/visitas')).rejects.toThrow('Operador: selecciona una opción válida')
  })
  it('conserva el mensaje de un conflicto y la sesión', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: 'El operador tiene otra visita' }), { status: 409 })))
    await expect(request('/panel/visitas')).rejects.toThrow('El operador tiene otra visita')
    expect(localStorage.token).toBe('token-prueba')
  })
  it('cierra una sesión vencida y avisa a la aplicación', async () => {
    const expired = vi.fn()
    window.addEventListener(SESSION_EXPIRED, expired, { once: true })
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('{}', { status: 401 })))
    await expect(request('/clientes')).rejects.toMatchObject({ status: 401 })
    expect(localStorage.token).toBeUndefined()
    expect(expired).toHaveBeenCalledOnce()
  })
  it('un login rechazado no expira otra sesión ni envía su token', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: 'Credenciales inválidas' }), { status: 401 }))
    vi.stubGlobal('fetch', fetcher)
    await expect(request('/auth/login', { method: 'POST' })).rejects.toThrow('Credenciales inválidas')
    expect(localStorage.token).toBe('token-prueba')
    expect(fetcher.mock.calls[0][1].headers.Authorization).toBeUndefined()
  })
  it('un 401 antiguo no cierra una sesión nueva', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => { localStorage.token = 'token-nuevo'; return new Response('{}', { status: 401 }) }))
    await expect(request('/clientes')).rejects.toMatchObject({ status: 401 })
    expect(localStorage.token).toBe('token-nuevo')
  })
  it('da un mensaje útil si no hay conexión', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
    await expect(request('/clientes')).rejects.toThrow('No se pudo conectar con el servidor')
  })
  it('no muestra detalles internos del servidor', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: 'password=secreto' }), { status: 500 })))
    await expect(request('/clientes')).rejects.toThrow('El servidor no pudo completar la solicitud')
  })
  it('cancela una petición que tarda más de quince segundos', async () => {
    vi.useFakeTimers()
    vi.stubGlobal('fetch', vi.fn((url, { signal }) => new Promise((resolve, reject) => signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError'))))))
    const assertion = expect(request('/clientes')).rejects.toThrow('tardó demasiado')
    await vi.advanceTimersByTimeAsync(15000)
    await assertion
  })
})

describe('CRP descarga privada de fotos', () => {
  const path = '/dispositivos-trampa/11111111-1111-1111-1111-111111111111/foto?v=abc123'
  it.each(['https://evil.test/foto', '//evil.test/foto', '/clientes', `${path}&token=abc`, '/dispositivos-trampa/../foto'])('CRP01 rechaza dirección no permitida %s', async value => {
    const fetcher = vi.fn(); vi.stubGlobal('fetch', fetcher)
    await expect(requestPhoto(value)).rejects.toThrow('dirección de la foto no es válida')
    expect(fetcher).not.toHaveBeenCalled()
  })
  it('CRP02 no permite SVG u otro contenido ejecutable', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response('<svg/>', { headers: { 'Content-Type': 'image/svg+xml' } })))
    await expect(requestPhoto(path)).rejects.toThrow('foto válida')
  })
  it.each([0, 5 * 1024 * 1024 + 1])('CRP03 rechaza foto con tamaño %s', async size => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(new Uint8Array(size), { headers: { 'Content-Type': 'image/png' } })))
    await expect(requestPhoto(path)).rejects.toThrow('vacía o supera')
  })
  it('CRP04 devuelve PNG sin persistencia ni redirecciones', async () => {
    const fetcher = vi.fn(async () => new Response('png', { headers: { 'Content-Type': 'image/png' } })); vi.stubGlobal('fetch', fetcher)
    expect((await requestPhoto(path, { method: 'POST' })).type).toBe('image/png')
    expect(fetcher.mock.calls[0][1]).toMatchObject({ method: 'GET', redirect: 'error', cache: 'no-store' })
    expect(fetcher.mock.calls[0][0]).not.toContain('token-prueba')
  })
})
