import React from 'react'
import { fireEvent, render } from '@testing-library/react'
import { App } from '../../src/main.jsx'

// Las regresiones del panel recorren el mismo acceso público que el usuario.
export function renderAccess() {
  const result = render(<App />)
  fireEvent.click(result.getByRole('button', { name: 'Ingresar', exact: true }))
  return result
}
