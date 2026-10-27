import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'
import { App } from '../src/main.jsx'
import { PasswordRecovery } from '../src/PasswordRecovery.jsx'

const label = 'Kill Bichos, control de plagas'
beforeEach(() => {
  localStorage.clear()
  window.history.replaceState(null, '', '/')
})

it('muestra el logo original con texto accesible en el login', () => {
  render(<App />)
  expect(screen.getByRole('img', { name: label })).toHaveAttribute('src', '/brand/kill-bichos.png')
  expect(screen.getByRole('img', { name: label })).toHaveClass('login-logo')
  expect(screen.getByRole('button', { name: 'Olvidé mi contraseña' })).toHaveClass('secondary')
})

it.each([undefined, 'A'.repeat(43)])('recuperación conserva logo y botón secundario (token %s)', token => {
  render(<PasswordRecovery token={token} onCancel={vi.fn()} onReset={vi.fn()} />)
  expect(screen.getByRole('img', { name: label })).toHaveAttribute('src', '/brand/kill-bichos.png')
  expect(screen.getByRole('button', { name: 'Volver al inicio de sesión' })).toHaveClass('secondary')
})

it('muestra el logo en la navegación y conserva los colores por estado compartidos con la app', async () => {
  localStorage.token = 'synthetic-brand-session'
  const states = ['agendada', 'en_curso', 'completada', 'cancelada', 'reagendada']
  vi.stubGlobal('fetch', vi.fn(async url => {
    const path = new URL(url).pathname
    const value = path === '/panel/visitas' ? states.map((estado, index) => ({
      id: `visita-${index}`, estado, fecha_hora: '2026-10-26T13:00:00Z', operador: null,
      cliente: { id: 'cliente', nombre: `Cliente ${index}`, direccion: null },
    })) : path === '/panel/stats' ? { visitas_hoy: 5, clientes: 5, operadores: 0 } : []
    return new Response(JSON.stringify(value), { status: 200 })
  }))
  const { container } = render(<App />)
  await waitFor(() => expect(container.querySelectorAll('.pill')).toHaveLength(5))
  expect(container.querySelector('aside img')).toHaveAttribute('alt', label)
  for (const [name, color] of [['Agendada', 'gray'], ['En curso', 'yellow'], ['Completada', 'green'], ['Cancelada', 'red'], ['Reagendada', 'blue']]) {
    expect(screen.getByText(name, { selector: '.pill' })).toHaveClass(color)
  }
})
