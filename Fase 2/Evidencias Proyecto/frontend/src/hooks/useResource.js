// Hook que carga datos de la API y cancela las cargas antiguas al navegar.
import { useEffect, useState } from 'react'
import { request } from '../api.js'

// Cancela cargas antiguas al navegar: una respuesta lenta no reemplaza el día actual.
export function useResource(paths) {
  // Las rutas se convierten a texto para poder compararlas: así el efecto solo
  // se vuelve a ejecutar si cambian de verdad (y no en cada repintado).
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
