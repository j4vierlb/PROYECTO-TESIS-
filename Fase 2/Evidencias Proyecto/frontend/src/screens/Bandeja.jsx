// Bandeja de WhatsApp: conversaciones, chat y estado de entrega.
import React, { useEffect, useRef, useState } from 'react'
import { request } from '../api.js'
import { chileDateTime } from '../panel-utils.js'

// Estado de entrega que informa Twilio para cada mensaje enviado al cliente.
const DELIVERY = { accepted: ['🕓', 'En cola'], queued: ['🕓', 'En cola'], sending: ['🕓', 'Enviando'], sent: ['✓', 'Enviado'], delivered: ['✓✓', 'Entregado'], read: ['✓✓', 'Leído'], failed: ['⚠', 'No entregado'], undelivered: ['⚠', 'No entregado'], no_enviado: ['⚠', 'No enviado'] }

// Nombre que se muestra según quién envió cada mensaje de la conversación.
const SENDERS = { cliente: 'Cliente', agente_ia: 'Agente IA', sistema: 'Aviso automático', operador: 'Operador' }

function Delivery({ message }) { const [icon, label] = DELIVERY[message.estado_entrega] || []; if (!icon) return null; return <span className={`delivery ${message.estado_entrega}`} title={message.error_entrega || label}>{icon} {label}{message.error_entrega ? ` · ${message.error_entrega}` : ''}</span> }

function poll(load, delay, onError) {
  const controller = new AbortController()
  const { signal } = controller
  let timer

  async function refresh() {
    try {
      await load({ signal, cache: 'no-store' })
    } catch (error) {
      if (!signal.aborted) onError(error.message)
    }
    if (!signal.aborted) timer = setTimeout(refresh, delay)
  }

  refresh()
  return () => {
    controller.abort()
    clearTimeout(timer)
  }
}

// Bandeja de WhatsApp: lista de conversaciones a la izquierda y el chat a la
// derecha. El operador puede tomar la conversación (la IA deja de responder),
// escribir, y devolverla a la IA cuando termine.
export function Bandeja() {
  const [conversations, setConversations] = useState([])
  const [selected, setSelected] = useState(null)
  const [loadedDetail, setDetail] = useState(null)
  const [text, setText] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [action, setAction] = useState(null)
  const stopDetailPolling = useRef(null)
  const detail = loadedDetail?.id === selected ? loadedDetail : null

  // Pausa las lecturas al escribir y vuelve a consultar al terminar.
  useEffect(() => {
    if (action) return
    return poll(async options => {
      const list = await request('/panel/conversaciones', options)
      if (options.signal.aborted) return
      setConversations(list)
      setSelected(current => current ?? list[0]?.id ?? null)
    }, 10000, setError)
  }, [action])

  useEffect(() => {
    if (!selected || action) return
    const stop = poll(async options => {
      const updated = await request(`/panel/conversaciones/${selected}`, options)
      if (!options.signal.aborted && updated.id === selected) setDetail(updated)
    }, 5000, setError)
    stopDetailPolling.current = stop
    return stop
  }, [selected, action])

  // Envía un mensaje del operador al cliente. El cuadro de texto solo aparece si
  // la ventana de 24 horas de WhatsApp está abierta (detail.ventana_abierta).
  async function send(e) {
    e.preventDefault()
    if (!text.trim() || action) return
    stopDetailPolling.current?.()
    setAction('send')
    setError('')
    try {
      await request(`/panel/conversaciones/${selected}/mensajes`, { method: 'POST', body: JSON.stringify({ contenido: text }) })
      setText('')
    } catch (err) {
      setError(err.message)
    } finally {
      setAction(null)
    }
  }

  // Alterna entre 'atiende la IA' y 'atiende el operador' (campo atendida_por_humano).
  async function toggle() {
    if (!detail || action) return
    // Una lectura iniciada antes del PATCH puede traer el estado anterior.
    stopDetailPolling.current?.()
    setAction('control')
    setError('')
    try {
      const updated = await request(`/panel/conversaciones/${detail.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ atendida_por_humano: !detail.atendida_por_humano }),
      })
      setDetail(updated)
      setConversations(list => list.map(item => item.id === updated.id
        ? { ...item, atendida_por_humano: updated.atendida_por_humano }
        : item))
    } catch (err) {
      setError(err.message)
    } finally {
      setAction(null)
    }
  }

  // Dispara a mano el envío de los recordatorios de mañana (el sistema también
  // los manda solo, a la hora configurada).
  async function reminders() { setError(''); try { const r = await request('/panel/whatsapp/recordatorios', { method: 'POST' }); setNotice(`Recordatorios de mañana enviados: ${r.enviados}${r.no_enviados ? ` · no enviados: ${r.no_enviados}` : ''}`) } catch (err) { setError(err.message) } }
  return <>
    <header className="topbar">
      <div><p className="eyebrow">ATENCIÓN AL CLIENTE</p><h1>WhatsApp</h1><p className="muted">Revisa lo que conversa el agente IA y responde tú cuando haga falta.</p></div>
      <button className="secondary" onClick={reminders}>Enviar recordatorios de mañana</button>
    </header>
    {error && <div className="error banner" role="alert">{error}</div>}
    {notice && <div className="notice banner">{notice}</div>}
    <section className="inbox">
      <div className="inbox-list">
        {conversations.map(c => <button key={c.id} className={`inbox-item ${c.id === selected ? 'active' : ''}`} onClick={() => setSelected(c.id)}>
          <strong>{c.cliente.nombre}</strong><small>{c.cliente.telefono_whatsapp}</small>
          <span>{c.ultimo_emisor && `${SENDERS[c.ultimo_emisor] || c.ultimo_emisor}: `}{c.ultimo_mensaje}</span>
          <span className={`pill ${c.atendida_por_humano ? 'orange' : 'green'}`}>{c.atendida_por_humano ? 'Operador' : 'IA'}</span>
        </button>)}
        {!conversations.length && <div className="empty">Todavía no hay conversaciones de WhatsApp.</div>}
      </div>
      <div className="thread">
        {detail ? <>
          <div className="thread-head">
            <div><strong>{detail.cliente.nombre}</strong><small>{detail.cliente.telefono_whatsapp}</small></div>
            <button type="button" className={detail.atendida_por_humano ? 'primary' : 'secondary'} onClick={toggle} disabled={Boolean(action)}>
              {action === 'control' ? 'Guardando…' : detail.atendida_por_humano ? 'Devolver a la IA' : 'Tomar conversación'}
            </button>
          </div>
          <div className="messages" role="region" aria-label="Historial de mensajes" tabIndex={0}>
            {detail.mensajes.map(m => <div key={m.id} className={`bubble ${m.emisor}`}>
              <small>{SENDERS[m.emisor] || m.emisor} · {chileDateTime(m.created_at)}</small>
              <p>{m.contenido}</p><Delivery message={m} />
            </div>)}
          </div>
          {detail.ventana_abierta ? <form className="composer" onSubmit={send}>
            <textarea rows="2" aria-label="Mensaje para el cliente" placeholder={detail.atendida_por_humano ? 'Escribe tu respuesta' : 'Al enviar, la IA deja de responder en esta conversación'} value={text} onChange={e => setText(e.target.value)} />
            <button className="primary" disabled={Boolean(action) || !text.trim()}>Enviar</button>
          </form> : <div className="composer closed">El cliente no escribe hace más de 24 h: WhatsApp solo permite responder cuando vuelva a escribir.</div>}
        </> : <div className="empty">Selecciona una conversación.</div>}
      </div>
    </section>
  </>
}
