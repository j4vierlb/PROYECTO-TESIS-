import React from 'react'
import { fireEvent, render } from '@testing-library/react'
import { App } from '../../src/main.jsx'

// Sin sesión se entra por la portada; con sesión la app abre el panel directamente.
export function renderAccess() {
  const result = render(<App />)
  const entry = result.queryByRole('button', { name: 'Ingresar', exact: true })
  if (entry) fireEvent.click(entry)
  return result
}
