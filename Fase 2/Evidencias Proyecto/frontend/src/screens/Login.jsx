// Pantalla de inicio de sesión del panel.
import React, { useRef, useState } from 'react'
import { request } from '../api.js'
import { BrandLogo } from '../BrandLogo.jsx'
import { useLoginIdle } from '../useLoginIdle.js'
import { Feedback } from '../components/ui.jsx'

// Pantalla de inicio de sesión. Manda usuario y clave a POST /auth/login y guarda
// el token en localStorage. Después prueba GET /panel/operadores: si ese permiso
// falla (por ejemplo, un técnico intentando entrar al panel), borra el token.
export function Login({ onLogin, notice, onForgot, onHome }) {
  const [form, setForm] = useState({ usuario: '', clave: '' }), [error, setError] = useState(''), [busy, setBusy] = useState(false)
  const submitting = useRef(false)
  // Si el login se queda 5 minutos sin actividad, vuelve a la portada (hook
  // useLoginIdle). Se pausa mientras se está enviando el formulario (busy).
  useLoginIdle(onHome, busy)
  async function submit(event) {
    event.preventDefault()
    if (submitting.current) return
    submitting.current = true; setBusy(true); setError('')
    let sessionToken
    try {
      const data = await request('/auth/login', { method: 'POST', body: JSON.stringify({ ...form, usuario: form.usuario.trim() }) })
      if (!data.access_token) throw new Error('El servidor no entregó una sesión válida. Intenta nuevamente.')
      sessionToken = data.access_token
      localStorage.token = sessionToken
      // El login también admite técnicos; la API confirma el permiso del panel.
      await request('/panel/operadores')
      onLogin()
    } catch (err) {
      if (sessionToken && localStorage.token === sessionToken) localStorage.removeItem('token')
      setError(err.message)
    }
    finally { submitting.current = false; setBusy(false) }
  }
  return <main className="login-page"><div className="login-card"><BrandLogo className="login-logo" /><p className="eyebrow">CONTROL DE PLAGAS</p><h1>Bienvenido a Kill Bichos</h1><p className="muted">Gestiona clientes, visitas y la agenda de tu equipo.</p>
    {notice && <p role="status" className="info">{notice}</p>}
    <form onSubmit={submit} aria-busy={busy}><label>Correo<input required type="email" autoComplete="username" value={form.usuario} onChange={e => setForm({ ...form, usuario: e.target.value })} /></label><label>Contraseña<input required type="password" autoComplete="current-password" value={form.clave} onChange={e => setForm({ ...form, clave: e.target.value })} /></label><Feedback error={error} /><button className="primary full" disabled={busy}>{busy ? 'Ingresando…' : 'Ingresar al panel'}</button></form>
    <button type="button" className="secondary full" onClick={onForgot} disabled={busy}>Olvidé mi contraseña</button>
    <button type="button" className="secondary full" onClick={onHome} disabled={busy}>Volver a la página principal</button>
    <p className="login-idle-help">Tras 5 minutos sin actividad volverás a la página principal.</p>
  </div></main>
}
