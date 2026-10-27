import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, it, vi } from 'vitest'
import { App } from '../src/main.jsx'
import { PasswordRecovery } from '../src/PasswordRecovery.jsx'

const token = 'A'.repeat(43)
const message = 'Si el correo corresponde a una cuenta activa del panel, recibirás un enlace para restablecer tu contraseña.'

beforeEach(() => {
  localStorage.clear()
  window.history.replaceState(null, '', '/')
  vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ message }), { status: 202 })))
})

it('permite pedir recuperación desde el login sin enviar contraseña ni sesión', async () => {
  const user = userEvent.setup()
  render(<App />)
  await user.click(screen.getByRole('button', { name: 'Olvidé mi contraseña' }))
  await user.type(screen.getByLabelText('Correo'), 'admin@example.test')
  await user.click(screen.getByRole('button', { name: 'Enviar enlace' }))
  expect(await screen.findByRole('status')).toHaveTextContent(message)
  const [url, options] = fetch.mock.calls[0]
  expect(url).toMatch(/\/auth\/forgot-password$/)
  expect(JSON.parse(options.body)).toEqual({ email: 'admin@example.test' })
  expect(options.headers.Authorization).toBeUndefined()
})

it('borra el enlace de la barra y abre nueva contraseña aunque había una sesión', async () => {
  localStorage.token = 'sesion-anterior'
  window.history.replaceState(null, '', `/#restablecer=${token}`)
  render(<App />)
  expect(screen.getByRole('heading', { name: 'Nueva contraseña' })).toBeInTheDocument()
  await waitFor(() => expect(window.location.hash).toBe(''))
  expect(fetch).not.toHaveBeenCalled()
})

it('no permite guardar si la confirmación no coincide', async () => {
  const user = userEvent.setup()
  render(<PasswordRecovery token={token} onCancel={vi.fn()} onReset={vi.fn()} />)
  await user.type(screen.getByLabelText('Nueva contraseña'), 'NuevaClaveSegura2026!')
  await user.type(screen.getByLabelText('Confirmar contraseña'), 'OtraClaveSegura2026!')
  await user.click(screen.getByRole('button', { name: 'Guardar contraseña' }))
  expect(screen.getByRole('alert')).toHaveTextContent('no coinciden')
  expect(fetch).not.toHaveBeenCalled()
})

it('valida máximo de bytes UTF8 antes de enviar', async () => {
  const user = userEvent.setup()
  render(<PasswordRecovery token={token} onCancel={vi.fn()} onReset={vi.fn()} />)
  await user.type(screen.getByLabelText('Nueva contraseña'), 'ñ'.repeat(37))
  await user.type(screen.getByLabelText('Confirmar contraseña'), 'ñ'.repeat(37))
  await user.click(screen.getByRole('button', { name: 'Guardar contraseña' }))
  expect(screen.getByRole('alert')).toHaveTextContent('72 bytes')
  expect(fetch).not.toHaveBeenCalled()
})

it('guarda por POST sin Authorization ni token en URL, vuelve al login sin sesión', async () => {
  const user = userEvent.setup()
  localStorage.token = 'sesion-anterior'
  window.history.replaceState(null, '', `/#restablecer=${token}`)
  fetch.mockResolvedValue(new Response(JSON.stringify({ message: 'Contraseña actualizada.' }), { status: 200 }))
  render(<App />)
  await user.type(screen.getByLabelText('Nueva contraseña'), 'NuevaClaveSegura2026!')
  await user.type(screen.getByLabelText('Confirmar contraseña'), 'NuevaClaveSegura2026!')
  await user.click(screen.getByRole('button', { name: 'Guardar contraseña' }))
  expect(await screen.findByRole('button', { name: 'Ingresar al panel' })).toBeInTheDocument()
  expect(screen.getByRole('status')).toHaveTextContent('Contraseña actualizada')
  expect(localStorage.token).toBeUndefined()
  const [url, options] = fetch.mock.calls[0]
  expect(url).not.toContain(token)
  expect(options.headers.Authorization).toBeUndefined()
  expect(JSON.parse(options.body)).toEqual({ token, password: 'NuevaClaveSegura2026!' })
  expect(sessionStorage.length).toBe(0)
})

it('muestra enlace vencido sin cerrar sesión por un error público y permite volver', async () => {
  const user = userEvent.setup()
  fetch.mockResolvedValue(new Response(JSON.stringify({ detail: 'El enlace no es válido o ya venció. Solicita uno nuevo.' }), { status: 400 }))
  window.history.replaceState(null, '', `/#restablecer=${token}`)
  render(<App />)
  await user.type(screen.getByLabelText('Nueva contraseña'), 'NuevaClaveSegura2026!')
  await user.type(screen.getByLabelText('Confirmar contraseña'), 'NuevaClaveSegura2026!')
  await user.click(screen.getByRole('button', { name: 'Guardar contraseña' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Solicita uno nuevo')
  await user.click(screen.getByRole('button', { name: 'Volver al inicio de sesión' }))
  expect(screen.getByRole('button', { name: 'Olvidé mi contraseña' })).toBeInTheDocument()
})

it('muestra error de límite de intentos sin confirmar envío', async () => {
  const user = userEvent.setup()
  fetch.mockResolvedValue(new Response(JSON.stringify({ detail: 'Demasiados intentos. Espera 15 minutos.' }), { status: 429 }))
  render(<PasswordRecovery onCancel={vi.fn()} onReset={vi.fn()} />)
  await user.type(screen.getByLabelText('Correo'), 'admin@example.test')
  await user.click(screen.getByRole('button', { name: 'Enviar enlace' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Demasiados intentos')
  expect(screen.queryByRole('status')).not.toBeInTheDocument()
})

it('deshabilita controles durante el envío y evita solicitudes duplicadas', async () => {
  const user = userEvent.setup()
  let resolve
  fetch.mockImplementation(() => new Promise(done => { resolve = done }))
  render(<PasswordRecovery onCancel={vi.fn()} onReset={vi.fn()} />)
  await user.type(screen.getByLabelText('Correo'), 'admin@example.test')
  await user.dblClick(screen.getByRole('button', { name: 'Enviar enlace' }))
  expect(fetch).toHaveBeenCalledTimes(1)
  expect(screen.getByRole('button', { name: 'Volver al inicio de sesión' })).toBeDisabled()
  resolve(new Response(JSON.stringify({ message }), { status: 202 }))
  expect(await screen.findByRole('status')).toHaveTextContent(message)
})

it('avisa cuando el envío de correo no está habilitado sin simular éxito', async () => {
  const user = userEvent.setup()
  fetch.mockResolvedValue(new Response(JSON.stringify({ detail: 'No habilitado' }), { status: 503 }))
  render(<PasswordRecovery onCancel={vi.fn()} onReset={vi.fn()} />)
  await user.type(screen.getByLabelText('Correo'), 'admin@example.test')
  await user.click(screen.getByRole('button', { name: 'Enviar enlace' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Contacta al soporte')
  expect(screen.queryByRole('status')).not.toBeInTheDocument()
})
