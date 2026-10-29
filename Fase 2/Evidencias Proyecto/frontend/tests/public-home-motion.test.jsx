// Movimiento y marca de la portada: insignia de WhatsApp, aparición al hacer
// scroll y reglas de CSS que protegen la fluidez y la accesibilidad.
import React from 'react'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { act, render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { PublicHome } from '../src/PublicHome.jsx'

const css = readFileSync(resolve('src/public-home.css'), 'utf8')

// IntersectionObserver de mentira: anota qué se observa y deja disparar a mano.
class FakeObserver {
  static instances = []
  constructor(callback) { this.callback = callback; this.observed = []; this.unobserved = []; this.disconnected = false; FakeObserver.instances.push(this) }
  observe(el) { this.observed.push(el) }
  unobserve(el) { this.unobserved.push(el) }
  disconnect() { this.disconnected = true }
}

afterEach(() => {
  FakeObserver.instances = []
  vi.unstubAllGlobals()
})

const bloques = container => [...container.querySelectorAll('[data-reveal]')]

it('la insignia de WhatsApp es decorativa, lleva los colores de la marca y no cambia el texto accesible', () => {
  const { container } = render(<PublicHome onEnter={() => {}} />)
  const badge = container.querySelector('.public-chat-badge')
  expect(badge).toHaveAttribute('aria-hidden', 'true')
  expect(badge.querySelectorAll('.public-typing')).toHaveLength(3)
  expect(badge.innerHTML).toContain('#F5C518')
  expect(badge.innerHTML).toContain('#1A1A1A')
  expect(screen.getByRole('heading', { name: 'Hablemos por WhatsApp' })).toBeVisible()
  expect(screen.getByText('WHATSAPP · DEMOSTRACIÓN')).toBeVisible()
})

it('sin IntersectionObserver todo el contenido se muestra de inmediato', () => {
  const { container } = render(<PublicHome onEnter={() => {}} />)
  expect(container.querySelector('.public-home')).not.toHaveClass('reveal-ready')
  const items = bloques(container)
  expect(items.length).toBe(10)
  items.forEach(el => expect(el).toHaveClass('is-visible'))
})

it('con IntersectionObserver los bloques esperan y aparecen una sola vez al entrar en pantalla', () => {
  vi.stubGlobal('IntersectionObserver', FakeObserver)
  const { container, unmount } = render(<PublicHome onEnter={() => {}} />)
  const [observer] = FakeObserver.instances
  const items = bloques(container)

  expect(container.querySelector('.public-home')).toHaveClass('reveal-ready')
  expect(observer.observed).toEqual(items)
  items.forEach(el => expect(el).not.toHaveClass('is-visible'))

  act(() => observer.callback([
    { isIntersecting: false, target: items[0] },
    { isIntersecting: true, target: items[1] },
  ]))
  expect(items[0]).not.toHaveClass('is-visible')
  expect(items[1]).toHaveClass('is-visible')
  expect(observer.unobserved).toEqual([items[1]]) // no se vuelve a animar

  unmount()
  expect(observer.disconnected).toBe(true)
})

it('con movimiento reducido no se oculta nada aunque exista IntersectionObserver', () => {
  vi.stubGlobal('IntersectionObserver', FakeObserver)
  vi.stubGlobal('matchMedia', query => ({ matches: query.includes('prefers-reduced-motion'), media: query, addEventListener() {}, removeEventListener() {} }))
  const { container } = render(<PublicHome onEnter={() => {}} />)
  expect(container.querySelector('.public-home')).not.toHaveClass('reveal-ready')
  bloques(container).forEach(el => expect(el).toHaveClass('is-visible'))
  expect(FakeObserver.instances.every(o => o.observed.length === 0)).toBe(true)
})

// Devuelve el cuerpo de cada @keyframes (contando llaves, porque van anidadas).
function keyframes(texto) {
  const cuerpos = []
  let i = texto.indexOf('@keyframes')
  while (i !== -1) {
    const abre = texto.indexOf('{', i)
    let nivel = 0, fin = abre
    for (; fin < texto.length; fin++) {
      if (texto[fin] === '{') nivel++
      if (texto[fin] === '}' && --nivel === 0) break
    }
    cuerpos.push(texto.slice(abre + 1, fin))
    i = texto.indexOf('@keyframes', fin)
  }
  return cuerpos
}

it('las animaciones solo mueven transform y opacity, que no traban la página', () => {
  const cuerpos = keyframes(css)
  expect(cuerpos.length).toBeGreaterThanOrEqual(3)
  const propiedades = new Set()
  cuerpos.forEach(c => [...c.matchAll(/([a-z-]+)\s*:/g)].forEach(m => propiedades.add(m[1])))
  expect([...propiedades].sort()).toEqual(['opacity', 'transform'])
})

it('el CSS no usa "transition: all" y respeta el movimiento reducido', () => {
  expect(css).not.toMatch(/transition\s*:\s*all/)
  expect(css).toContain('@media (prefers-reduced-motion:reduce)')
  expect(css).toMatch(/prefers-reduced-motion:reduce\)\{[^@]*animation:none !important/)
})

it('los efectos de mouse van solo en dispositivos con mouse', () => {
  const inicio = css.indexOf('@media (hover:hover) and (pointer:fine){')
  expect(inicio).toBeGreaterThan(-1)
  // Todo ":hover" de movimiento (translate/scale) está dentro de ese bloque.
  const fuera = css.slice(0, inicio) + css.slice(css.indexOf('@media (prefers-reduced-motion'))
  expect(fuera).not.toMatch(/:hover[^{]*\{[^}]*(translate|scale)/)
})
