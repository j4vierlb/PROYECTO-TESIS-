import React from 'react'
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import jsQR from 'jsqr'
import { App } from '../src/main.jsx'
import { PublicHome } from '../src/PublicHome.jsx'
import { sandboxLink } from '../src/whatsapp-sandbox.js'
import { SESSION_EXPIRED } from '../src/api.js'

const sandbox = { phone: '+1 (555) 555-0123', joinMessage: 'join prueba-local' }
const href = 'https://wa.me/15555550123?text=join%20prueba-local'
const token = 'A'.repeat(43)

beforeEach(() => {
  localStorage.clear()
  window.history.replaceState(null, '', '/')
  vi.stubGlobal('fetch', vi.fn(async url => new Response(JSON.stringify(new URL(url).pathname === '/panel/stats' ? { clientes: 0, visitas_hoy: 0, pendientes: 0 } : []), { status: 200 })))
})
afterEach(() => {
  window.history.replaceState(null, '', '/')
  vi.unstubAllGlobals()
})

it('sin sesión muestra la portada, sus servicios y contacto, sin consultar la API', () => {
  render(<App />)
  expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Kill Bichos')
  expect(screen.getByRole('heading', { name: 'Quiénes somos' })).toBeVisible()
  for (const name of ['Desinsectación', 'Desratización', 'Sanitización']) expect(screen.getByRole('heading', { name })).toBeVisible()
  expect(screen.getByText('Av. Luis Valenzuela Aris 3273, Macul, Santiago, Chile.')).toBeVisible()
  expect(screen.getByRole('link', { name: '+56 9 9093 0634' })).toHaveAttribute('href', 'tel:+56990930634')
  expect(screen.getByRole('link', { name: 'ventas@killbichos.cl' })).toHaveAttribute('href', 'mailto:ventas@killbichos.cl')
  expect(screen.queryByLabelText('Contraseña')).not.toBeInTheDocument()
  expect(fetch).not.toHaveBeenCalled()
})

it('Ingresar abre el mismo login vacío, sin solicitudes ni sesión creada', async () => {
  const user = userEvent.setup()
  render(<App />)
  await user.click(screen.getByRole('button', { name: 'Ingresar', exact: true }))
  expect(screen.getByRole('heading', { name: 'Bienvenido a Kill Bichos' })).toBeVisible()
  expect(screen.getByLabelText('Correo')).toHaveValue('')
  expect(screen.getByLabelText('Contraseña')).toHaveValue('')
  expect(screen.getByRole('button', { name: 'Olvidé mi contraseña' })).toBeVisible()
  expect(localStorage.token).toBeUndefined()
  expect(fetch).not.toHaveBeenCalled()
})

it('Ingresar se puede activar con teclado', async () => {
  const user = userEvent.setup()
  render(<App />)
  screen.getByRole('button', { name: 'Ingresar', exact: true }).focus()
  await user.keyboard('{Enter}')
  expect(screen.getByLabelText('Correo')).toBeVisible()
})

it('con sesión muestra primero la portada y solo entra al panel al pulsar Ingresar', async () => {
  const user = userEvent.setup()
  localStorage.token = 'synthetic-public-home-session'
  render(<App />)
  expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Kill Bichos')
  expect(screen.queryByRole('heading', { name: 'Agenda' })).not.toBeInTheDocument()
  expect(fetch).not.toHaveBeenCalled()
  await user.click(screen.getByRole('button', { name: 'Ingresar', exact: true }))
  expect(await screen.findByRole('heading', { name: 'Agenda' })).toBeVisible()
  expect(screen.queryByLabelText('Contraseña')).not.toBeInTheDocument()
  expect(within(screen.getByRole('navigation', { name: 'Navegación principal' })).getAllByRole('button')).toHaveLength(3)
  expect(screen.queryByRole('button', { name: 'Ingresar', exact: true })).not.toBeInTheDocument()
  await waitFor(() => expect(screen.getByRole('button', { name: /Nueva visita/ })).toBeEnabled())
})

it.each([false, true])('el enlace restablecer tiene prioridad sobre portada y panel: sesión=%s', async session => {
  if (session) localStorage.token = 'synthetic-existing-session'
  window.history.replaceState(null, '', `/#restablecer=${token}`)
  render(<App />)
  expect(screen.getByRole('heading', { name: 'Nueva contraseña' })).toBeVisible()
  expect(screen.queryByRole('heading', { name: 'Agenda' })).not.toBeInTheDocument()
  await waitFor(() => expect(window.location.hash).toBe(''))
  expect(fetch).not.toHaveBeenCalled()
})

it('un enlace de recuperación recibido con la portada abierta también se consume', async () => {
  render(<App />)
  act(() => {
    window.history.replaceState(null, '', `/#restablecer=${token}`)
    window.dispatchEvent(new Event('hashchange'))
  })
  expect(await screen.findByRole('heading', { name: 'Nueva contraseña' })).toBeVisible()
  expect(window.location.hash).toBe('')
  expect(fetch).not.toHaveBeenCalled()
})

it('cerrar sesión en otra pestaña conserva el aviso y vuelve al login', async () => {
  const user = userEvent.setup()
  localStorage.token = 'synthetic-tab-session'
  render(<App />)
  await user.click(screen.getByRole('button', { name: 'Ingresar', exact: true }))
  await screen.findByRole('heading', { name: 'Agenda' })
  act(() => {
    localStorage.removeItem('token')
    window.dispatchEvent(new StorageEvent('storage', { key: 'token', newValue: null }))
  })
  expect(screen.getByRole('status')).toHaveTextContent('otra pestaña')
  expect(screen.getByRole('button', { name: 'Ingresar al panel' })).toBeVisible()
})

it('una sesión vencida no desvía el aviso hacia la portada', async () => {
  const user = userEvent.setup()
  localStorage.token = 'synthetic-expired-session'
  render(<App />)
  await user.click(screen.getByRole('button', { name: 'Ingresar', exact: true }))
  await screen.findByRole('heading', { name: 'Agenda' })
  act(() => {
    localStorage.removeItem('token')
    window.dispatchEvent(new Event(SESSION_EXPIRED))
  })
  expect(screen.getByRole('status')).toHaveTextContent('Tu sesión venció')
  expect(screen.getByLabelText('Correo')).toBeVisible()
})

it('volver a abrir el sistema muestra la portada y conserva la sesión sin validarla en segundo plano', async () => {
  const user = userEvent.setup()
  localStorage.token = 'synthetic-retained-session'
  const first = render(<App />)
  await user.click(screen.getByRole('button', { name: 'Ingresar', exact: true }))
  await screen.findByRole('heading', { name: 'Agenda' })
  await waitFor(() => expect(screen.getByRole('button', { name: /Nueva visita/ })).toBeEnabled())
  first.unmount()
  fetch.mockClear()
  render(<App />)
  expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Kill Bichos')
  expect(localStorage.token).toBe('synthetic-retained-session')
  expect(screen.queryByRole('heading', { name: 'Agenda' })).not.toBeInTheDocument()
  expect(fetch).not.toHaveBeenCalled()
})

it('la guía tiene tres pasos y explica que el usuario debe enviar el mensaje', () => {
  render(<PublicHome onEnter={vi.fn()} sandbox={sandbox} />)
  expect(screen.getAllByRole('listitem')).toHaveLength(3)
  expect(screen.getByRole('heading', { name: 'Envía el mensaje de unión' })).toBeVisible()
  expect(screen.getByText(/quiero agendar una visita/)).toBeVisible()
  expect(screen.getByText(/Tú debes enviarlo desde WhatsApp/)).toBeVisible()
  expect(screen.getByText(/No es un servicio abierto al público/)).toBeVisible()
  expect(fetch).not.toHaveBeenCalled()
})

it('el botón y el QR usan el mismo destino con el mensaje de unión codificado', () => {
  render(<PublicHome onEnter={vi.fn()} sandbox={sandbox} />)
  const button = screen.getByRole('link', { name: 'Hablemos por WhatsApp' })
  const qrLink = screen.getByRole('link', { name: 'Abrir WhatsApp de prueba desde el código QR' })
  for (const link of [button, qrLink]) {
    expect(link).toHaveAttribute('href', href)
    expect(link).toHaveAttribute('target', '_blank')
    expect(link).toHaveAttribute('rel', 'noopener noreferrer')
  }
  expect(new URL(button.href).searchParams.get('text')).toBe(sandbox.joinMessage)
  expect(fetch).not.toHaveBeenCalled()
})

it.each([
  ['datos sintéticos', sandbox, href],
  ['QR proporcionado por Juan', undefined, 'https://wa.me/14155238886?text=join%20example-primitive'],
])('decodifica el QR SVG y recupera el destino exacto del botón: %s', (_, config, expected) => {
  render(<PublicHome onEnter={vi.fn()} sandbox={config} />)
  const qr = screen.getByRole('img', { name: /Código QR/ })
  const size = Number(qr.getAttribute('viewBox').split(' ')[3])
  const scale = 6, width = size * scale
  const pixels = new Uint8ClampedArray(width * width * 4).fill(255)
  for (const [, x, y] of qr.querySelector('path').getAttribute('d').matchAll(/M(\d+) (\d+)h1v1h-1z/g)) {
    for (let dy = 0; dy < scale; dy++) for (let dx = 0; dx < scale; dx++) {
      const offset = ((Number(y) * scale + dy) * width + Number(x) * scale + dx) * 4
      pixels[offset] = pixels[offset + 1] = pixels[offset + 2] = 0
    }
  }
  const decoded = jsQR(pixels, width, width)?.data
  expect(decoded).toBe(expected)
  expect(decoded).toBe(screen.getByRole('link', { name: 'Hablemos por WhatsApp' }).href)
})

it.each([{ phone: '', joinMessage: '' }, { phone: '+15555550123', joinMessage: '' }, { phone: 'javascript:alert(1)', joinMessage: 'join prueba-local' }])('sin configuración válida no inventa QR ni enlaces: %j', sandbox => {
  render(<PublicHome onEnter={vi.fn()} sandbox={sandbox} />)
  expect(screen.getByRole('button', { name: 'Hablemos por WhatsApp' })).toBeDisabled()
  expect(screen.queryByRole('img', { name: /Código QR/ })).not.toBeInTheDocument()
  expect(screen.queryByRole('link', { name: 'Hablemos por WhatsApp' })).not.toBeInTheDocument()
  expect(screen.getByText(/no está disponible por el momento/)).toBeVisible()
})

it('muestra el horario confirmado por Juan y conserva la fuente corporativa', () => {
  render(<PublicHome onEnter={vi.fn()} sandbox={sandbox} />)
  expect(screen.getByText('Lunes a sábado, de 08:00 a 18:00 horas.')).toBeVisible()
  expect(screen.getByRole('link', { name: /Sitio de la empresa/ })).toHaveAttribute('href', 'https://killbichos.cl/')
})

it('usa anclas internas para servicios y contacto sin interferir con restablecer', () => {
  render(<App />)
  for (const [name, target] of [['Servicios', '#servicios'], ['Contacto', '#contacto']]) {
    expect(screen.getByRole('link', { name, exact: true })).toHaveAttribute('href', target)
  }
  expect(screen.getByRole('link', { name: 'Saltar al contenido' })).toHaveAttribute('href', '#contenido-publico')
  expect(screen.queryByRole('heading', { name: 'Nueva contraseña' })).not.toBeInTheDocument()
})

it('la portada conserva el logo y restaura el título al ingresar al panel', async () => {
  const previous = document.title
  const user = userEvent.setup()
  render(<App />)
  expect(screen.getByRole('img', { name: 'Kill Bichos, control de plagas' })).toHaveAttribute('src', '/brand/kill-bichos.png')
  expect(document.title).toBe('Kill Bichos | Control de plagas')
  await user.click(screen.getByRole('button', { name: 'Ingresar', exact: true }))
  expect(document.title).toBe(previous)
})

it('el botón Ingresar ejecuta solo la navegación solicitada', () => {
  const enter = vi.fn()
  render(<PublicHome onEnter={enter} sandbox={sandbox} />)
  fireEvent.click(screen.getByRole('button', { name: 'Ingresar', exact: true }))
  expect(enter).toHaveBeenCalledTimes(1)
  expect(fetch).not.toHaveBeenCalled()
})

it('normaliza el número pero conserva el mensaje exacto de unión', () => {
  expect(sandboxLink(sandbox)).toBe(href)
  expect(sandboxLink({ phone: '15555550123', joinMessage: 'join prueba-local' })).toBe(href)
})

it.each([
  undefined, {}, { phone: 15555550123, joinMessage: 'join prueba-local' },
  { phone: '+05555550123', joinMessage: 'join prueba-local' },
  { phone: '+15555550123?text=otro', joinMessage: 'join prueba-local' },
  { phone: '+15555550123', joinMessage: 'hola' },
  { phone: '+15555550123', joinMessage: 'join prueba\notro' },
  { phone: '+15555550123', joinMessage: 'join ' + 'a'.repeat(100) },
])('rechaza datos inválidos sin enlaces externos arbitrarios: %j', config => {
  expect(sandboxLink(config)).toBeNull()
})
