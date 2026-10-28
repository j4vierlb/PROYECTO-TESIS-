import React from 'react'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { App } from '../src/main.jsx'

const client = { id: '33333333-3333-3333-3333-333333333333', nombre: 'Cliente WhatsApp', telefono_whatsapp: '+56912345678', direccion: null, lat: null, lng: null }
const operator = { id: '44444444-4444-4444-4444-444444444444', nombre: 'Operador de prueba' }
let visits, operators, clients, writes
const existingVisit = (changes = {}) => ({ id: 'visita-test', fecha_hora: '2026-09-29T13:00:00Z', cliente: client, operador_id: null, operador: null, estado: 'agendada', notas: null, origen_agendamiento: 'manual', ...changes })

beforeEach(() => {
  localStorage.token = 'sesion-de-prueba'
  visits = []
  operators = [operator]
  clients = [client]
  writes = []
  vi.stubGlobal('fetch', vi.fn(async (url, options = {}) => {
    const path = new URL(url).pathname
    if (options.method === 'POST' || options.method === 'PATCH') {
      const body = JSON.parse(options.body)
      writes.push({ path, body })
      if (path === '/panel/visitas') {
        visits.push({ ...body, id: 'visita-test', cliente: client, operador: body.operador_id ? operator : null, estado: 'agendada' })
      }
      if (path.startsWith('/panel/visitas/')) {
        visits = visits.map(visit => ({ ...visit, ...body, operador: body.operador_id ? operator : body.operador_id === null ? null : visit.operador, estado: body.fecha_hora ? 'reagendada' : body.estado || visit.estado }))
        return new Response(JSON.stringify(visits[0]), { status: 200 })
      }
      if (path.startsWith('/clientes/')) clients = [{ ...client, ...body }]
      if (path === '/clientes') clients = [...clients, { ...body, id: 'cliente-nuevo' }]
      return new Response(JSON.stringify(body), { status: 201 })
    }
    const body = { '/panel/visitas': visits, '/panel/operadores': operators, '/panel/stats': { clientes: 1, visitas_hoy: visits.length, pendientes: visits.length }, '/clientes': clients }[path]
    return new Response(JSON.stringify(body), { status: 200 })
  }))
})

describe('Regresión del panel: interacción con el formulario y respuestas API', () => {
  it('crea clientes manuales sin exigir coordenadas', async () => {
    const user = userEvent.setup()
    render(<App />)
    await user.click(screen.getByRole('button', { name: /Clientes/ }))
    await user.click(screen.getByRole('button', { name: /Nuevo cliente/ }))
    await user.type(screen.getByLabelText('Nombre'), 'Nuevo sin GPS')
    await user.type(screen.getByLabelText('Teléfono WhatsApp'), '+00000000009')
    await user.type(screen.getByLabelText('Dirección'), 'Dirección QA 1234')
    await user.click(screen.getByRole('button', { name: 'Guardar cliente' }))
    await waitFor(() => expect(writes[0]?.body).toEqual({ nombre: 'Nuevo sin GPS', telefono_whatsapp: '+00000000009', direccion: 'Dirección QA 1234' }))
    expect(await screen.findByText('Nuevo sin GPS')).toBeVisible()
    expect(screen.queryByLabelText('Latitud')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Longitud')).not.toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveTextContent('Ubicación pendiente de confirmar')
  })

  it('el filtro Sin asignar oculta visitas con operador', async () => {
    visits = [existingVisit(), existingVisit({ id: 'otra-visita', cliente: { ...client, nombre: 'Cliente asignado' }, operador_id: operator.id, operador: operator })]
    const user = userEvent.setup()
    render(<App />)
    await screen.findByText('Cliente asignado')
    await user.selectOptions(screen.getByLabelText('Filtrar por operador'), 'unassigned')
    await waitFor(() => expect(screen.queryByText('Cliente asignado')).not.toBeInTheDocument())
    expect(screen.getByText('Cliente WhatsApp')).toBeVisible()
  })

  it('el login no trae credenciales de demostración precargadas', () => {
    localStorage.clear()
    render(<App />)
    expect(screen.getByLabelText('Correo')).toHaveValue('')
    expect(screen.getByLabelText('Contraseña')).toHaveValue('')
  })

  it('comprueba permisos del panel antes de aceptar un login', async () => {
    localStorage.clear()
    const base = globalThis.fetch
    vi.stubGlobal('fetch', vi.fn((url, options) => new URL(url).pathname === '/auth/login' ? Promise.resolve(new Response(JSON.stringify({ access_token: 'token-admin' }), { status: 200 })) : base(url, options)))
    const user = userEvent.setup()
    render(<App />)
    await user.type(screen.getByLabelText('Correo'), 'admin@panel.test')
    await user.type(screen.getByLabelText('Contraseña'), 'ClaveQA123')
    await user.click(screen.getByRole('button', { name: 'Ingresar al panel' }))
    expect(await screen.findByRole('button', { name: /Nueva visita/ })).toBeVisible()
    expect(localStorage.token).toBe('token-admin')
  })

  it('una cuenta sin permiso administrativo permanece en el login', async () => {
    localStorage.clear()
    vi.stubGlobal('fetch', vi.fn(async url => new URL(url).pathname === '/auth/login'
      ? new Response(JSON.stringify({ access_token: 'token-operador' }), { status: 200 })
      : new Response(JSON.stringify({ detail: 'Se requiere un usuario del panel' }), { status: 403 })))
    const user = userEvent.setup()
    render(<App />)
    await user.type(screen.getByLabelText('Correo'), 'operador@panel.test')
    await user.type(screen.getByLabelText('Contraseña'), 'ClaveQA123')
    await user.click(screen.getByRole('button', { name: 'Ingresar al panel' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Se requiere un usuario del panel')
    expect(screen.getByRole('button', { name: 'Ingresar al panel' })).toBeEnabled()
    expect(localStorage.token).toBeUndefined()
  })

  it('el cierre de sesión sigue disponible en la navegación', async () => {
    const user = userEvent.setup()
    render(<App />)
    await user.click(screen.getByRole('button', { name: 'Cerrar sesión' }))
    expect(screen.getByRole('button', { name: 'Ingresar al panel' })).toBeVisible()
    expect(localStorage.token).toBeUndefined()
  })
  it('reprograma una visita y asigna operador con UTC correcto', async () => {
    visits = [existingVisit()]
    const user = userEvent.setup()
    render(<App />)
    await user.click(await screen.findByRole('button', { name: 'Editar visita' }))
    expect(screen.getByLabelText('Fecha y hora (Chile)')).toHaveValue('2026-09-29T10:00')
    await user.selectOptions(screen.getByLabelText('Operador'), operator.id)
    fireEvent.change(screen.getByLabelText('Fecha y hora (Chile)'), { target: { value: '2026-07-15T11:00' } })
    await user.type(screen.getByLabelText('Notas'), 'Avisar al llegar')
    await user.click(screen.getByRole('button', { name: 'Guardar cambios' }))
    await waitFor(() => expect(writes[0]).toEqual({ path: '/panel/visitas/visita-test', body: { operador_id: operator.id, fecha_hora: '2026-07-15T15:00:00.000Z', notas: 'Avisar al llegar' } }))
    expect(await screen.findByText('11:00')).toBeVisible()
    expect(screen.getByText('Reagendada', { selector: 'span' })).toBeVisible()
    expect(screen.getByLabelText('Fecha de la agenda')).toHaveValue('2026-07-15')
  })

  it('permite quitar el operador sin cambiar la fecha', async () => {
    visits = [existingVisit({ operador_id: operator.id, operador: operator })]
    const user = userEvent.setup()
    render(<App />)
    await user.click(await screen.findByRole('button', { name: 'Editar visita' }))
    await user.selectOptions(screen.getByLabelText('Operador'), '')
    await user.click(screen.getByRole('button', { name: 'Guardar cambios' }))
    await waitFor(() => expect(writes[0]?.body).toEqual({ operador_id: null, notas: null }))
    expect(await within(screen.getByRole('region', { name: 'Visitas del día' })).findByText('Sin asignar')).toBeVisible()
  })

  it('Reagendada abre la edición en lugar de cambiar solo el estado', async () => {
    visits = [existingVisit()]
    const user = userEvent.setup()
    render(<App />)
    await user.selectOptions(await screen.findByLabelText('Estado de visita de Cliente WhatsApp'), 'reagendada')
    expect(screen.getByRole('dialog', { name: 'Editar visita' })).toBeVisible()
    expect(writes).toHaveLength(0)
    await user.keyboard('{Escape}')
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('un conflicto al guardar conserva los datos del formulario', async () => {
    visits = [existingVisit()]
    const base = globalThis.fetch
    vi.stubGlobal('fetch', vi.fn((url, options) => options?.method === 'PATCH' ? Promise.resolve(new Response(JSON.stringify({ detail: 'El operador tiene otra visita' }), { status: 409 })) : base(url, options)))
    const user = userEvent.setup()
    render(<App />)
    await user.click(await screen.findByRole('button', { name: 'Editar visita' }))
    await user.type(screen.getByLabelText('Notas'), 'No perder esta nota')
    await user.click(screen.getByRole('button', { name: 'Guardar cambios' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('El operador tiene otra visita')
    expect(screen.getByLabelText('Notas')).toHaveValue('No perder esta nota')
    expect(screen.getByRole('button', { name: 'Guardar cambios' })).toBeEnabled()
  })

  it('muestra el rechazo de un cambio de estado sin fallar la pantalla', async () => {
    visits = [existingVisit()]
    const base = globalThis.fetch
    vi.stubGlobal('fetch', vi.fn((url, options) => options?.method === 'PATCH' ? Promise.resolve(new Response(JSON.stringify({ detail: 'Horario ocupado' }), { status: 409 })) : base(url, options)))
    const user = userEvent.setup()
    render(<App />)
    await user.selectOptions(await screen.findByLabelText('Estado de visita de Cliente WhatsApp'), 'en_curso')
    expect(await screen.findByRole('alert')).toHaveTextContent('Horario ocupado')
    expect(screen.getByLabelText('Estado de visita de Cliente WhatsApp')).toHaveValue('agendada')
  })

  it('una sesión vencida vuelve al login con una explicación', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: 'Token expirado' }), { status: 401 })))
    render(<App />)
    expect(await screen.findByRole('button', { name: 'Ingresar al panel' })).toBeVisible()
    expect(screen.getByRole('status')).toHaveTextContent('Tu sesión venció')
    expect(localStorage.token).toBeUndefined()
  })

  it('Clientes informa errores de carga y permite reintentar', async () => {
    const base = globalThis.fetch
    let fail = true
    vi.stubGlobal('fetch', vi.fn((url, options) => new URL(url).pathname === '/clientes' && fail ? Promise.reject(new TypeError('Failed to fetch')) : base(url, options)))
    const user = userEvent.setup()
    render(<App />)
    await user.click(screen.getByRole('button', { name: /Clientes/ }))
    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo conectar')
    fail = false
    await user.click(screen.getByRole('button', { name: 'Reintentar' }))
    expect(await screen.findByText('Cliente WhatsApp')).toBeVisible()
  })

  it('no cambia fecha ni operador de una visita finalizada al editar notas', async () => {
    visits = [existingVisit({ estado: 'completada' })]
    const user = userEvent.setup()
    render(<App />)
    await user.click(await screen.findByRole('button', { name: 'Editar visita' }))
    expect(screen.getByLabelText('Fecha y hora (Chile)')).toBeDisabled()
    expect(screen.getByLabelText('Operador')).toBeDisabled()
    await user.type(screen.getByLabelText('Notas'), 'Informe revisado')
    await user.click(screen.getByRole('button', { name: 'Guardar cambios' }))
    await waitFor(() => expect(writes[0]?.body).toEqual({ notas: 'Informe revisado' }))
  })

  it('confirma el borrado y muestra el 409 si el cliente tiene visitas', async () => {
    const base = globalThis.fetch
    vi.stubGlobal('fetch', vi.fn((url, options) => options?.method === 'DELETE' ? Promise.resolve(new Response(JSON.stringify({ detail: 'No se puede eliminar un cliente con visitas asociadas' }), { status: 409 })) : base(url, options)))
    const user = userEvent.setup()
    render(<App />)
    await user.click(screen.getByRole('button', { name: /Clientes/ }))
    await user.click(await screen.findByRole('button', { name: 'Eliminar' }))
    expect(screen.getByRole('dialog', { name: 'Eliminar cliente' })).toBeVisible()
    expect(globalThis.fetch.mock.calls.some(([, options]) => options?.method === 'DELETE')).toBe(false)
    await user.click(screen.getByRole('button', { name: 'Confirmar eliminación' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('visitas asociadas')
  })

  it('un doble envío mientras guarda crea una sola visita', async () => {
    const base = globalThis.fetch
    let resolve
    vi.stubGlobal('fetch', vi.fn((url, options) => options?.method === 'POST' ? new Promise(done => { resolve = done }) : base(url, options)))
    const user = userEvent.setup()
    render(<App />)
    await waitFor(() => expect(screen.getByRole('button', { name: /Nueva visita/ })).toBeEnabled())
    await user.click(screen.getByRole('button', { name: /Nueva visita/ }))
    const dialog = screen.getByRole('dialog')
    fireEvent.submit(dialog); fireEvent.submit(dialog)
    expect(globalThis.fetch.mock.calls.filter(([, options]) => options?.method === 'POST')).toHaveLength(1)
    resolve(new Response(JSON.stringify(existingVisit()), { status: 201 }))
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
  })

  it('una respuesta antigua no reemplaza el nuevo día seleccionado', async () => {
    const base = globalThis.fetch
    let resolveFirst, reads = 0
    vi.stubGlobal('fetch', vi.fn((url, options) => {
      if (new URL(url).pathname !== '/panel/visitas') return base(url, options)
      if (reads++ === 0) return new Promise(resolve => { resolveFirst = resolve })
      return Promise.resolve(new Response(JSON.stringify([existingVisit({ cliente: { ...client, nombre: 'Día nuevo' } })]), { status: 200 }))
    }))
    render(<App />)
    await waitFor(() => expect(resolveFirst).toBeDefined())
    fireEvent.change(screen.getByLabelText('Fecha de la agenda'), { target: { value: '2026-11-03' } })
    expect(await screen.findByText('Día nuevo')).toBeVisible()
    resolveFirst(new Response(JSON.stringify([existingVisit({ cliente: { ...client, nombre: 'Día anterior' } })]), { status: 200 }))
    await waitFor(() => expect(screen.queryByText('Día anterior')).not.toBeInTheDocument())
    expect(screen.getByText('Día nuevo')).toBeVisible()
  })

  it('no permite agendar sin clientes registrados', async () => {
    clients = []
    const user = userEvent.setup()
    render(<App />)
    await waitFor(() => expect(screen.getByRole('button', { name: /Nueva visita/ })).toBeEnabled())
    await user.click(screen.getByRole('button', { name: /Nueva visita/ }))
    expect(screen.getByRole('button', { name: 'Agendar visita' })).toBeDisabled()
  })
  it('Clientes se abre y permite guardar clientes sin ubicación ni dirección', async () => {
    const user = userEvent.setup()
    render(<App />)
    await user.click(screen.getByRole('button', { name: /Clientes/ }))
    expect(await screen.findByText('Sin coordenadas')).toBeVisible()
    await user.click(screen.getByRole('button', { name: 'Editar' }))
    expect(screen.queryByLabelText('Latitud')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Longitud')).not.toBeInTheDocument()
    await user.clear(screen.getByLabelText('Nombre'))
    await user.type(screen.getByLabelText('Nombre'), 'Nombre corregido')
    await user.click(screen.getByRole('button', { name: 'Guardar cliente' }))
    await waitFor(() => expect(writes[0]?.body).toEqual({ nombre: 'Nombre corregido', telefono_whatsapp: client.telefono_whatsapp, direccion: null }))
    expect(await screen.findByText('Nombre corregido')).toBeVisible()
    expect(screen.getByText('Sin coordenadas')).toBeVisible()
  })

  it('una ubicación completa sigue mostrando sus coordenadas', async () => {
    clients = [{ ...client, lat: -33.4869, lng: -70.5989 }]
    const user = userEvent.setup()
    render(<App />)
    await user.click(screen.getByRole('button', { name: /Clientes/ }))
    expect(await screen.findByText('-33.4869, -70.5989')).toBeVisible()
  })

  it('editar una dirección no reenvía el punto viejo al backend', async () => {
    clients = [{ ...client, direccion: 'Macul 1234, Macul', lat: -33.4, lng: -70.6 }]
    const user = userEvent.setup()
    render(<App />)
    await user.click(screen.getByRole('button', { name: /Clientes/ }))
    await user.click(await screen.findByRole('button', { name: 'Editar' }))
    expect(screen.getByText(/Buscaremos la ubicación automáticamente/)).toBeVisible()
    await user.clear(screen.getByLabelText('Dirección'))
    await user.type(screen.getByLabelText('Dirección'), 'Providencia 1208, Providencia')
    await user.click(screen.getByRole('button', { name: 'Guardar cliente' }))
    await waitFor(() => expect(writes[0]?.body).toEqual({ nombre: client.nombre, telefono_whatsapp: client.telefono_whatsapp, direccion: 'Providencia 1208, Providencia' }))
    expect(screen.getByRole('status')).toHaveTextContent('Ubicación pendiente de confirmar')
  })

  it('muestra la ubicación devuelta por el servidor sin pedir números al usuario', async () => {
    const base = globalThis.fetch
    vi.stubGlobal('fetch', vi.fn(async (url, options) => {
      const response = await base(url, options)
      if (new URL(url).pathname === '/clientes' && options?.method === 'POST') {
        const saved = { ...JSON.parse(options.body), id: 'cliente-geocodificado', lat: -33.4290994, lng: -70.621161 }
        clients = [saved]
        return new Response(JSON.stringify(saved), { status: 201 })
      }
      return response
    }))
    const user = userEvent.setup()
    render(<App />)
    await user.click(screen.getByRole('button', { name: /Clientes/ }))
    await user.click(screen.getByRole('button', { name: /Nuevo cliente/ }))
    await user.type(screen.getByLabelText('Nombre'), 'Cliente ubicado')
    await user.type(screen.getByLabelText('Teléfono WhatsApp'), '+00000000009')
    await user.type(screen.getByLabelText('Dirección'), 'Providencia 1208, Providencia')
    await user.click(screen.getByRole('button', { name: 'Guardar cliente' }))
    expect(await screen.findByText('-33.4291, -70.6212')).toBeVisible()
    expect(screen.getByRole('status')).toHaveTextContent('Ubicación disponible para el croquis')
  })

  it('si falla el guardado conserva la dirección y permite reintentar', async () => {
    const base = globalThis.fetch
    vi.stubGlobal('fetch', vi.fn((url, options) => options?.method === 'POST' && new URL(url).pathname === '/clientes'
      ? Promise.resolve(new Response(JSON.stringify({ detail: 'Servicio temporalmente no disponible' }), { status: 503 }))
      : base(url, options)))
    const user = userEvent.setup()
    render(<App />)
    await user.click(screen.getByRole('button', { name: /Clientes/ }))
    await user.click(screen.getByRole('button', { name: /Nuevo cliente/ }))
    await user.type(screen.getByLabelText('Nombre'), 'Cliente QA')
    await user.type(screen.getByLabelText('Teléfono WhatsApp'), '+00000000009')
    await user.type(screen.getByLabelText('Dirección'), 'Providencia 1208, Providencia')
    await user.click(screen.getByRole('button', { name: 'Guardar cliente' }))
    expect(await screen.findByRole('alert')).toBeVisible()
    expect(screen.getByLabelText('Dirección')).toHaveValue('Providencia 1208, Providencia')
    expect(screen.getByRole('button', { name: 'Guardar cliente' })).toBeEnabled()
  })

  it('agenda una visita Sin asignar con hora chilena, y la vuelve a mostrar', async () => {
    const user = userEvent.setup()
    render(<App />)
    await waitFor(() => expect(screen.getByText('Clientes registrados').parentElement).toHaveTextContent('1'))
    await user.click(screen.getByRole('button', { name: /Nueva visita/ }))
    await user.selectOptions(screen.getByLabelText('Operador'), '')
    const dateInput = screen.getByLabelText('Fecha y hora (Chile)')
    // fireEvent para datetime-local: userEvent no escribe estos controles nativos.
    const { fireEvent } = await import('@testing-library/react')
    fireEvent.change(dateInput, { target: { value: '2026-09-29T10:00' } })
    await user.click(screen.getByRole('button', { name: 'Agendar visita' }))
    await waitFor(() => expect(writes[0]?.body).toEqual({ cliente_id: client.id, operador_id: null, fecha_hora: '2026-09-29T13:00:00.000Z' }))
    expect(await within(screen.getByRole('region', { name: 'Visitas del día' })).findByText('Sin asignar')).toBeVisible()
    expect(screen.getByText('10:00')).toBeVisible()
    expect(screen.queryByText('13:00')).not.toBeInTheDocument()
  })

  it('también agenda cuando la API no entrega ningún operador', async () => {
    operators = []
    const user = userEvent.setup()
    render(<App />)
    await waitFor(() => expect(screen.getByText('Clientes registrados').parentElement).toHaveTextContent('1'))
    await user.click(screen.getByRole('button', { name: /Nueva visita/ }))
    await user.click(screen.getByRole('button', { name: 'Agendar visita' }))
    await waitFor(() => expect(writes[0]?.body.operador_id).toBeNull())
    expect(await within(screen.getByRole('region', { name: 'Visitas del día' })).findByText('Sin asignar')).toBeVisible()
  })

  it('agrupa UTC en hora chilena y ordena los horarios', async () => {
    visits = [
      { id: 'v1', fecha_hora: '2026-09-30T02:30:00Z', cliente: client, operador: null, estado: 'agendada' },
      { id: 'v2', fecha_hora: '2026-09-29T13:00:00Z', cliente: client, operador: operator, estado: 'agendada' },
    ]
    const { container } = render(<App />)
    await screen.findByText('23:30')
    expect([...container.querySelectorAll('.time')].map(el => el.firstChild.textContent)).toEqual(['10:00', '23:30'])
    expect(within(screen.getByRole('region', { name: 'Visitas del día' })).getByText('Sin asignar')).toBeVisible()
  })

  it('la nueva visita usa la fecha seleccionada en la agenda', async () => {
    const user = userEvent.setup()
    const { container } = render(<App />)
    await waitFor(() => expect(screen.getByText('Clientes registrados').parentElement).toHaveTextContent('1'))
    const { fireEvent } = await import('@testing-library/react')
    fireEvent.change(container.querySelector('input[type="date"]'), { target: { value: '2026-07-15' } })
    await user.click(screen.getByRole('button', { name: /Nueva visita/ }))
    expect(screen.getByLabelText('Fecha y hora (Chile)')).toHaveValue('2026-07-15T10:00')
    await user.click(screen.getByRole('button', { name: 'Agendar visita' }))
    await waitFor(() => expect(writes[0]?.body.fecha_hora).toBe('2026-07-15T14:00:00.000Z'))
  })
})

describe('Bandeja de WhatsApp y reagendamiento', () => {
  const conversationId = '88888888-8888-8888-8888-888888888888'
  const message = (id, emisor, contenido, extra = {}) => ({ id, emisor, contenido, created_at: '2026-10-22T13:00:00Z', estado_entrega: null, error_entrega: null, ...extra })
  let detail

  beforeEach(() => {
    detail = {
      id: conversationId, cliente: client, atendida_por_humano: false, ventana_abierta: true,
      mensajes: [
        message('m1', 'cliente', 'Hola, ¿atienden hoy?'),
        message('m2', 'agente_ia', 'Hola 😊 Sí, ¿qué necesitas?', { estado_entrega: 'read' }),
        message('m3', 'sistema', 'Recordatorio de tu visita', { estado_entrega: 'undelivered', error_entrega: '63016: Fuera de la ventana' }),
      ],
    }
    const summary = () => ({ ...detail, mensajes: undefined, ultimo_mensaje: detail.mensajes.at(-1).contenido, ultimo_emisor: detail.mensajes.at(-1).emisor })
    vi.stubGlobal('fetch', vi.fn(async (url, options = {}) => {
      const path = new URL(url).pathname
      const body = options.body ? JSON.parse(options.body) : null
      if (body) writes.push({ path, method: options.method, body })
      if (path === `/panel/conversaciones/${conversationId}/mensajes`) {
        detail = { ...detail, atendida_por_humano: true, mensajes: [...detail.mensajes, message('m4', 'operador', body.contenido, { estado_entrega: 'queued' })] }
        return new Response(JSON.stringify(detail.mensajes.at(-1)), { status: 201 })
      }
      if (path === `/panel/conversaciones/${conversationId}` && options.method === 'PATCH') detail = { ...detail, ...body }
      if (path.startsWith('/panel/visitas/') && options.method === 'PATCH') return new Response(JSON.stringify({}), { status: 200 })
      const responses = { '/panel/conversaciones': [summary()], [`/panel/conversaciones/${conversationId}`]: detail, '/panel/visitas': visits, '/panel/operadores': operators, '/panel/stats': { clientes: 1, visitas_hoy: 0, pendientes: 0 }, '/clientes': clients }
      return new Response(JSON.stringify(responses[path]), { status: 200 })
    }))
  })

  it('muestra la conversación con quién escribió y el estado de entrega', async () => {
    const user = userEvent.setup()
    render(<App />)
    await user.click(screen.getByRole('button', { name: /WhatsApp/ }))
    expect(await screen.findByText('Hola, ¿atienden hoy?')).toBeVisible()
    expect(screen.getByText(/✓✓ Leído/)).toBeVisible()
    expect(screen.getByText(/No entregado · 63016: Fuera de la ventana/)).toBeVisible()
    expect(screen.getByText(/^Aviso automático ·/)).toBeVisible()
  })

  it('el operador responde y la conversación pasa a estar atendida por un humano', async () => {
    const user = userEvent.setup()
    render(<App />)
    await user.click(screen.getByRole('button', { name: /WhatsApp/ }))
    await user.type(await screen.findByLabelText('Mensaje para el cliente'), 'Hola, soy Juan')
    await user.click(screen.getByRole('button', { name: 'Enviar' }))
    await waitFor(() => expect(writes.at(-1)).toEqual({ path: `/panel/conversaciones/${conversationId}/mensajes`, method: 'POST', body: { contenido: 'Hola, soy Juan' } }))
    expect(await screen.findByText('Hola, soy Juan')).toBeVisible()
    expect(screen.getByLabelText('Mensaje para el cliente')).toHaveValue('')
    expect(await screen.findByRole('button', { name: 'Devolver a la IA' })).toBeVisible()
    await user.click(screen.getByRole('button', { name: 'Devolver a la IA' }))
    await waitFor(() => expect(writes.at(-1).body).toEqual({ atendida_por_humano: false }))
    expect(await screen.findByRole('button', { name: 'Tomar conversación' })).toBeVisible()
  })

  it('fuera de la ventana de 24 h no deja escribir', async () => {
    detail.ventana_abierta = false
    const user = userEvent.setup()
    render(<App />)
    await user.click(screen.getByRole('button', { name: /WhatsApp/ }))
    expect(await screen.findByText(/no escribe hace más de 24 h/)).toBeVisible()
    expect(screen.queryByLabelText('Mensaje para el cliente')).not.toBeInTheDocument()
  })

  it('al editar una visita avisa que el cambio de fecha se le informa al cliente', async () => {
    visits = [existingVisit()]
    const user = userEvent.setup()
    render(<App />)
    await user.click(await screen.findByRole('button', { name: 'Editar visita' }))
    expect(screen.getByText(/se le avisará al cliente por WhatsApp/)).toBeVisible()
  })
})
