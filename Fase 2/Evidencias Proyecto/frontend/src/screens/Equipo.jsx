// Pantalla de equipo: lista de técnicos y su formulario.
import React, { useRef, useState } from 'react'
import { request } from '../api.js'
import { useResource } from '../hooks/useResource.js'
import { Feedback, Modal } from '../components/ui.jsx'

// Gestión de técnicos: crear, editar, cambiar la clave y desactivar. No se elimina a nadie
// para conservar el historial de visitas (la API solo permite desactivar).
export function Equipo() {
  const resource = useResource(['/panel/operadores?incluir_inactivos=true'])
  const [team = []] = resource.data
  const [modal, setModal] = useState(null), [toggling, setToggling] = useState(null), [busy, setBusy] = useState(false)
  const [error, setError] = useState(''), [success, setSuccess] = useState('')
  const changing = useRef(false)
  const active = team.filter(t => t.activo).length
  async function setActive(event) {
    event.preventDefault()
    if (changing.current) return
    changing.current = true; setBusy(true); setError('')
    try {
      await request(`/panel/operadores/${toggling.tecnico.id}`, { method: 'PATCH', body: JSON.stringify({ activo: toggling.activar }) })
      setSuccess(toggling.activar ? 'Técnico reactivado.' : 'Técnico desactivado. Ya no puede iniciar sesión.')
      setToggling(null); resource.reload()
    } catch (err) { setError(err.message) }
    finally { changing.current = false; setBusy(false) }
  }
  return <><header className="topbar"><div><p className="eyebrow">GESTIÓN DE TÉCNICOS</p><h1>Equipo</h1><p className="muted">Crea las cuentas de tus técnicos y controla quién puede usar la app en terreno.</p></div><button className="primary" disabled={resource.loading || Boolean(resource.error)} onClick={() => { setSuccess(''); setModal({}) }}>＋ Nuevo técnico</button></header>
    <Feedback error={toggling ? resource.error : error || resource.error} success={success} />
    <p className="team-count" aria-live="polite">{resource.loading ? 'Cargando equipo…' : `${active} ${active === 1 ? 'técnico activo' : 'técnicos activos'} de ${team.length}`}</p>
    <section className="client-table team-table" aria-label="Técnicos" aria-busy={resource.loading}><div className="table-head"><span>Técnico</span><span>Teléfono</span><span>Estado</span><span>Acciones</span></div>
      {resource.loading ? <div className="empty" role="status">Cargando equipo…</div> : resource.error ? <div className="empty">No se pudo cargar el equipo. Usa Reintentar.</div> : <>{team.map(t => <div className={`client-row${t.activo ? '' : ' is-inactive'}`} key={t.id}><div className="client-name"><span className="client-initial" aria-hidden="true">{t.nombre.trim().charAt(0).toUpperCase()}</span><div><strong>{t.nombre}</strong><small>{t.email || 'Sin correo'}</small></div></div><span>{t.telefono || 'Sin teléfono'}</span><span><span className={`pill ${t.activo ? 'green' : 'gray'}`}>{t.activo ? 'Activo' : 'Inactivo'}</span></span><div className="row-actions"><button className="link-button" onClick={() => { setSuccess(''); setModal({ tecnico: t }) }}>Editar</button><button className={`link-button${t.activo ? ' danger-text' : ''}`} onClick={() => { setError(''); setSuccess(''); setToggling({ tecnico: t, activar: !t.activo }) }}>{t.activo ? 'Desactivar' : 'Reactivar'}</button></div></div>)}{!team.length && <div className="empty">Aún no hay técnicos. Crea el primero con «Nuevo técnico».</div>}</>}
    </section>
    {modal && <TecnicoModal tecnico={modal.tecnico} onClose={() => setModal(null)} onSaved={(saved, created) => { setModal(null); setError(''); setSuccess(created ? `Técnico creado. ${saved.nombre} ya puede iniciar sesión en la app con su correo y la clave inicial.` : 'Cambios guardados.'); resource.reload() }} />}
    {toggling && <Modal title={toggling.activar ? 'Reactivar técnico' : 'Desactivar técnico'} busy={busy} onClose={() => { setToggling(null); setError('') }} onSubmit={setActive}>
      <p>{toggling.activar ? <>¿Reactivar a <strong>{toggling.tecnico.nombre}</strong>? Podrá iniciar sesión de nuevo.</> : <>¿Desactivar a <strong>{toggling.tecnico.nombre}</strong>? Dejará de poder iniciar sesión y su sesión actual dejará de servir.</>}</p>
      {!toggling.activar && <p className="field-help">No se borra nada: el historial de sus visitas se conserva. Sus visitas pendientes siguen asignadas a él, así que reasígnalas desde la Agenda con «Editar visita».</p>}
      <Feedback error={error} /><div className="modal-actions"><button type="button" className="secondary" disabled={busy} onClick={() => { setToggling(null); setError('') }}>Cancelar</button><button className={toggling.activar ? 'primary' : 'danger'} disabled={busy}>{busy ? 'Guardando…' : toggling.activar ? 'Confirmar reactivación' : 'Confirmar desactivación'}</button></div>
    </Modal>}
  </>
}

function TecnicoModal({ tecnico, onClose, onSaved }) {
  const [form, setForm] = useState({ nombre: tecnico?.nombre ?? '', email: tecnico?.email ?? '', telefono: tecnico?.telefono ?? '', clave: '' })
  const [error, setError] = useState(''), [busy, setBusy] = useState(false), [showKey, setShowKey] = useState(false)
  const submitting = useRef(false)
  const field = key => ({ value: form[key], onChange: e => setForm({ ...form, [key]: e.target.value }) })
  async function save(event) {
    event.preventDefault()
    if (submitting.current) return
    submitting.current = true; setBusy(true); setError('')
    try {
      const nombre = form.nombre.trim(), telefono = form.telefono.trim(), clave = form.clave
      if (nombre.length < 2) throw new Error('Escribe el nombre del técnico.')
      if (telefono && telefono.length < 5) throw new Error('El teléfono debe tener al menos 5 caracteres.')
      if ((!tecnico || clave) && (clave.length < 12 || new TextEncoder().encode(clave).length > 72)) throw new Error('La clave debe tener entre 12 y 72 caracteres.')
      let saved
      if (tecnico) {
        const payload = {}
        if (nombre !== tecnico.nombre) payload.nombre = nombre
        if (telefono !== (tecnico.telefono ?? '')) payload.telefono = telefono || null
        if (clave) payload.clave = clave
        saved = Object.keys(payload).length ? await request(`/panel/operadores/${tecnico.id}`, { method: 'PATCH', body: JSON.stringify(payload) }) : tecnico
      } else {
        saved = await request('/panel/operadores', { method: 'POST', body: JSON.stringify({ nombre, email: form.email.trim(), telefono: telefono || null, clave }) })
      }
      onSaved(saved, !tecnico)
    } catch (err) { setError(err.message) }
    finally { submitting.current = false; setBusy(false) }
  }
  return <Modal title={tecnico ? 'Editar técnico' : 'Nuevo técnico'} busy={busy} onClose={onClose} onSubmit={save}>
    <fieldset disabled={busy}><label>Nombre<input required minLength="2" maxLength="150" autoComplete="off" {...field('nombre')} /></label>
      <label>Correo<input required type="email" maxLength="150" autoComplete="off" readOnly={Boolean(tecnico)} {...field('email')} /></label>
      {tecnico && <p className="field-help">El correo es el usuario con el que entra a la app y no se puede cambiar.</p>}
      <label>Teléfono (opcional)<input type="tel" minLength="5" maxLength="30" autoComplete="off" {...field('telefono')} /></label>
      <label>{tecnico ? 'Nueva clave (opcional)' : 'Clave inicial'}<span className="key-field"><input required={!tecnico} type={showKey ? 'text' : 'password'} minLength="12" maxLength="72" autoComplete="new-password" {...field('clave')} /><button type="button" className="link-button" onClick={() => setShowKey(!showKey)}>{showKey ? 'Ocultar' : 'Mostrar'}</button></span></label>
      <p className="field-help">{tecnico ? 'Si escribes una clave nueva, se cierra la sesión que el técnico tenga abierta en la app.' : 'Entre 12 y 72 caracteres. Entrégasela al técnico por un canal privado; él puede entrar con su correo y esta clave.'}</p>
    </fieldset><Feedback error={error} /><div className="modal-actions"><button type="button" className="secondary" disabled={busy} onClick={onClose}>Cancelar</button><button className="primary" disabled={busy}>{busy ? 'Guardando…' : tecnico ? 'Guardar cambios' : 'Crear técnico'}</button></div>
  </Modal>
}
