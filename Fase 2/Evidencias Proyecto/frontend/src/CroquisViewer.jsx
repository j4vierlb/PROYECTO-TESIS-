import React, { useEffect, useRef, useState } from 'react'
import { request, requestPhoto } from './api.js'
import { coordinates, drawCroquis, loadMaps, trapAppearance } from './croquis-map.js'

function TrapPhoto({ device }) {
  const [result, setResult] = useState(null), [retry, setRetry] = useState(0)
  useEffect(() => {
    if (!device.foto_url) return
    const controller = new AbortController()
    let objectUrl
    setResult(null)
    requestPhoto(device.foto_url, { signal: controller.signal }).then(blob => {
      if (controller.signal.aborted) return
      objectUrl = URL.createObjectURL(blob)
      setResult({ url: objectUrl })
    }).catch(error => {
      if (!controller.signal.aborted) setResult({ error: error.status === 404 ? 'La foto ya no está disponible.' : error.status === 403 ? 'No tienes permiso para ver esta foto.' : error.message })
    })
    return () => { controller.abort(); if (objectUrl) URL.revokeObjectURL(objectUrl) }
  }, [device.foto_url, retry])
  if (!device.foto_url) return <p className="muted">Sin foto registrada.</p>
  if (!result) return <p role="status">Cargando foto…</p>
  if (result.error) return <><p role="alert" className="error">{result.error}</p><button type="button" className="secondary" onClick={() => setRetry(value => value + 1)}>Reintentar foto</button></>
  return <img className="trap-photo" src={result.url} alt={`Foto de la trampa ${device.codigo}`} onError={() => setResult({ error: 'No se pudo mostrar la foto. Intenta nuevamente.' })} />
}

function CroquisMap({ devices, client, selected, onSelect }) {
  const element = useRef(null), instance = useRef(null), latestSelect = useRef(onSelect)
  latestSelect.current = onSelect
  const [error, setError] = useState(''), [ready, setReady] = useState(false), [retry, setRetry] = useState(0)
  useEffect(() => {
    if (!devices.some(coordinates) && !coordinates(client)) return
    let disposed = false
    setError(''); setReady(false)
    const previousAuthFailure = window.gm_authFailure
    const authFailure = () => { if (!disposed) setError('Google Maps rechazó la clave o sus restricciones. El listado y las fotos siguen disponibles.') }
    window.gm_authFailure = authFailure
    const timeout = setTimeout(() => { if (!disposed) setError('Google Maps no respondió. Comprueba tu conexión y reintenta.') }, 15000)
    loadMaps().then(maps => {
      if (disposed) return
      clearTimeout(timeout)
      instance.current = drawCroquis(maps, element.current, devices, client, id => latestSelect.current(id))
      setReady(true)
    }).catch(() => { if (!disposed) { clearTimeout(timeout); setError(import.meta.env.VITE_GOOGLE_MAPS_API_KEY ? 'No se pudo cargar Google Maps. Revisa la conexión y la configuración de la clave.' : 'Falta configurar la clave web de Google Maps. Puedes consultar las trampas y sus fotos en el listado.') } })
    return () => {
      disposed = true; clearTimeout(timeout); instance.current?.destroy(); instance.current = null
      if (window.gm_authFailure === authFailure) window.gm_authFailure = previousAuthFailure
    }
  }, [devices, client, retry])
  useEffect(() => { if (ready) instance.current?.select(selected) }, [selected, ready])
  const located = devices.some(coordinates) || coordinates(client)
  if (!located) return <p className="info">No hay coordenadas válidas para mostrar este croquis en el mapa. Consulta las trampas en el listado.</p>
  return <section className="croquis-map-section" aria-label="Ubicación de trampas">
    {error ? <div className="info" role="status">{error} <button type="button" className="link-button" onClick={() => setRetry(value => value + 1)}>Reintentar mapa</button></div> : !ready && <p role="status">Cargando mapa…</p>}
    <div ref={element} className={`croquis-map ${error ? 'map-unavailable' : ''}`} aria-label="Mapa satelital del croquis" />
  </section>
}

export function CroquisViewer({ visit }) {
  const [result, setResult] = useState(null), [revision, setRevision] = useState(0), [selected, setSelected] = useState(null)
  useEffect(() => {
    const controller = new AbortController()
    setResult(null); setSelected(null)
    request(`/croquis/${visit.id}`, { method: 'GET', signal: controller.signal }).then(data => {
      if (controller.signal.aborted) return
      if (data.visita_id !== visit.id || !Array.isArray(data.dispositivos)) throw new Error('El servidor entregó un croquis inválido. Actualiza e intenta nuevamente.')
      setResult({ data }); setSelected(data.dispositivos[0]?.id || null)
    }).catch(error => {
      if (!controller.signal.aborted) setResult({ error: error.status === 404 ? 'La visita no tiene un croquis disponible. El técnico debe crearlo desde la app.' : error.status === 403 ? 'No tienes permiso para ver el croquis de esta visita.' : error.message, status: error.status })
    })
    return () => controller.abort()
  }, [visit.id, revision])
  const devices = result?.data?.dispositivos || []
  const device = devices.find(item => item.id === selected)
  return <div className="croquis-viewer">
    <p className="muted">{visit.cliente.nombre} · Solo lectura. Las trampas se gestionan desde la app del técnico.</p>
    {!result ? <p role="status">Cargando croquis…</p> : result.error ? <div><p role={result.status === 404 ? 'status' : 'alert'} className={result.status === 404 ? 'info' : 'error'}>{result.error}</p><button type="button" className="secondary" onClick={() => setRevision(value => value + 1)}>Reintentar croquis</button></div> : <>
      <div className="croquis-summary"><span>Versión {result.data.version} · {devices.length} trampas</span><span>{result.data.validado_por_operador ? 'Validado por el técnico' : 'Pendiente de validación del técnico'}</span><button type="button" className="secondary" onClick={() => setRevision(value => value + 1)}>Actualizar croquis</button></div>
      <p className="field-help">Verde: confirmada · Amarillo: IA sin confirmar · Azul: sin confirmar · Naranja: revisar · Gris tenue: retirada.</p>
      <CroquisMap devices={devices} client={visit.cliente} selected={selected} onSelect={setSelected} />
      {!devices.length ? <p className="info">El croquis existe, pero aún no tiene trampas registradas.</p> : <div className="croquis-details">
        <section aria-label="Trampas del croquis" className="trap-list">{devices.map(item => {
          const appearance = trapAppearance(item)
          return <button key={item.id} type="button" className={`trap-item ${appearance.tone}`} aria-pressed={selected === item.id} onClick={() => setSelected(item.id)}><strong>{item.codigo}</strong><span>{appearance.label}</span><small>{item.tipo.replaceAll('_', ' ')} · {item.foto_url ? 'Con foto' : 'Sin foto'}</small></button>
        })}</section>
        {device && <section className="trap-detail" aria-label={`Detalle de ${device.codigo}`}><h3>{device.codigo}</h3><p>{trapAppearance(device).label}</p><p className="field-help">{coordinates(device) ? `${device.lat.toFixed(6)}, ${device.lng.toFixed(6)}` : 'Sin coordenadas válidas'}</p><TrapPhoto key={device.id} device={device} /></section>}
      </div>}
    </>}
  </div>
}
