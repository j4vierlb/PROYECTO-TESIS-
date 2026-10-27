const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'
export const SESSION_EXPIRED = 'panel:session-expired'

export class ApiError extends Error {
  constructor(message, status = 0) {
    super(message)
    this.status = status
  }
}

const fieldNames = { nombre: 'Nombre', telefono_whatsapp: 'Teléfono', direccion: 'Dirección', lat: 'Latitud', lng: 'Longitud', fecha_hora: 'Fecha y hora', operador_id: 'Operador', estado: 'Estado' }

function errorMessage(detail) {
  if (typeof detail === 'string') return detail
  if (!Array.isArray(detail)) return 'No se pudo completar la solicitud. Intenta nuevamente.'
  return detail.map(item => {
    const field = fieldNames[item.loc?.at(-1)] || 'Datos'
    const messages = {
      missing: 'este campo es obligatorio', uuid_parsing: 'selecciona una opción válida',
      timezone_aware: 'incluye una zona horaria válida', string_too_short: 'el texto es demasiado corto',
      string_too_long: 'el texto es demasiado largo', less_than_equal: 'el valor supera el máximo permitido',
      greater_than_equal: 'el valor es menor al mínimo permitido', float_parsing: 'ingresa un número válido',
      extra_forbidden: 'este campo no está permitido',
    }
    return `${field}: ${messages[item.type] || (item.type === 'value_error' ? item.msg.replace(/^Value error, /, '') : 'revisa el valor ingresado')}`
  }).join('. ')
}

export async function request(path, options = {}) {
  return execute(path, options)
}

// Solo las rutas de fotos de la API pueden recibir el token. No se siguen
// redirecciones ni se acepta una URL externa entregada por un croquis.
export async function requestPhoto(path, options = {}) {
  if (typeof path !== 'string' || !/^\/dispositivos-trampa\/[0-9a-f-]{36}\/foto(?:\?v=[0-9a-z-]{1,64})?$/i.test(path)) {
    throw new ApiError('La dirección de la foto no es válida.')
  }
  return execute(path, { signal: options.signal, method: 'GET', redirect: 'error', cache: 'no-store' }, true)
}

async function execute(path, options, photo = false) {
  const token = ['/auth/login', '/auth/forgot-password', '/auth/reset-password'].includes(path) ? null : localStorage.token
  const controller = new AbortController()
  const abort = () => controller.abort()
  if (options.signal?.aborted) controller.abort()
  options.signal?.addEventListener('abort', abort, { once: true })
  const timeout = setTimeout(abort, 15000)
  try {
    const response = await fetch(`${API}${path}`, {
      ...options, signal: controller.signal,
      headers: { 'Content-Type': 'application/json', ...options.headers, ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    })
    if (!response.ok) {
      const body = await response.json().catch(() => ({}))
      if (response.status === 401 && token && token === localStorage.token) {
        localStorage.removeItem('token')
        window.dispatchEvent(new Event(SESSION_EXPIRED))
      }
      throw new ApiError(response.status >= 500
        ? 'El servidor no pudo completar la solicitud. Intenta nuevamente.'
        : errorMessage(body.detail), response.status)
    }
    if (photo) {
      if (!['image/jpeg', 'image/png'].includes(response.headers.get('content-type')?.split(';')[0])) {
        throw new ApiError('El servidor no entregó una foto válida.')
      }
      const blob = await response.blob()
      if (!blob.size || blob.size > 5 * 1024 * 1024) throw new ApiError('La foto está vacía o supera los 5 MB.')
      return blob
    }
    return response.status === 204 ? null : await response.json()
  } catch (error) {
    if (error instanceof ApiError || options.signal?.aborted) throw error
    throw new ApiError(controller.signal.aborted
      ? 'La solicitud tardó demasiado. Comprueba la conexión e intenta nuevamente.'
      : 'No se pudo conectar con el servidor. Comprueba tu conexión e intenta nuevamente.')
  } finally {
    clearTimeout(timeout)
    options.signal?.removeEventListener('abort', abort)
  }
}
