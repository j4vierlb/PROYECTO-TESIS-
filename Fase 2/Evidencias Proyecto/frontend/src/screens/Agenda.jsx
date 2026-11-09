// Pantalla de agenda: visitas del día, resumen y formulario de visita.
import React, { useMemo, useRef, useState } from 'react'
import { request } from '../api.js'
import { CroquisViewer } from '../CroquisViewer.jsx'
import { addDays, chileDate, chileTime, chileDateTimeInput, visitPayload } from '../panel-utils.js'
import { useResource } from '../hooks/useResource.js'
import { Feedback, Modal, Stat } from '../components/ui.jsx'

const statuses = {
  agendada: ['Agendada', 'gray'], en_curso: ['En curso', 'yellow'], completada: ['Completada', 'green'],
  cancelada: ['Cancelada', 'red'], reagendada: ['Reagendada', 'blue'],
}

// Pantalla de agenda: lista las visitas del día elegido, agrupadas por hora, con
// filtro por técnico. Permite crear, reagendar, cancelar y ver el croquis.
export function Agenda() {
  const [croquisVisit, setCroquisVisit] = useState(null)
  const [date, setDate] = useState(() => chileDate()), [operator, setOperator] = useState(''), [modal, setModal] = useState(null)
  const [error, setError] = useState(''), [success, setSuccess] = useState(''), [pending, setPending] = useState(null)
  // useRef funciona como un candado: evita que un doble clic envíe dos veces
  // la misma acción al servidor.
  const saving = useRef(false)
  // Pide a la API, todo junto: las visitas del día, los técnicos, las estadísticas
  // y los clientes.
  const resource = useResource([`/panel/visitas?fecha=${date}${operator && operator !== 'unassigned' ? `&operador_id=${operator}` : ''}`, '/panel/operadores', '/panel/stats', '/clientes'])
  const [visits = [], operators = [], stats = {}, clients = []] = resource.data
  // Agrupa las visitas por hora (hora de Chile) para dibujar la agenda. useMemo
  // evita recalcular si no cambió nada.
  const grouped = useMemo(() => visits.filter(v => operator !== 'unassigned' || !v.operador_id).reduce((acc, visit) => {
    const key = chileTime(visit.fecha_hora); (acc[key] ||= []).push(visit); return acc
  }, {}), [visits, operator])
  // Cambia el estado de una visita (PATCH). Si es 'reagendada', abre el
  // formulario para elegir la nueva fecha y hora.
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
    <section className="stats"><Stat label="Clientes registrados" value={stats.clientes ?? '—'} tone="green" icon="clientes" /><Stat label="Visitas para hoy" value={stats.visitas_hoy ?? '—'} tone="blue" icon="hoy" /><Stat label="Visitas pendientes" value={stats.pendientes ?? '—'} tone="orange" icon="pendientes" /></section>
    <section className="toolbar"><div className="date-picker"><button aria-label="Día anterior" onClick={() => setDate(addDays(date, -1))}>‹</button><input aria-label="Fecha de la agenda" type="date" required value={date} onChange={e => { if (e.target.value) setDate(e.target.value) }} /><button aria-label="Día siguiente" onClick={() => setDate(addDays(date, 1))}>›</button></div>
      <button className="secondary" onClick={() => setDate(chileDate())}>Hoy</button><select aria-label="Filtrar por operador" value={operator} onChange={e => setOperator(e.target.value)}><option value="">Todos los operadores</option><option value="unassigned">Sin asignar</option>{operators.map(o => <option key={o.id} value={o.id}>{o.nombre}</option>)}</select>
      <button className="secondary" disabled={resource.loading} onClick={resource.reload}>{resource.error ? 'Reintentar' : 'Actualizar'}</button>
    </section>
    <div className="agenda-layout">
    <section className="schedule" aria-label="Visitas del día" aria-busy={resource.loading}><div className="schedule-head"><span>Hora de Chile</span><span>Visitas agendadas</span></div>
      {resource.loading ? <div className="empty" role="status">Cargando agenda…</div> : resource.error ? <div className="empty">No se pudo cargar la agenda. Usa Reintentar.</div> : Object.keys(grouped).length === 0 ? <div className="empty">No hay visitas para este día y filtro.</div> : Object.entries(grouped).sort(([a], [b]) => a.localeCompare(b)).map(([hour, items]) => <div className="time-row" key={hour}><div className="time">{hour}<small>Hora de Chile</small></div><div className="cards">{items.map(v => <VisitCard key={v.id} visit={v} busy={pending !== null} onStatus={update} onCroquis={() => setCroquisVisit(v)} onEdit={() => { setSuccess(''); setModal({ visit: v }) }} />)}</div></div>)}
    </section>
    <DaySummary date={date} visits={visits} operators={operators} loading={resource.loading} />
    </div>
    {modal && <VisitModal date={date} visit={modal.visit} clients={clients} operators={operators} onClose={() => setModal(null)} onSaved={saved} />}
    {croquisVisit && <Modal title="Croquis de la visita" wide onClose={() => setCroquisVisit(null)}><CroquisViewer visit={croquisVisit} /></Modal>}
  </>
}

// Resumen lateral del día elegido: cuántas visitas hay y cómo se reparten entre los técnicos.
function DaySummary({ date, visits, operators, loading }) {
  const label = new Date(`${date}T12:00:00`).toLocaleDateString('es-CL', { weekday: 'long', day: 'numeric', month: 'long' })
  const loads = operators.map(o => ({ id: o.id, nombre: o.nombre, total: visits.filter(v => v.operador_id === o.id).length }))
  const unassigned = visits.filter(v => !v.operador_id).length
  const max = Math.max(1, ...loads.map(l => l.total), unassigned)
  return <section className="day-summary" aria-label="Resumen del día" aria-busy={loading}>
    <p className="eyebrow">RESUMEN DEL DÍA</p>
    <h2>{label}</h2>
    <p className="day-total"><strong>{loading ? '—' : visits.length}</strong><span>{visits.length === 1 ? 'visita en la fecha' : 'visitas en la fecha'}</span></p>
    <ul className="load-list">
      {loads.map(l => <li key={l.id}><div><span>{l.nombre}</span><strong>{loading ? '—' : l.total}</strong></div><i style={{ '--w': `${(l.total / max) * 100}%` }} aria-hidden="true" /></li>)}
      {unassigned > 0 && <li className="load-warn"><div><span>Por asignar</span><strong>{unassigned}</strong></div><i style={{ '--w': `${(unassigned / max) * 100}%` }} aria-hidden="true" /></li>}
    </ul>
    {!loading && operators.length === 0 && <p className="muted">Aún no hay técnicos registrados.</p>}
  </section>
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
