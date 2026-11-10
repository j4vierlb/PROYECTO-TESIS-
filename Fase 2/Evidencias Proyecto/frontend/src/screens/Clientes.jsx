// Pantalla de clientes: búsqueda, creación, edición y borrado.
import React, { useRef, useState } from 'react'
import { request } from '../api.js'
import { clientLocation, hasClientLocation } from '../panel-utils.js'
import { useResource } from '../hooks/useResource.js'
import { Feedback, Modal } from '../components/ui.jsx'

// Pantalla de clientes: búsqueda, crear, editar y eliminar. Un cliente con
// visitas asociadas no se puede eliminar, para conservar el historial.
export function Clientes() {
  const resource = useResource(['/clientes'])
  const [clients = []] = resource.data
  const [query, setQuery] = useState(''), [modal, setModal] = useState(null), [deleting, setDeleting] = useState(null), [busy, setBusy] = useState(false)
  const [error, setError] = useState(''), [success, setSuccess] = useState('')
  const removing = useRef(false)
  // Búsqueda en el propio navegador: compara el texto escrito con el nombre, la
  // dirección y el teléfono, sin distinguir mayúsculas de minúsculas.
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
      {resource.loading ? <div className="empty" role="status">Cargando clientes…</div> : resource.error ? <div className="empty">No se pudo cargar el listado. Usa Reintentar.</div> : <>{filtered.map(c => <div className="client-row" key={c.id}><div className="client-name"><span className="client-initial" aria-hidden="true">{c.nombre.trim().charAt(0).toUpperCase()}</span><div><strong>{c.nombre}</strong><small>{c.direccion || 'Sin dirección registrada'}</small></div></div><span>{c.telefono_whatsapp}</span><span className={hasClientLocation(c) ? undefined : 'location-pending'}>{clientLocation(c)}</span><div className="row-actions"><button className="link-button" onClick={() => { setSuccess(''); setModal({ client: c }) }}>Editar</button><button className="link-button danger-text" onClick={() => { setError(''); setSuccess(''); setDeleting(c) }}>Eliminar</button></div></div>)}{!filtered.length && <div className="empty">{clients.length ? 'No hay clientes que coincidan con la búsqueda.' : 'Aún no hay clientes registrados.'}</div>}</>}
    </section>
    {modal && <ClientModal client={modal.client} onClose={() => setModal(null)} onSaved={saved => { setModal(null); setError(''); setSuccess(hasClientLocation(saved) ? 'Cliente guardado correctamente. Ubicación disponible para el croquis.' : 'Cliente guardado correctamente. Ubicación pendiente de confirmar: revisa calle, número y comuna, y vuelve a guardar para reintentar.'); resource.reload() }} />}
    {deleting && <Modal title="Eliminar cliente" busy={busy} onClose={() => { setDeleting(null); setError('') }} onSubmit={remove}><p>¿Eliminar a <strong>{deleting.nombre}</strong>? Esta acción no se puede deshacer.</p><p className="field-help">Si tiene visitas asociadas, el sistema impedirá su eliminación para conservar el historial.</p><Feedback error={error} /><div className="modal-actions"><button type="button" className="secondary" disabled={busy} onClick={() => { setDeleting(null); setError('') }}>Cancelar</button><button className="danger" disabled={busy}>{busy ? 'Eliminando…' : 'Confirmar eliminación'}</button></div></Modal>}
  </>
}

// Formulario para crear o editar un cliente. Pide nombre, teléfono y dirección;
// las coordenadas las calcula el backend a partir de la dirección (geocoding.py).
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
