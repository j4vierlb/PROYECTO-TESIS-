import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { expect, it } from 'vitest'

it('el logo web es una copia exacta del original compartido con iOS', () => {
  const webLogo = readFileSync(resolve('public/brand/kill-bichos.png'))
  const mobileLogo = readFileSync(resolve('../app-movil/assets/images/logo.png'))
  expect(webLogo.equals(mobileLogo)).toBe(true)
})

it('la paleta web coincide con los colores del tema móvil', () => {
  const css = readFileSync(resolve('src/styles.css'), 'utf8')
  const theme = readFileSync(resolve('../app-movil/lib/theme/app_theme.dart'), 'utf8')
  for (const hex of ['F5C518', '1A1A1A', 'F7F7F4', 'E7E7E1', '6B6B65']) {
    expect(css.toUpperCase()).toContain(`#${hex}`)
    expect(theme.toUpperCase()).toContain(`0XFF${hex}`)
  }
})
