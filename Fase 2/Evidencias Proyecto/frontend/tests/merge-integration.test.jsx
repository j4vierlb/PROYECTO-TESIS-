import React from 'react'
import { readFileSync } from 'node:fs'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, it, vi } from 'vitest'
import { App } from '../src/main.jsx'
import { chileDateTime } from '../src/panel-utils.js'

const createdAt = '2026-10-26T13:00:00Z'
let detail, writes

beforeEach(() => {
  window.history.replaceState(null, '', '/')
  localStorage.token = 'synthetic-merge-session'
  writes = []
  detail = {
    id: 'conversation-merge', cliente: { id: 'client-merge', nombre: 'Cliente integración QA', telefono_whatsapp: '+00000000001' },
    atendida_por_humano: false, ventana_abierta: true, ultimo_emisor: 'cliente', ultimo_mensaje: 'Consulta QA',
    mensajes: [{ id: 'message-merge', emisor: 'sistema', contenido: 'Aviso QA', created_at: createdAt, estado_entrega: 'delivered' }],
  }
  vi.stubGlobal('fetch', vi.fn(async (url, options = {}) => {
    const path = new URL(url).pathname
    let value = []
    if (options.method === 'POST' || options.method === 'PATCH') {
      const body = options.body ? JSON.parse(options.body) : {}
      writes.push({ path, body, method: options.method })
      if (path.endsWith('/mensajes')) {
        const message = { id: 'outgoing-merge', emisor: 'operador', contenido: body.contenido, created_at: createdAt, estado_entrega: 'sent' }
        detail = { ...detail, atendida_por_humano: true, mensajes: [...detail.mensajes, message] }
        value = message
      } else if (path.endsWith('/recordatorios')) value = { enviados: 1, no_enviados: 0 }
      else { detail = { ...detail, ...body }; value = detail }
    } else if (path === '/panel/stats') value = { visitas_hoy: 0, clientes: 1, operadores: 0 }
    else if (path === '/panel/conversaciones') value = [detail]
    else if (path === `/panel/conversaciones/${detail.id}`) value = detail
    return new Response(JSON.stringify(value), { status: 200 })
  }))
})

async function inbox(user) {
  render(<App />)
  await user.click(screen.getByRole('button', { name: 'Ingresar', exact: true }))
  await user.click(screen.getByRole('button', { name: /WhatsApp/ }))
  await screen.findByText('Aviso QA')
}

it('mantiene logo, las tres vistas y la bandeja con fechas de Chile', async () => {
  const user = userEvent.setup()
  await inbox(user)
  const nav = screen.getByRole('navigation', { name: 'Navegación principal' })
  expect(within(nav).getAllByRole('button')).toHaveLength(4)
  expect(screen.getByRole('img', { name: 'Kill Bichos, control de plagas' })).toBeVisible()
  expect(screen.getByText(`Aviso automático · ${chileDateTime(createdAt)}`)).toBeVisible()
  expect(screen.getByText('✓✓ Entregado')).toBeVisible()
  expect(writes).toHaveLength(0)
})

it('permite responder en la bandeja y conserva los estados de entrega', async () => {
  const user = userEvent.setup()
  await inbox(user)
  await user.type(screen.getByRole('textbox', { name: 'Mensaje para el cliente' }), 'Respuesta sintética QA')
  await user.click(screen.getByRole('button', { name: 'Enviar', exact: true }))
  expect(await screen.findByText('Respuesta sintética QA')).toBeVisible()
  expect(screen.getByText('✓ Enviado')).toBeVisible()
  expect(writes).toEqual([{ path: '/panel/conversaciones/conversation-merge/mensajes', method: 'POST', body: { contenido: 'Respuesta sintética QA' } }])
})

it('conserva tomar/devolver conversación y el envío manual de recordatorios', async () => {
  const user = userEvent.setup()
  await inbox(user)
  await user.click(screen.getByRole('button', { name: 'Tomar conversación' }))
  await user.click(await screen.findByRole('button', { name: 'Devolver a la IA' }))
  await screen.findByRole('button', { name: 'Tomar conversación' })
  await user.click(screen.getByRole('button', { name: 'Enviar recordatorios de mañana' }))
  await waitFor(() => expect(screen.getByText('Recordatorios de mañana enviados: 1')).toBeVisible())
  expect(writes.map(write => write.body)).toEqual([{ atendida_por_humano: true }, { atendida_por_humano: false }, {}])
})

it('conserva recuperación después de cerrar sesión desde WhatsApp', async () => {
  const user = userEvent.setup()
  await inbox(user)
  await user.click(screen.getByRole('button', { name: 'Cerrar sesión' }))
  await user.click(screen.getByRole('button', { name: 'Olvidé mi contraseña' }))
  expect(screen.getByRole('heading', { name: 'Recuperar contraseña' })).toBeVisible()
  expect(screen.getByRole('textbox', { name: 'Correo' })).toBeVisible()
  expect(screen.getByRole('img', { name: 'Kill Bichos, control de plagas' })).toBeVisible()
})

it('los estilos combinados incluyen marca, bandeja y composición de mensajes', () => {
  const css = readFileSync('src/styles.css', 'utf8')
  for (const selector of ['--brand-yellow', '.company-logo', '.inbox-list', '.thread-head', '.messages', '.bubble', '.delivery', '.composer']) {
    expect(css).toContain(selector)
  }
  expect(css).toContain('.inbox-item.active{background:var(--brand-soft)}')
  expect(css).not.toMatch(/^(<<<<<<<|=======|>>>>>>>)/m)
})
