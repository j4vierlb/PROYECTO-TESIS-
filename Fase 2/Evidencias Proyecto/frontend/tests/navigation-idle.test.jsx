import React from 'react'
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { App } from '../src/main.jsx'

const FIVE_MINUTES = 5 * 60 * 1000
const response = data => new Response(JSON.stringify(data), { status: 200 })
const apiData = url => new URL(url).pathname === '/panel/stats' ? { clientes: 0, visitas_hoy: 0, pendientes: 0 } : []

beforeEach(() => {
  localStorage.clear()
  window.history.replaceState(null, '', '/')
  vi.stubGlobal('fetch', vi.fn(async url => response(apiData(url))))
})
afterEach(() => {
  cleanup()
  vi.useRealTimers()
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

it.each(['Agenda', 'Clientes', 'WhatsApp', 'Equipo'])('permite volver a la portada desde %s y regresar sin perder la sesión', async view => {
  const user = userEvent.setup()
  localStorage.token = 'synthetic-navigation-session'
  render(<App />)
  await screen.findByRole('heading', { name: 'Agenda' })
  await user.click(screen.getByRole('button', { name: view, exact: true }))
  await user.click(screen.getByRole('button', { name: 'Volver a la página principal', exact: true }))
  expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Kill Bichos')
  expect(localStorage.token).toBe('synthetic-navigation-session')
  fetch.mockClear()
  await user.click(screen.getByRole('button', { name: 'Ingresar', exact: true }))
  expect(screen.getByRole('navigation', { name: 'Navegación principal' })).toBeVisible()
  expect(screen.queryByLabelText('Contraseña')).not.toBeInTheDocument()
  expect(fetch.mock.calls.every(([url]) => !url.endsWith('/auth/login'))).toBe(true)
  await waitFor(() => expect(screen.queryByText(/Cargando (agenda|equipo|conversaciones|clientes)/)).not.toBeInTheDocument())
})

it('Ingresar reconoce una sesión iniciada en otra pestaña después de abrir la portada', async () => {
  const user = userEvent.setup()
  render(<App />)
  expect(fetch).not.toHaveBeenCalled()
  localStorage.token = 'synthetic-other-tab-session'
  await user.click(screen.getByRole('button', { name: 'Ingresar', exact: true }))
  expect(await screen.findByRole('heading', { name: 'Agenda' })).toBeVisible()
  expect(screen.queryByLabelText('Contraseña')).not.toBeInTheDocument()
  await waitFor(() => expect(screen.getByRole('button', { name: /Nueva visita/ })).toBeEnabled())
})

describe('Inactividad solo en la pantalla de login', () => {
  beforeEach(() => { vi.useFakeTimers() })

  function login() {
    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: 'Ingresar', exact: true }))
    expect(screen.getByLabelText('Contraseña')).toBeVisible()
  }
  function advance(ms) { act(() => { vi.advanceTimersByTime(ms) }) }

  it('vuelve a la portada a los cinco minutos y descarta los campos del login', () => {
    login()
    fireEvent.change(screen.getByLabelText('Correo'), { target: { value: 'qa@example.test' } })
    fireEvent.change(screen.getByLabelText('Contraseña'), { target: { value: 'ClaveTemporalQA123!' } })
    advance(FIVE_MINUTES - 1)
    expect(screen.getByLabelText('Contraseña')).toBeVisible()
    advance(1)
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Kill Bichos')
    expect(screen.queryByLabelText('Contraseña')).not.toBeInTheDocument()
    expect(fetch).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Ingresar', exact: true }))
    expect(screen.getByLabelText('Correo')).toHaveValue('')
    expect(screen.getByLabelText('Contraseña')).toHaveValue('')
  })

  it.each(['keydown', 'pointermove', 'pointerdown', 'wheel', 'input', 'touchstart'])('reinicia la espera cuando hay actividad: %s', event => {
    login()
    advance(4 * 60 * 1000)
    fireEvent(window, new Event(event, { bubbles: true }))
    advance(2 * 60 * 1000)
    expect(screen.getByLabelText('Contraseña')).toBeVisible()
    advance(3 * 60 * 1000)
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Kill Bichos')
  })

  it.each(['focus', 'visibilitychange'])('detecta la inactividad al regresar a la pestaña aunque el navegador haya retrasado el timer: %s', event => {
    login()
    vi.setSystemTime(Date.now() + FIVE_MINUTES + 1)
    if (event === 'visibilitychange') {
      vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('visible')
      fireEvent(document, new Event(event))
    } else fireEvent(window, new Event(event))
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Kill Bichos')
    expect(screen.queryByLabelText('Contraseña')).not.toBeInTheDocument()
  })

  it('permite volver manualmente desde el login y da cinco minutos nuevos al regresar', () => {
    login()
    advance(4 * 60 * 1000)
    fireEvent.click(screen.getByRole('button', { name: 'Volver a la página principal', exact: true }))
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Kill Bichos')
    advance(FIVE_MINUTES)
    fireEvent.click(screen.getByRole('button', { name: 'Ingresar', exact: true }))
    advance(FIVE_MINUTES - 1)
    expect(screen.getByLabelText('Contraseña')).toBeVisible()
    advance(1)
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Kill Bichos')
  })

  it('no interrumpe la recuperación ni un enlace de restablecimiento', () => {
    login()
    fireEvent.click(screen.getByRole('button', { name: 'Olvidé mi contraseña' }))
    advance(2 * FIVE_MINUTES)
    expect(screen.getByRole('heading', { name: 'Recuperar contraseña' })).toBeVisible()
    act(() => {
      window.history.replaceState(null, '', '/#restablecer=' + 'A'.repeat(43))
      window.dispatchEvent(new Event('hashchange'))
    })
    advance(2 * FIVE_MINUTES)
    expect(screen.getByRole('heading', { name: 'Nueva contraseña' })).toBeVisible()
    expect(fetch).not.toHaveBeenCalled()
  })

  it('pausa la salida durante un ingreso en curso y no expulsa al usuario una vez dentro del panel', async () => {
    let resolveLogin
    fetch.mockImplementation(url => url.endsWith('/auth/login')
      ? new Promise(resolve => { resolveLogin = resolve })
      : Promise.resolve(response(apiData(url))))
    login()
    fireEvent.change(screen.getByLabelText('Correo'), { target: { value: 'qa@example.test' } })
    fireEvent.change(screen.getByLabelText('Contraseña'), { target: { value: 'ClaveTemporalQA123!' } })
    fireEvent.click(screen.getByRole('button', { name: 'Ingresar al panel' }))
    expect(screen.getByRole('button', { name: 'Ingresando…' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Volver a la página principal' })).toBeDisabled()
    vi.setSystemTime(Date.now() + FIVE_MINUTES + 1)
    fireEvent(window, new Event('focus'))
    expect(screen.getByRole('button', { name: 'Ingresando…' })).toBeVisible()
    await act(async () => resolveLogin(response({ access_token: 'synthetic-new-session' })))
    expect(screen.getByRole('heading', { name: 'Agenda' })).toBeVisible()
    advance(2 * FIVE_MINUTES)
    expect(screen.getByRole('heading', { name: 'Agenda' })).toBeVisible()
    expect(localStorage.token).toBe('synthetic-new-session')
  })
})
