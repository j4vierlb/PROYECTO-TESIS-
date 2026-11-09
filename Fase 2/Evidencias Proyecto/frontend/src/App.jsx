// Componente raíz del panel: decide qué pantalla mostrar (portada, login, recuperación o panel).
import React, { useCallback, useEffect, useState } from 'react'
import { SESSION_EXPIRED } from './api.js'
import { PasswordRecovery } from './PasswordRecovery.jsx'
import { BrandLogo } from './BrandLogo.jsx'
import { PublicHome } from './PublicHome.jsx'
import { Icon } from './components/ui.jsx'
import { Login } from './screens/Login.jsx'
import { Agenda } from './screens/Agenda.jsx'
import { Bandeja } from './screens/Bandeja.jsx'
import { Equipo } from './screens/Equipo.jsx'
import { Clientes } from './screens/Clientes.jsx'

// Componente raíz del panel. Decide qué pantalla se muestra: recuperación de
// contraseña, portada, login, o el panel con su menú (Agenda, Clientes,
// WhatsApp y Equipo).
export function App() {
  // El enlace de recuperación trae el token en el fragmento de la URL
  // (#restablecer=...). Se lee al cargar y luego se borra de la barra de direcciones.
  const [resetToken, setResetToken] = useState(() => new URLSearchParams(window.location.hash.slice(1)).get('restablecer') || '')
  const [recovering, setRecovering] = useState(false)
  const [entered, setEntered] = useState(() => Boolean(localStorage.token))
  // Volver a la portada NO cierra la sesión: el token sigue guardado, así que
  // al entrar de nuevo al panel no hace falta escribir la clave otra vez.
  const goHome = useCallback(() => { setEntered(false); setNotice('') }, [])
  useEffect(() => {
    function consumeLink() {
      const token = new URLSearchParams(window.location.hash.slice(1)).get('restablecer')
      if (token) {
        setResetToken(token)
        window.history.replaceState(null, '', window.location.pathname + window.location.search)
      }
    }
    consumeLink()
    window.addEventListener('hashchange', consumeLink)
    return () => window.removeEventListener('hashchange', consumeLink)
  }, [])
  // Hay sesión si existe un token guardado en localStorage. Si ya venció, el
  // primer 401 del servidor lo borra (ver api.js).
  const [logged, setLogged] = useState(Boolean(localStorage.token)), [view, setView] = useState('agenda'), [notice, setNotice] = useState('')
  useEffect(() => {
    // Dos cosas cierran la sesión: el evento SESSION_EXPIRED (el backend respondió
    // 401) y el evento 'storage' (se cerró sesión en otra pestaña del navegador).
    const expired = () => { setLogged(false); setEntered(true); setNotice('Tu sesión venció. Inicia sesión nuevamente para continuar.') }
    const changed = event => { if (event.key === 'token' && !event.newValue) { setLogged(false); setEntered(true); setNotice('La sesión se cerró en otra pestaña.') } }
    window.addEventListener(SESSION_EXPIRED, expired)
    window.addEventListener('storage', changed)
    return () => { window.removeEventListener(SESSION_EXPIRED, expired); window.removeEventListener('storage', changed) }
  }, [])
  if (resetToken || recovering) return <PasswordRecovery token={resetToken} onCancel={() => {
    setResetToken(''); setRecovering(false); setLogged(false); setEntered(true); localStorage.removeItem('token')
  }} onReset={message => {
    setResetToken(''); setRecovering(false); setLogged(false); setEntered(true); localStorage.removeItem('token'); setNotice(message)
  }} />
  if (!entered) return <PublicHome onEnter={() => { setLogged(Boolean(localStorage.token)); setEntered(true) }} />
  if (!logged) return <Login notice={notice} onHome={goHome} onForgot={() => setRecovering(true)} onLogin={() => { setNotice(''); setLogged(true) }} />
  return <div className="app-shell"><aside><div className="logo"><BrandLogo /><div><strong>Kill Bichos</strong><small>Panel operativo</small></div></div>
    <nav aria-label="Navegación principal"><button className={view === 'agenda' ? 'active' : ''} aria-current={view === 'agenda' ? 'page' : undefined} onClick={() => setView('agenda')}><Icon name="agenda" /><span>Agenda</span></button><button className={view === 'clientes' ? 'active' : ''} aria-current={view === 'clientes' ? 'page' : undefined} onClick={() => setView('clientes')}><Icon name="clientes" /><span>Clientes</span></button><button className={view === 'whatsapp' ? 'active' : ''} aria-current={view === 'whatsapp' ? 'page' : undefined} onClick={() => setView('whatsapp')}><Icon name="whatsapp" /><span>WhatsApp</span></button><button className={view === 'equipo' ? 'active' : ''} aria-current={view === 'equipo' ? 'page' : undefined} onClick={() => setView('equipo')}><Icon name="equipo" /><span>Equipo</span></button></nav>
    <div className="sidebar-bottom"><div className="user-chip"><div className="avatar">KB</div><div><strong>Cuenta del panel</strong><small>Gestión administrativa</small></div></div></div>
    <div className="panel-actions"><button type="button" className="home-link" aria-label="Volver a la página principal" title="Volver a la página principal" onClick={goHome}><Icon name="inicio" /><span>Página principal</span></button><button className="logout" aria-label="Cerrar sesión" title="Cerrar sesión" onClick={() => { localStorage.removeItem('token'); setNotice(''); setLogged(false); setEntered(true) }}><Icon name="salir" /><span>Cerrar sesión</span></button></div>
  </aside><main className="content">{{ agenda: <Agenda />, clientes: <Clientes />, whatsapp: <Bandeja />, equipo: <Equipo /> }[view]}</main></div>
}
