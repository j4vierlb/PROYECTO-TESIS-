// Bandeja de WhatsApp: conversaciones, chat y estado de entrega.
import React, { useEffect, useState } from 'react'
import { request } from '../api.js'
import { chileDateTime } from '../panel-utils.js'

// Estado de entrega que informa Twilio para cada mensaje enviado al cliente.
const DELIVERY = { accepted: ['🕓', 'En cola'], queued: ['🕓', 'En cola'], sending: ['🕓', 'Enviando'], sent: ['✓', 'Enviado'], delivered: ['✓✓', 'Entregado'], read: ['✓✓', 'Leído'], failed: ['⚠', 'No entregado'], undelivered: ['⚠', 'No entregado'], no_enviado: ['⚠', 'No enviado'] }

// Nombre que se muestra según quién envió cada mensaje de la conversación.
const SENDERS = { cliente: 'Cliente', agente_ia: 'Agente IA', sistema: 'Aviso automático', operador: 'Operador' }

function Delivery({ message }) { const [icon, label] = DELIVERY[message.estado_entrega] || []; if (!icon) return null; return <span className={`delivery ${message.estado_entrega}`} title={message.error_entrega || label}>{icon} {label}{message.error_entrega ? ` · ${message.error_entrega}` : ''}</span> }

// Bandeja de WhatsApp: lista de conversaciones a la izquierda y el chat a la
// derecha. El operador puede tomar la conversación (la IA deja de responder),
// escribir, y devolverla a la IA cuando termine.
export function Bandeja() {
  const [conversations, setConversations] = useState([]), [selected, setSelected] = useState(null), [detail, setDetail] = useState(null), [text, setText] = useState(''), [error, setError] = useState(''), [notice, setNotice] = useState(''), [sending, setSending] = useState(false)
  const loadList = () => request('/panel/conversaciones').then(list => { setConversations(list); setSelected(current => current ?? list[0]?.id ?? null) }).catch(e => setError(e.message))
  const loadDetail = id => id ? request(`/panel/conversaciones/${id}`).then(d => setDetail(d.id === id ? d : null)).catch(e => setError(e.message)) : Promise.resolve()
  // Se actualiza solo: los mensajes nuevos y los estados de entrega llegan por el webhook de Twilio.
  useEffect(() => { loadList(); const timer = setInterval(loadList, 10000); return () => clearInterval(timer) }, [])
  useEffect(() => { setDetail(null); loadDetail(selected); const timer = setInterval(() => loadDetail(selected), 5000); return () => clearInterval(timer) }, [selected])
  // Envía un mensaje del operador al cliente. El cuadro de texto solo aparece si
  // la ventana de 24 horas de WhatsApp está abierta (detail.ventana_abierta).
  async function send(e) { e.preventDefault(); if (!text.trim()) return; setSending(true); setError(''); try { await request(`/panel/conversaciones/${selected}/mensajes`, { method: 'POST', body: JSON.stringify({ contenido: text }) }); setText(''); await Promise.all([loadDetail(selected), loadList()]) } catch (err) { setError(err.message) } finally { setSending(false) } }
  // Alterna entre 'atiende la IA' y 'atiende el operador' (campo atendida_por_humano).
  async function toggle() { try { setDetail(await request(`/panel/conversaciones/${selected}`, { method: 'PATCH', body: JSON.stringify({ atendida_por_humano: !detail.atendida_por_humano }) })); loadList() } catch (err) { setError(err.message) } }
  // Dispara a mano el envío de los recordatorios de mañana (el sistema también
  // los manda solo, a la hora configurada).
  async function reminders() { setError(''); try { const r = await request('/panel/whatsapp/recordatorios', { method: 'POST' }); setNotice(`Recordatorios de mañana enviados: ${r.enviados}${r.no_enviados ? ` · no enviados: ${r.no_enviados}` : ''}`) } catch (err) { setError(err.message) } }
  return <><header className="topbar"><div><p className="eyebrow">ATENCIÓN AL CLIENTE</p><h1>WhatsApp</h1><p className="muted">Revisa lo que conversa el agente IA y responde tú cuando haga falta.</p></div><button className="secondary" onClick={reminders}>Enviar recordatorios de mañana</button></header>{error && <div className="error banner">{error}</div>}{notice && <div className="notice banner">{notice}</div>}<section className="inbox"><div className="inbox-list">{conversations.map(c => <button key={c.id} className={`inbox-item ${c.id === selected ? 'active' : ''}`} onClick={() => setSelected(c.id)}><strong>{c.cliente.nombre}</strong><small>{c.cliente.telefono_whatsapp}</small><span>{c.ultimo_emisor && `${SENDERS[c.ultimo_emisor] || c.ultimo_emisor}: `}{c.ultimo_mensaje}</span><span className={`pill ${c.atendida_por_humano ? 'orange' : 'green'}`}>{c.atendida_por_humano ? 'Operador' : 'IA'}</span></button>)}{!conversations.length && <div className="empty">Todavía no hay conversaciones de WhatsApp.</div>}</div><div className="thread">{detail ? <><div className="thread-head"><div><strong>{detail.cliente.nombre}</strong><small>{detail.cliente.telefono_whatsapp}</small></div><button className={detail.atendida_por_humano ? 'primary' : 'secondary'} onClick={toggle}>{detail.atendida_por_humano ? 'Devolver a la IA' : 'Tomar conversación'}</button></div><div className="messages">{detail.mensajes.map(m => <div key={m.id} className={`bubble ${m.emisor}`}><small>{SENDERS[m.emisor] || m.emisor} · {chileDateTime(m.created_at)}</small><p>{m.contenido}</p><Delivery message={m} /></div>)}</div>{detail.ventana_abierta ? <form className="composer" onSubmit={send}><textarea rows="2" aria-label="Mensaje para el cliente" placeholder={detail.atendida_por_humano ? 'Escribe tu respuesta' : 'Al enviar, la IA deja de responder en esta conversación'} value={text} onChange={e => setText(e.target.value)} /><button className="primary" disabled={sending || !text.trim()}>Enviar</button></form> : <div className="composer closed">El cliente no escribe hace más de 24 h: WhatsApp solo permite responder cuando vuelva a escribir.</div>}</> : <div className="empty">Selecciona una conversación.</div>}</div></section></>
}
