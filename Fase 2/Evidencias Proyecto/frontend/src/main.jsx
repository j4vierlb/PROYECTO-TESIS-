// Punto de entrada del panel: carga los estilos y monta <App /> en la página.
import React from 'react'
import { createRoot } from 'react-dom/client'
import './styles.css'
import './panel.css'
import { App } from './App.jsx'

// Las pruebas importan App desde aquí.
export { App }

const root = document.getElementById('root')
if (root) {
  // Vite puede reevaluar este módulo al editar: reutilizar la raíz evita
  // montar dos árboles React sobre el mismo elemento durante desarrollo.
  const reactRoot = import.meta.hot?.data.reactRoot || createRoot(root)
  if (import.meta.hot) import.meta.hot.data.reactRoot = reactRoot
  reactRoot.render(<App />)
}
