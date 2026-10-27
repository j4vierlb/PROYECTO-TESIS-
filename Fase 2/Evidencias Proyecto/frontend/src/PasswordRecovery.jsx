import React, { useRef, useState } from 'react'
import { request } from './api.js'
import { BrandLogo } from './BrandLogo.jsx'

export function PasswordRecovery({ token, onCancel, onReset }) {
  const resetting = Boolean(token)
  const [email, setEmail] = useState(''), [password, setPassword] = useState(''), [confirmation, setConfirmation] = useState('')
  const [busy, setBusy] = useState(false), [error, setError] = useState(''), [success, setSuccess] = useState('')
  const submitting = useRef(false)

  async function submit(event) {
    event.preventDefault()
    if (submitting.current) return
    setError(''); setSuccess('')
    if (resetting && password !== confirmation) { setError('Las contraseñas no coinciden.'); return }
    if (resetting && new TextEncoder().encode(password).length > 72) { setError('La contraseña no debe superar 72 bytes UTF-8.'); return }
    submitting.current = true; setBusy(true)
    try {
      const data = await request(resetting ? '/auth/reset-password' : '/auth/forgot-password', {
        method: 'POST', cache: 'no-store',
        body: JSON.stringify(resetting ? { token, password } : { email: email.trim() }),
      })
      if (resetting) { setPassword(''); setConfirmation(''); onReset(data.message) }
      else setSuccess(data.message)
    } catch (err) {
      setError(err.status === 503 ? 'La recuperación por correo aún no está disponible. Contacta al soporte.' : err.message)
    }
    finally { submitting.current = false; setBusy(false) }
  }

  return <main className="login-page"><div className="login-card">
    <BrandLogo className="login-logo" /><p className="eyebrow">PANEL KILL BICHOS</p>
    <h1>{resetting ? 'Nueva contraseña' : 'Recuperar contraseña'}</h1>
    <p className="muted">{resetting ? 'Usa al menos 12 caracteres (máximo 72 bytes). Al guardar se cerrarán tus sesiones anteriores.' : 'Ingresa el correo de tu cuenta de administrador o coordinador. Si está activa, recibirás un enlace válido por 15 minutos.'}</p>
    <form onSubmit={submit} aria-busy={busy}>
      {resetting ? <>
        <label>Nueva contraseña<input required type="password" minLength={12} maxLength={72} autoComplete="new-password" value={password} onChange={event => setPassword(event.target.value)} disabled={busy} /></label>
        <label>Confirmar contraseña<input required type="password" minLength={12} maxLength={72} autoComplete="new-password" value={confirmation} onChange={event => setConfirmation(event.target.value)} disabled={busy} /></label>
      </> : <label>Correo<input required type="email" maxLength={150} autoComplete="email" value={email} onChange={event => setEmail(event.target.value)} disabled={busy} /></label>}
      {error && <div className="error" role="alert">{error}</div>}
      {success && <div className="success" role="status">{success}</div>}
      <button className="primary full" disabled={busy}>{busy ? 'Procesando…' : resetting ? 'Guardar contraseña' : 'Enviar enlace'}</button>
      <button type="button" className="secondary full" disabled={busy} onClick={onCancel}>Volver al inicio de sesión</button>
    </form>
  </div></main>
}
