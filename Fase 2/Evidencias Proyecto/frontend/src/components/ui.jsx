// Piezas visuales reutilizables del panel: íconos, mensajes, ventana emergente y tarjeta de número.
import React, { useEffect, useRef } from 'react'

// Íconos de línea para el menú y los contadores (decorativos: el texto de al lado ya dice qué son).
const ICONS = {
  agenda: <><rect x="3.5" y="5" width="17" height="15.5" rx="3" /><path d="M8 3v4M16 3v4M3.5 10h17" /></>,
  clientes: <><circle cx="9" cy="8.5" r="3.5" /><path d="M2.5 20c.6-3.6 3.3-5.5 6.5-5.5s5.9 1.9 6.5 5.5" /><path d="M16 5.2a3.4 3.4 0 0 1 0 6.6M18 14.8c2 .6 3.3 2.3 3.6 5.2" /></>,
  whatsapp: <><path d="M21 11.5a9 9 0 0 1-9 9 10 10 0 0 1-4-.9L3 21l1.4-4.7a9 9 0 1 1 16.6-4.8Z" /><path d="M8 10h8M8 14h5" /></>,
  equipo: <><path d="M14.5 6.5a4 4 0 0 0-5 5L3.5 17.5a1.8 1.8 0 0 0 2.5 2.5l6-6a4 4 0 0 0 5-5l-2.4 2.4-2.2-.6-.6-2.2Z" /></>,
  hoy: <><circle cx="12" cy="12" r="8.5" /><path d="M12 7.5V12l3 2" /></>,
  pendientes: <><path d="M5 12.5 9.5 17 19 7.5" /></>,
  salir: <><path d="M10 4H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h4M15 8l4 4-4 4M19 12H9" /></>,
  inicio: <><path d="m3 10 9-7 9 7M5 9v11h14V9M9 20v-7h6v7" /></>,
}

export function Icon({ name }) { return <svg className="icon" aria-hidden="true" focusable="false" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">{ICONS[name]}</svg> }

// Muestra un mensaje de error (rojo) o de éxito (verde). role='alert' hace que
// los lectores de pantalla lo anuncien a quien no ve la pantalla.
export function Feedback({ error, success }) {
  return <>{error && <div className="error" role="alert">{error}</div>}{success && <div className="success" role="status">{success}</div>}</>
}

// Ventana emergente reutilizable (la usan agenda, clientes, equipo y croquis).
// Cuida la accesibilidad: el foco queda atrapado dentro con la tecla Tab, se
// cierra con Escape y, al cerrarse, devuelve el foco al elemento anterior.
export function Modal({ title, busy, onClose, onSubmit = event => event.preventDefault(), children, wide = false }) {
  const form = useRef(null)
  useEffect(() => {
    const previous = document.activeElement
    const overflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    const keepFocus = event => { if (!form.current?.contains(event.target)) form.current?.focus() }
    document.addEventListener('focusin', keepFocus)
    form.current.querySelector('input, select, textarea, button')?.focus()
    return () => { document.removeEventListener('focusin', keepFocus); document.body.style.overflow = overflow; previous?.focus() }
  }, [])
  function keys(event) {
    if (event.key === 'Escape' && !busy) { event.preventDefault(); onClose() }
    if (event.key !== 'Tab') return
    const controls = [...form.current.querySelectorAll('button, input, select, textarea, [tabindex="0"]')].filter(el => !el.disabled)
    const first = controls[0], last = controls.at(-1)
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus() }
    if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus() }
  }
  return <div className="overlay"><form ref={form} tabIndex={-1} className={`modal${wide ? ' modal-wide' : ''}`} role="dialog" aria-modal="true" aria-labelledby="modal-title" aria-busy={busy} onKeyDown={keys} onSubmit={onSubmit}>
    <div className="modal-head"><div><p className="eyebrow">PANEL OPERATIVO</p><h2 id="modal-title">{title}</h2></div><button type="button" className="icon-button" aria-label="Cerrar ventana" disabled={busy} onClick={onClose}>×</button></div>
    {children}
  </form></div>
}

// Tarjeta con un número (clientes registrados, visitas de hoy, pendientes).
export function Stat({ label, value, tone, icon }) { return <div className="stat"><span aria-hidden="true" className={`stat-icon ${tone}`}><Icon name={icon} /></span><div><small>{label}</small><strong>{value}</strong></div></div> }
