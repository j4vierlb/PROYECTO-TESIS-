import React, { useEffect, useMemo, useRef, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './styles.css'
import { request, SESSION_EXPIRED } from './api.js'
import { CroquisViewer } from './CroquisViewer.jsx'
import { PasswordRecovery } from './PasswordRecovery.jsx'
import { BrandLogo } from './BrandLogo.jsx'
import { PublicHome } from './PublicHome.jsx'
import { addDays, chileDate, chileDateTime, chileTime, chileDateTimeInput, clientLocation, hasClientLocation, visitPayload } from './panel-utils.js'

const statuses = {
  agendada: ['Agendada', 'gray'], en_curso: ['En curso', 'yellow'], completada: ['Completada', 'green'],
  cancelada: ['Cancelada', 'red'], reagendada: ['Reagendada', 'blue'],
}

// Cancela cargas antiguas al navegar: una respuesta lenta no reemplaza el día actual.
function useResource(paths) {
  const key = JSON.stringify(paths)
  const [data, setData] = useState([]), [loading, setLoading] = useState(true)
  const [error, setError] = useState(''), [revision, setRevision] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    setLoading(true); setError('')
    Promise.all(JSON.parse(key).map(path => request(path, { signal: controller.signal })))
      .then(values => { if (!controller.signal.aborted) setData(values) })
      .catch(err => { if (!controller.signal.aborted) setError(err.message) })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [key, revision])
  return { data, loading, error, reload: () => setRevision(value => value + 1) }
}

function Feedback({ error, success }) {
  return <>{error && <div className="error" role="alert">{error}</div>}{success && <div className="success" role="status">{success}</div>}</>
}

function Modal({ title, busy, onClose, onSubmit = event => event.preventDefault(), children, wide = false }) {
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

function Login({ onLogin, notice, onForgot }) {
  const [form, setForm] = useState({ usuario: '', clave: '' }), [error, setError] = useState(''), [busy, setBusy] = useState(false)
  const submitting = useRef(false)
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
  </div></main>
}

export function App() {
  const [resetToken, setResetToken] = useState(() => new URLSearchParams(window.location.hash.slice(1)).get('restablecer') || '')
  const [recovering, setRecovering] = useState(false)
  const [entered, setEntered] = useState(false)
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
  const [logged, setLogged] = useState(Boolean(localStorage.token)), [view, setView] = useState('agenda'), [notice, setNotice] = useState('')
  useEffect(() => {
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
  if (!entered) return <PublicHome onEnter={() => setEntered(true)} />
  if (!logged) return <Login notice={notice} onForgot={() => setRecovering(true)} onLogin={() => { setNotice(''); setLogged(true) }} />
  return <div className="app-shell"><aside><div className="logo"><BrandLogo /><div><strong>Kill Bichos</strong><small>Panel operativo</small></div></div>
    <nav aria-label="Navegación principal"><button className={view === 'agenda' ? 'active' : ''} aria-current={view === 'agenda' ? 'page' : undefined} onClick={() => setView('agenda')}>▦ <span>Agenda</span></button><button className={view === 'clientes' ? 'active' : ''} aria-current={view === 'clientes' ? 'page' : undefined} onClick={() => setView('clientes')}>♧ <span>Clientes</span></button><button className={view === 'whatsapp' ? 'active' : ''} aria-current={view === 'whatsapp' ? 'page' : undefined} onClick={() => setView('whatsapp')}>✉ <span>WhatsApp</span></button></nav>
    <div className="sidebar-bottom"><div className="user-chip"><div className="avatar">KB</div><div><strong>Cuenta del panel</strong><small>Gestión administrativa</small></div></div></div>
    <button className="logout" onClick={() => { localStorage.removeItem('token'); setNotice(''); setLogged(false); setEntered(true) }}>Cerrar sesión</button>
  </aside><main className="content">{{ agenda: <Agenda />, clientes: <Clientes />, whatsapp: <Bandeja /> }[view]}</main></div>
}

function Stat({ label, value, tone }) { return <div className="stat"><span aria-hidden="true" className={`stat-icon ${tone}`}>●</span><div><small>{label}</small><strong>{value}</strong></div></div> }

function Agenda() {
  const [croquisVisit, setCroquisVisit] = useState(null)
  const [date, setDate] = useState(() => chileDate()), [operator, setOperator] = useState(''), [modal, setModal] = useState(null)
  const [error, setError] = useState(''), [success, setSuccess] = useState(''), [pending, setPending] = useState(null)
  const saving = useRef(false)
  const resource = useResource([`/panel/visitas?fecha=${date}${operator && operator !== 'unassigned' ? `&operador_id=${operator}` : ''}`, '/panel/operadores', '/panel/stats', '/clientes'])
  const [visits = [], operators = [], stats = {}, clients = []] = resource.data
  const grouped = useMemo(() => visits.filter(v => operator !== 'unassigned' || !v.operador_id).reduce((acc, visit) => {
    const key = chileTime(visit.fecha_hora); (acc[key] ||= []).push(visit); return acc
  }, {}), [visits, operator])
  async function update(visit, estado) {
    if (estado === 'reagendada') { setModal({ visit }); return }
    if (saving.current) return
    saving.current = true; setPending(visit.id); setError(''); setSuccess('')
    try {
      await request(`/panel/visitas/${visit.id}`, { method: 'PATCH', body: JSON.stringify({ estado }) })
      setSuccess('Estado de la visita actualizado.'); resource.reload()
    } catch (err) { setError(err.message) }
    finally { saving.current = false; setPending(null) }
  }
  function saved(result) {
    const editing = Boolean(modal.visit)
    if (result.fecha_hora) setDate(chileDate(new Date(result.fecha_hora)))
    if (operator && (operator === 'unassigned' ? result.operador_id : result.operador_id !== operator)) setOperator('')
    setModal(null); setError(''); setSuccess(editing ? 'Visita actualizada. Se muestra su fecha guardada.' : 'Visita agendada correctamente.'); resource.reload()
  }
  return <><header className="topbar"><div><p className="eyebrow">OPERACIÓN DIARIA</p><h1>Agenda</h1><p className="muted">Coordina las visitas y mantén a tu equipo en movimiento.</p></div><button className="primary" disabled={resource.loading || Boolean(resource.error)} onClick={() => { setSuccess(''); setModal({}) }}>＋ Nueva visita</button></header>
    <Feedback error={error || resource.error} success={success} />
    <section className="stats"><Stat label="Clientes registrados" value={stats.clientes ?? '—'} tone="green" /><Stat label="Visitas para hoy" value={stats.visitas_hoy ?? '—'} tone="blue" /><Stat label="Visitas pendientes" value={stats.pendientes ?? '—'} tone="orange" /></section>
    <section className="toolbar"><div className="date-picker"><button aria-label="Día anterior" onClick={() => setDate(addDays(date, -1))}>‹</button><input aria-label="Fecha de la agenda" type="date" required value={date} onChange={e => { if (e.target.value) setDate(e.target.value) }} /><button aria-label="Día siguiente" onClick={() => setDate(addDays(date, 1))}>›</button></div>
      <button className="secondary" onClick={() => setDate(chileDate())}>Hoy</button><select aria-label="Filtrar por operador" value={operator} onChange={e => setOperator(e.target.value)}><option value="">Todos los operadores</option><option value="unassigned">Sin asignar</option>{operators.map(o => <option key={o.id} value={o.id}>{o.nombre}</option>)}</select>
      <button className="secondary" disabled={resource.loading} onClick={resource.reload}>{resource.error ? 'Reintentar' : 'Actualizar'}</button>
    </section>
    <section className="schedule" aria-label="Visitas del día" aria-busy={resource.loading}><div className="schedule-head"><span>Hora de Chile</span><span>Visitas agendadas</span></div>
      {resource.loading ? <div className="empty" role="status">Cargando agenda…</div> : resource.error ? <div className="empty">No se pudo cargar la agenda. Usa Reintentar.</div> : Object.keys(grouped).length === 0 ? <div className="empty">No hay visitas para este día y filtro.</div> : Object.entries(grouped).sort(([a], [b]) => a.localeCompare(b)).map(([hour, items]) => <div className="time-row" key={hour}><div className="time">{hour}<small>Hora de Chile</small></div><div className="cards">{items.map(v => <VisitCard key={v.id} visit={v} busy={pending !== null} onStatus={update} onCroquis={() => setCroquisVisit(v)} onEdit={() => { setSuccess(''); setModal({ visit: v }) }} />)}</div></div>)}
    </section>
    {modal && <VisitModal date={date} visit={modal.visit} clients={clients} operators={operators} onClose={() => setModal(null)} onSaved={saved} />}
    {croquisVisit && <Modal title="Croquis de la visita" wide onClose={() => setCroquisVisit(null)}><CroquisViewer visit={croquisVisit} /></Modal>}
  </>
}

function VisitCard({ visit, busy, onStatus, onEdit, onCroquis }) {
  const status = statuses[visit.estado] || [visit.estado, 'gray']
  return <article className="visit-card"><div className="visit-main"><div className="visit-dot" /><div><strong>{visit.cliente.nombre}</strong><p>{visit.cliente.direccion || 'Sin dirección registrada'}</p><p className="small">{visit.cliente.telefono_whatsapp}</p>{visit.notas && <p className="visit-notes">{visit.notas}</p>}<p className="small">Origen: {visit.origen_agendamiento === 'whatsapp_ia' ? 'WhatsApp' : 'Manual'}</p></div></div>
    <div className="visit-meta"><span className={`pill ${status[1]}`}>{status[0]}</span><span className="operator">{visit.operador?.nombre || 'Sin asignar'}</span>
      <select disabled={busy} value={visit.estado} onChange={e => onStatus(visit, e.target.value)} aria-label={`Estado de visita de ${visit.cliente.nombre}`}>{Object.entries(statuses).map(([key, value]) => <option key={key} value={key}>{value[0]}</option>)}</select>
      <button className="link-button" disabled={busy} onClick={onEdit}>Editar visita</button>
      <button className="secondary" onClick={onCroquis} aria-label={`Ver croquis de ${visit.cliente.nombre}`}>Ver croquis</button>
    </div>
  </article>
}

function VisitModal({ date, visit, clients, operators, onClose, onSaved }) {
  const [form, setForm] = useState(() => ({ cliente_id: visit?.cliente.id || clients[0]?.id || '', operador_id: visit?.operador_id || '', fecha_hora: visit ? chileDateTimeInput(visit.fecha_hora) : `${date}T10:00`, notas: visit?.notas || '' }))
  const [error, setError] = useState(''), [busy, setBusy] = useState(false)
  const submitting = useRef(false)
  const closed = visit && ['completada', 'cancelada'].includes(visit.estado)
  const missingOperator = visit?.operador && !operators.some(o => o.id === visit.operador_id)
  const field = key => ({ value: form[key], onChange: e => setForm({ ...form, [key]: e.target.value }) })
  async function save(event) {
    event.preventDefault()
    if (submitting.current) return
    submitting.current = true; setBusy(true); setError('')
    try {
      let payload
      if (visit) {
        payload = { notas: form.notas || null }
        if (form.operador_id !== (visit.operador_id || '')) payload.operador_id = form.operador_id || null
        if (form.fecha_hora !== chileDateTimeInput(visit.fecha_hora)) payload.fecha_hora = visitPayload(form).fecha_hora
      } else {
        const { notas, ...base } = visitPayload(form)
        payload = notas ? { ...base, notas } : base
      }
      const result = await request(visit ? `/panel/visitas/${visit.id}` : '/panel/visitas', { method: visit ? 'PATCH' : 'POST', body: JSON.stringify(payload) })
      onSaved(result)
    } catch (err) { setError(err.message) }
    finally { submitting.current = false; setBusy(false) }
  }
  return <Modal title={visit ? 'Editar visita' : 'Nueva visita'} busy={busy} onClose={onClose} onSubmit={save}>
    {visit ? <p className="muted">Cliente: {visit.cliente.nombre}</p> : <label>Cliente<select required disabled={busy} {...field('cliente_id')}><option value="" disabled>Selecciona un cliente</option>{clients.map(c => <option key={c.id} value={c.id}>{c.nombre}</option>)}</select></label>}
    {!visit && !clients.length && <p className="info">Primero registra un cliente en la sección Clientes.</p>}
    {closed && <p className="info">Para cambiar la fecha u operador, reactiva la visita desde su estado en la agenda. Puedes editar sus notas.</p>}
    <label>Operador<select disabled={closed || busy} {...field('operador_id')}><option value="">Sin asignar</option>{missingOperator && <option value={visit.operador_id}>{visit.operador.nombre} (inactivo)</option>}{operators.map(o => <option key={o.id} value={o.id}>{o.nombre}</option>)}</select></label>
    <label>Fecha y hora (Chile)<input required disabled={closed || busy} type="datetime-local" {...field('fecha_hora')} /></label>
    <p className="field-help">Se aplican los días y horas de atención configurados. Cada operador necesita al menos una hora entre visitas.{visit && ' Cambiar la fecha marcará la visita como Reagendada y se le avisará al cliente por WhatsApp.'}</p>
    <label>Notas<textarea rows="3" disabled={busy} {...field('notas')} /></label><Feedback error={error} />
    <div className="modal-actions"><button type="button" className="secondary" disabled={busy} onClick={onClose}>Cancelar</button><button className="primary" disabled={busy || (!visit && !clients.length)}>{busy ? 'Guardando…' : visit ? 'Guardar cambios' : 'Agendar visita'}</button></div>
  </Modal>
}

// Estado de entrega que informa Twilio para cada mensaje enviado al cliente.
const DELIVERY = { accepted: ['🕓', 'En cola'], queued: ['🕓', 'En cola'], sending: ['🕓', 'Enviando'], sent: ['✓', 'Enviado'], delivered: ['✓✓', 'Entregado'], read: ['✓✓', 'Leído'], failed: ['⚠', 'No entregado'], undelivered: ['⚠', 'No entregado'], no_enviado: ['⚠', 'No enviado'] }
const SENDERS = { cliente: 'Cliente', agente_ia: 'Agente IA', sistema: 'Aviso automático', operador: 'Operador' }

function Delivery({ message }) { const [icon, label] = DELIVERY[message.estado_entrega] || []; if (!icon) return null; return <span className={`delivery ${message.estado_entrega}`} title={message.error_entrega || label}>{icon} {label}{message.error_entrega ? ` · ${message.error_entrega}` : ''}</span> }

function Bandeja() {
  const [conversations, setConversations] = useState([]), [selected, setSelected] = useState(null), [detail, setDetail] = useState(null), [text, setText] = useState(''), [error, setError] = useState(''), [notice, setNotice] = useState(''), [sending, setSending] = useState(false)
  const loadList = () => request('/panel/conversaciones').then(list => { setConversations(list); setSelected(current => current ?? list[0]?.id ?? null) }).catch(e => setError(e.message))
  const loadDetail = id => id ? request(`/panel/conversaciones/${id}`).then(d => setDetail(d.id === id ? d : null)).catch(e => setError(e.message)) : Promise.resolve()
  // Se actualiza solo: los mensajes nuevos y los estados de entrega llegan por el webhook de Twilio.
  useEffect(() => { loadList(); const timer = setInterval(loadList, 10000); return () => clearInterval(timer) }, [])
  useEffect(() => { setDetail(null); loadDetail(selected); const timer = setInterval(() => loadDetail(selected), 5000); return () => clearInterval(timer) }, [selected])
  async function send(e) { e.preventDefault(); if (!text.trim()) return; setSending(true); setError(''); try { await request(`/panel/conversaciones/${selected}/mensajes`, { method: 'POST', body: JSON.stringify({ contenido: text }) }); setText(''); await Promise.all([loadDetail(selected), loadList()]) } catch (err) { setError(err.message) } finally { setSending(false) } }
  async function toggle() { try { setDetail(await request(`/panel/conversaciones/${selected}`, { method: 'PATCH', body: JSON.stringify({ atendida_por_humano: !detail.atendida_por_humano }) })); loadList() } catch (err) { setError(err.message) } }
  async function reminders() { setError(''); try { const r = await request('/panel/whatsapp/recordatorios', { method: 'POST' }); setNotice(`Recordatorios de mañana enviados: ${r.enviados}${r.no_enviados ? ` · no enviados: ${r.no_enviados}` : ''}`) } catch (err) { setError(err.message) } }
  return <><header className="topbar"><div><p className="eyebrow">ATENCIÓN AL CLIENTE</p><h1>WhatsApp</h1><p className="muted">Revisa lo que conversa el agente IA y responde tú cuando haga falta.</p></div><button className="secondary" onClick={reminders}>Enviar recordatorios de mañana</button></header>{error && <div className="error banner">{error}</div>}{notice && <div className="notice banner">{notice}</div>}<section className="inbox"><div className="inbox-list">{conversations.map(c => <button key={c.id} className={`inbox-item ${c.id === selected ? 'active' : ''}`} onClick={() => setSelected(c.id)}><strong>{c.cliente.nombre}</strong><small>{c.cliente.telefono_whatsapp}</small><span>{c.ultimo_emisor && `${SENDERS[c.ultimo_emisor] || c.ultimo_emisor}: `}{c.ultimo_mensaje}</span><span className={`pill ${c.atendida_por_humano ? 'orange' : 'green'}`}>{c.atendida_por_humano ? 'Operador' : 'IA'}</span></button>)}{!conversations.length && <div className="empty">Todavía no hay conversaciones de WhatsApp.</div>}</div><div className="thread">{detail ? <><div className="thread-head"><div><strong>{detail.cliente.nombre}</strong><small>{detail.cliente.telefono_whatsapp}</small></div><button className={detail.atendida_por_humano ? 'primary' : 'secondary'} onClick={toggle}>{detail.atendida_por_humano ? 'Devolver a la IA' : 'Tomar conversación'}</button></div><div className="messages">{detail.mensajes.map(m => <div key={m.id} className={`bubble ${m.emisor}`}><small>{SENDERS[m.emisor] || m.emisor} · {chileDateTime(m.created_at)}</small><p>{m.contenido}</p><Delivery message={m} /></div>)}</div>{detail.ventana_abierta ? <form className="composer" onSubmit={send}><textarea rows="2" aria-label="Mensaje para el cliente" placeholder={detail.atendida_por_humano ? 'Escribe tu respuesta' : 'Al enviar, la IA deja de responder en esta conversación'} value={text} onChange={e => setText(e.target.value)} /><button className="primary" disabled={sending || !text.trim()}>Enviar</button></form> : <div className="composer closed">El cliente no escribe hace más de 24 h: WhatsApp solo permite responder cuando vuelva a escribir.</div>}</> : <div className="empty">Selecciona una conversación.</div>}</div></section></>
}

function Clientes() {
  const resource = useResource(['/clientes'])
  const [clients = []] = resource.data
  const [query, setQuery] = useState(''), [modal, setModal] = useState(null), [deleting, setDeleting] = useState(null), [busy, setBusy] = useState(false)
  const [error, setError] = useState(''), [success, setSuccess] = useState('')
  const removing = useRef(false)
  const filtered = clients.filter(c => `${c.nombre} ${c.direccion || ''} ${c.telefono_whatsapp}`.toLocaleLowerCase('es').includes(query.trim().toLocaleLowerCase('es')))
  async function remove(event) {
    event.preventDefault()
    if (removing.current) return
    removing.current = true; setBusy(true); setError('')
    try { await request(`/clientes/${deleting.id}`, { method: 'DELETE' }); setDeleting(null); setSuccess('Cliente eliminado.'); resource.reload() }
    catch (err) { setError(err.message) }
    finally { removing.current = false; setBusy(false) }
  }
  return <><header className="topbar"><div><p className="eyebrow">GESTIÓN DE CLIENTES</p><h1>Clientes</h1><p className="muted">Administra la información de contacto y ubicación de tus clientes.</p></div><button className="primary" onClick={() => { setSuccess(''); setModal({}) }}>＋ Nuevo cliente</button></header>
    <Feedback error={deleting ? resource.error : error || resource.error} success={success} />
    <div className="list-toolbar"><input className="search" aria-label="Buscar clientes" placeholder="Buscar por nombre, dirección o teléfono" value={query} onChange={e => setQuery(e.target.value)} /><button className="secondary" disabled={resource.loading} onClick={resource.reload}>{resource.error ? 'Reintentar' : 'Actualizar'}</button></div>
    <section className="client-table" aria-label="Clientes registrados" aria-busy={resource.loading}><div className="table-head"><span>Cliente</span><span>Contacto</span><span>Ubicación</span><span>Acciones</span></div>
      {resource.loading ? <div className="empty" role="status">Cargando clientes…</div> : resource.error ? <div className="empty">No se pudo cargar el listado. Usa Reintentar.</div> : <>{filtered.map(c => <div className="client-row" key={c.id}><div><strong>{c.nombre}</strong><small>{c.direccion || 'Sin dirección registrada'}</small></div><span>{c.telefono_whatsapp}</span><span className={hasClientLocation(c) ? undefined : 'location-pending'}>{clientLocation(c)}</span><div className="row-actions"><button className="link-button" onClick={() => { setSuccess(''); setModal({ client: c }) }}>Editar</button><button className="link-button danger-text" onClick={() => { setError(''); setSuccess(''); setDeleting(c) }}>Eliminar</button></div></div>)}{!filtered.length && <div className="empty">{clients.length ? 'No hay clientes que coincidan con la búsqueda.' : 'Aún no hay clientes registrados.'}</div>}</>}
    </section>
    {modal && <ClientModal client={modal.client} onClose={() => setModal(null)} onSaved={saved => { setModal(null); setError(''); setSuccess(hasClientLocation(saved) ? 'Cliente guardado correctamente. Ubicación disponible para el croquis.' : 'Cliente guardado correctamente. Ubicación pendiente de confirmar: revisa calle, número y comuna, y vuelve a guardar para reintentar.'); resource.reload() }} />}
    {deleting && <Modal title="Eliminar cliente" busy={busy} onClose={() => { setDeleting(null); setError('') }} onSubmit={remove}><p>¿Eliminar a <strong>{deleting.nombre}</strong>? Esta acción no se puede deshacer.</p><p className="field-help">Si tiene visitas asociadas, el sistema impedirá su eliminación para conservar el historial.</p><Feedback error={error} /><div className="modal-actions"><button type="button" className="secondary" disabled={busy} onClick={() => { setDeleting(null); setError('') }}>Cancelar</button><button className="danger" disabled={busy}>{busy ? 'Eliminando…' : 'Confirmar eliminación'}</button></div></Modal>}
  </>
}

function ClientModal({ client, onClose, onSaved }) {
  const [form, setForm] = useState({ nombre: client?.nombre ?? '', telefono_whatsapp: client?.telefono_whatsapp ?? '', direccion: client?.direccion ?? '' })
  const [error, setError] = useState(''), [busy, setBusy] = useState(false)
  const submitting = useRef(false)
  const field = key => ({ value: form[key], onChange: e => setForm({ ...form, [key]: e.target.value }) })
  async function save(event) {
    event.preventDefault()
    if (submitting.current) return
    submitting.current = true; setBusy(true); setError('')
    try {
      // No reenviar coordenadas anteriores al cambiar de dirección.
      const payload = { nombre: form.nombre.trim(), telefono_whatsapp: form.telefono_whatsapp.trim(), direccion: form.direccion.trim() || null }
      if (payload.nombre.length < 2 || payload.telefono_whatsapp.length < 5 || (!client && !payload.direccion)) throw new Error('Completa nombre, teléfono y dirección válidos.')
      const saved = await request(client ? `/clientes/${client.id}` : '/clientes', { method: client ? 'PATCH' : 'POST', body: JSON.stringify(payload) })
      onSaved(saved)
    } catch (err) { setError(err.message) }
    finally { submitting.current = false; setBusy(false) }
  }
  return <Modal title={client ? 'Editar cliente' : 'Nuevo cliente'} busy={busy} onClose={onClose} onSubmit={save}>
    <fieldset disabled={busy}><label>Nombre<input required minLength="2" maxLength="150" autoComplete="name" {...field('nombre')} /></label><label>Teléfono WhatsApp<input required type="tel" minLength="5" maxLength="30" autoComplete="tel" {...field('telefono_whatsapp')} /></label><label>Dirección<input required={!client} autoComplete="street-address" {...field('direccion')} /></label>
      <p className="field-help">Ingresa calle, número y comuna o ciudad de Chile. Buscaremos la ubicación automáticamente con Google Maps al guardar. La comuna o ciudad debe coincidir con la dirección encontrada. Si no se puede confirmar, el cliente se guardará con ubicación pendiente; corrige la dirección y vuelve a guardar para reintentar.</p>
    </fieldset><Feedback error={error} /><div className="modal-actions"><button type="button" className="secondary" disabled={busy} onClick={onClose}>Cancelar</button><button className="primary" disabled={busy}>{busy ? 'Guardando…' : 'Guardar cliente'}</button></div>
  </Modal>
}

const root = document.getElementById('root')
if (root) {
  // Vite puede reevaluar este módulo al editar: reutilizar la raíz evita
  // montar dos árboles React sobre el mismo elemento durante desarrollo.
  const reactRoot = import.meta.hot?.data.reactRoot || createRoot(root)
  if (import.meta.hot) import.meta.hot.data.reactRoot = reactRoot
  reactRoot.render(<App />)
}
