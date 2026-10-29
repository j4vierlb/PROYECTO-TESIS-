import React from 'react'
import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { renderAccess } from './support/render-access.jsx'

const ana = { id: 'tec-1', nombre: 'Ana Pérez', email: 'ana@killbichos.test', telefono: '+56911112222', activo: true }
const beto = { id: 'tec-2', nombre: 'Beto Soto', email: 'beto@killbichos.test', telefono: null, activo: false }
let team, writes, failWith

beforeEach(() => {
  localStorage.token = 'sesion-de-prueba'
  team = [ana, beto]
  writes = []
  failWith = null
  vi.stubGlobal('fetch', vi.fn(async (url, options = {}) => {
    const { pathname, search } = new URL(url)
    if (options.method === 'POST' || options.method === 'PATCH') {
      const body = JSON.parse(options.body)
      writes.push({ method: options.method, path: pathname, body })
      if (failWith) return new Response(JSON.stringify({ detail: failWith }), { status: 409 })
      if (options.method === 'POST') {
        const created = { id: 'tec-nuevo', nombre: body.nombre, email: body.email, telefono: body.telefono, activo: true }
        team = [...team, created]
        return new Response(JSON.stringify(created), { status: 201 })
      }
      const id = pathname.split('/').pop()
      team = team.map(t => t.id === id ? { ...t, ...Object.fromEntries(Object.entries(body).filter(([k]) => k !== 'clave')) } : t)
      return new Response(JSON.stringify(team.find(t => t.id === id)), { status: 200 })
    }
    const bodies = {
      '/panel/operadores': search.includes('incluir_inactivos=true') ? team : team.filter(t => t.activo),
      '/panel/visitas': [], '/panel/stats': { clientes: 0, visitas_hoy: 0, pendientes: 0 }, '/clientes': [],
    }
    return new Response(JSON.stringify(bodies[pathname]), { status: 200 })
  }))
})

async function abrirEquipo(user) {
  renderAccess()
  await user.click(screen.getByRole('button', { name: /Equipo/ }))
  await screen.findByText('Ana Pérez')
}

describe('Equipo: gestión de técnicos desde el panel', () => {
  it('lista activos e inactivos y cuenta solo los activos', async () => {
    const user = userEvent.setup()
    await abrirEquipo(user)
    expect(screen.getByRole('heading', { name: 'Equipo' })).toBeVisible()
    expect(screen.getByText('1 técnico activo de 2')).toBeVisible()
    const tabla = screen.getByRole('region', { name: 'Técnicos' })
    expect(within(tabla).getByText('Activo')).toHaveClass('green')
    expect(within(tabla).getByText('Inactivo')).toHaveClass('gray')
    expect(within(tabla).getByText('Sin teléfono')).toBeVisible()
    expect(globalThis.fetch.mock.calls.some(([url]) => url.includes('/panel/operadores?incluir_inactivos=true'))).toBe(true)
  })

  it('crea un técnico con la clave inicial y lo muestra en la lista', async () => {
    const user = userEvent.setup()
    await abrirEquipo(user)
    await user.click(screen.getByRole('button', { name: /Nuevo técnico/ }))
    await user.type(screen.getByLabelText('Nombre'), '  Carla Rojas ')
    await user.type(screen.getByLabelText('Correo'), 'carla@killbichos.test')
    await user.type(screen.getByLabelText('Clave inicial'), 'ClaveSegura2026!')
    await user.click(screen.getByRole('button', { name: 'Crear técnico' }))
    await waitFor(() => expect(writes[0]).toEqual({ method: 'POST', path: '/panel/operadores', body: { nombre: 'Carla Rojas', email: 'carla@killbichos.test', telefono: null, clave: 'ClaveSegura2026!' } }))
    expect(await screen.findByText('Carla Rojas')).toBeVisible()
    expect(screen.getByRole('status')).toHaveTextContent('Técnico creado')
  })

  it('no envía una clave corta y muestra el error del servidor si el correo ya existe', async () => {
    const user = userEvent.setup()
    await abrirEquipo(user)
    await user.click(screen.getByRole('button', { name: /Nuevo técnico/ }))
    await user.type(screen.getByLabelText('Nombre'), 'Dani')
    await user.type(screen.getByLabelText('Correo'), 'ana@killbichos.test')
    // minLength del navegador no aplica en jsdom al enviar: la validación propia lo frena.
    await user.type(screen.getByLabelText('Clave inicial'), 'corta')
    await user.click(screen.getByRole('button', { name: 'Crear técnico' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('entre 12 y 72 caracteres')
    expect(writes).toHaveLength(0)
    await user.clear(screen.getByLabelText('Clave inicial'))
    await user.type(screen.getByLabelText('Clave inicial'), 'ClaveSegura2026!')
    failWith = 'Ya existe una cuenta con ese correo'
    await user.click(screen.getByRole('button', { name: 'Crear técnico' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Ya existe una cuenta con ese correo')
  })

  it('edita solo lo que cambió, deja el correo fijo y permite una clave nueva', async () => {
    const user = userEvent.setup()
    await abrirEquipo(user)
    await user.click(within(screen.getByText('Ana Pérez').closest('.client-row')).getByRole('button', { name: 'Editar' }))
    expect(screen.getByLabelText('Correo')).toHaveAttribute('readonly')
    await user.clear(screen.getByLabelText('Nombre'))
    await user.type(screen.getByLabelText('Nombre'), 'Ana P. Pérez')
    await user.type(screen.getByLabelText('Nueva clave (opcional)'), 'OtraClaveSegura99')
    await user.click(screen.getByRole('button', { name: 'Guardar cambios' }))
    await waitFor(() => expect(writes[0]).toEqual({ method: 'PATCH', path: '/panel/operadores/tec-1', body: { nombre: 'Ana P. Pérez', clave: 'OtraClaveSegura99' } }))
    expect(await screen.findByText('Ana P. Pérez')).toBeVisible()
  })

  it('pide confirmación para desactivar, avisa de las visitas pendientes y luego reactiva', async () => {
    const user = userEvent.setup()
    await abrirEquipo(user)
    await user.click(within(screen.getByText('Ana Pérez').closest('.client-row')).getByRole('button', { name: 'Desactivar' }))
    expect(screen.getByRole('dialog', { name: 'Desactivar técnico' })).toBeVisible()
    expect(screen.getByText(/visitas pendientes siguen asignadas/)).toBeVisible()
    expect(writes).toHaveLength(0)
    await user.click(screen.getByRole('button', { name: 'Confirmar desactivación' }))
    await waitFor(() => expect(writes[0]).toEqual({ method: 'PATCH', path: '/panel/operadores/tec-1', body: { activo: false } }))
    await waitFor(() => expect(screen.getByText('0 técnicos activos de 2')).toBeVisible())
    await user.click(within(screen.getByText('Beto Soto').closest('.client-row')).getByRole('button', { name: 'Reactivar' }))
    await user.click(screen.getByRole('button', { name: 'Confirmar reactivación' }))
    await waitFor(() => expect(writes[1]).toEqual({ method: 'PATCH', path: '/panel/operadores/tec-2', body: { activo: true } }))
  })
})
