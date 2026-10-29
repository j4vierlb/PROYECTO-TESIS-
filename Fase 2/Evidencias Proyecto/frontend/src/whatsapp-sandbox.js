// Un mismo enlace para el botón y el QR. No usa sesiones, backend ni servicios QR externos.
export function sandboxLink({ phone, joinMessage } = {}) {
  if (typeof phone !== 'string' || typeof joinMessage !== 'string') return null
  const number = phone.trim().replace(/[ ()-]/g, '')
  const message = joinMessage.trim()
  if (!/^\+?[1-9]\d{7,14}$/.test(number)) return null
  if (!/^join [a-z0-9]+(?:-[a-z0-9]+)*$/i.test(message) || message.length > 100) return null
  return `https://wa.me/${number.replace(/^\+/, '')}?text=${encodeURIComponent(message)}`
}
