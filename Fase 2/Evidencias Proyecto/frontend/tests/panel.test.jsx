import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { App } from '../src/main.jsx'

const client = { id: '33333333-3333-3333-3333-333333333333', nombre: 'Cliente WhatsApp', telefono_whatsapp: '+56912345678', direccion: null, lat: null, lng: null }
const operator = { id: '44444444-4444-4444-4444-444444444444', nombre: 'Operador de prueba' }
let visits, operators, clients, writes

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
      if (path.startsWith('/clientes/')) clients = [{ ...client, ...body }]
      return new Response(JSON.stringify(body), { status: 201 })
    }
    const body = { '/panel/visitas': visits, '/panel/operadores': operators, '/panel/stats': { clientes: 1, visitas_hoy: visits.length, pendientes: visits.length }, '/clientes': clients }[path]
    return new Response(JSON.stringify(body), { status: 200 })
  }))
})

describe('Regresión del panel: interacción con el formulario y respuestas API', () => {
  it('Clientes se abre y permite guardar clientes sin ubicación ni dirección', async () => {
    const user = userEvent.setup()
    render(<App />)
    await user.click(screen.getByRole('button', { name: /Clientes/ }))
    expect(await screen.findByText('Sin coordenadas')).toBeVisible()
    await user.click(screen.getByRole('button', { name: 'Editar' }))
    expect(screen.getByLabelText('Latitud')).toHaveValue(null)
    expect(screen.getByLabelText('Longitud')).toHaveValue(null)
    await user.clear(screen.getByLabelText('Nombre'))
    await user.type(screen.getByLabelText('Nombre'), 'Nombre corregido')
    await user.click(screen.getByRole('button', { name: 'Guardar cliente' }))
    await waitFor(() => expect(writes[0]?.body).toEqual({ nombre: 'Nombre corregido', telefono_whatsapp: client.telefono_whatsapp, direccion: null, lat: null, lng: null }))
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
    expect(await screen.findByText('Sin asignar')).toBeVisible()
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
    expect(await screen.findByText('Sin asignar')).toBeVisible()
  })

  it('agrupa UTC en hora chilena y ordena los horarios', async () => {
    visits = [
      { id: 'v1', fecha_hora: '2026-09-30T02:30:00Z', cliente: client, operador: null, estado: 'agendada' },
      { id: 'v2', fecha_hora: '2026-09-29T13:00:00Z', cliente: client, operador: operator, estado: 'agendada' },
    ]
    const { container } = render(<App />)
    await screen.findByText('23:30')
    expect([...container.querySelectorAll('.time')].map(el => el.firstChild.textContent)).toEqual(['10:00', '23:30'])
    expect(screen.getByText('Sin asignar')).toBeVisible()
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
