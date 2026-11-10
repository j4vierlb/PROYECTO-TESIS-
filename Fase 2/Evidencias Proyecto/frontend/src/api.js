// Dirección del backend. Viene de VITE_API_URL y se fija al COMPILAR el panel
// (por eso, si cambia, hay que reconstruir). Si no existe, usa localhost:8000.
const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'
// Nombre de un evento propio: cuando el servidor responde 401 (sesión vencida)
// se dispara para que la pantalla vuelva al login.
export const SESSION_EXPIRED = 'panel:session-expired'

// Error propio que guarda el código HTTP (status), para que la pantalla pueda
// reaccionar distinto ante un 403, un 404, etc.
export class ApiError extends Error {
  constructor(message, status = 0) {
    super(message)
    this.status = status
  }
}

// Traduce los nombres de campos del backend a palabras para el usuario
// (ejemplo: 'telefono_whatsapp' pasa a 'Teléfono').
const fieldNames = { nombre: 'Nombre', telefono_whatsapp: 'Teléfono', direccion: 'Dirección', lat: 'Latitud', lng: 'Longitud', fecha_hora: 'Fecha y hora', operador_id: 'Operador', estado: 'Estado' }

// FastAPI devuelve los errores de validación como una lista técnica. Aquí se
// convierten en frases en español que el usuario puede entender.
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

// Función principal para llamar a la API desde el panel. Agrega el token de
// sesión solo cuando corresponde (ver execute más abajo).
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

// Hace la llamada de verdad con fetch. Pasos: 1) agrega el token de sesión,
// 2) pone un límite de 15 segundos, 3) si el servidor responde 401 cierra la
// sesión, 4) traduce los errores a mensajes claros.
async function execute(path, options, photo = false) {
  // Las rutas de login y de recuperación no llevan token (todavía no hay sesión).
  // Todas las demás sí.
  const token = ['/auth/login', '/auth/forgot-password', '/auth/reset-password'].includes(path) ? null : localStorage.token
  // AbortController permite cancelar la llamada, ya sea por el límite de tiempo
  // o porque el usuario cambió de pantalla.
  const controller = new AbortController()
  const abort = () => controller.abort()
  if (options.signal?.aborted) controller.abort()
  options.signal?.addEventListener('abort', abort, { once: true })
  // A los 15 segundos sin respuesta se cancela la solicitud.
  const timeout = setTimeout(abort, 15000)
  try {
    const response = await fetch(`${API}${path}`, {
      ...options, signal: controller.signal,
      headers: { 'Content-Type': 'application/json', ...options.headers, ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    })
    if (!response.ok) {
      const body = await response.json().catch(() => ({}))
      // 401 = la sesión venció o no es válida: se borra el token y se avisa a la
      // pantalla con un evento, para que vuelva al login.
      if (response.status === 401 && token && token === localStorage.token) {
        localStorage.removeItem('token')
        window.dispatchEvent(new Event(SESSION_EXPIRED))
      }
      // Los errores 5xx son del servidor: se muestra un mensaje genérico en vez de
      // mostrar detalles técnicos al usuario.
      throw new ApiError(response.status >= 500
        ? 'El servidor no pudo completar la solicitud. Intenta nuevamente.'
        : errorMessage(body.detail), response.status)
    }
    // Si es una foto, antes de mostrarla se comprueba que sea de verdad un JPEG o
    // PNG y que pese menos de 5 MB.
    if (photo) {
      if (!['image/jpeg', 'image/png'].includes(response.headers.get('content-type')?.split(';')[0])) {
        throw new ApiError('El servidor no entregó una foto válida.')
      }
      const blob = await response.blob()
      if (!blob.size || blob.size > 5 * 1024 * 1024) throw new ApiError('La foto está vacía o supera los 5 MB.')
      return blob
    }
    // 204 significa 'sin contenido' (por ejemplo, al borrar algo). Si no, se lee el JSON.
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
