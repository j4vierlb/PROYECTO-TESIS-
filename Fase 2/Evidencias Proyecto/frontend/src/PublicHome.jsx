import React, { useEffect, useMemo } from 'react'
import QRCode from 'qrcode'
import { BrandLogo } from './BrandLogo.jsx'
import { companyInfo, whatsappSandbox } from './public-site-config.js'
import { sandboxLink } from './whatsapp-sandbox.js'
import './public-home.css'

export function SandboxQr({ href }) {
  const modules = useMemo(() => QRCode.create(href, { errorCorrectionLevel: 'M' }).modules, [href])
  const path = []
  for (let y = 0; y < modules.size; y++) {
    for (let x = 0; x < modules.size; x++) {
      if (modules.get(y, x)) path.push(`M${x + 4} ${y + 4}h1v1h-1z`)
    }
  }
  return <svg className="public-qr" role="img" aria-label="Código QR para abrir WhatsApp con el mensaje de unión al Sandbox" viewBox={`0 0 ${modules.size + 8} ${modules.size + 8}`} width="208" height="208" shapeRendering="crispEdges">
    <rect width="100%" height="100%" fill="#fff" />
    <path d={path.join('')} fill="#000" />
  </svg>
}

function ChatIcon() {
  return <svg aria-hidden="true" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7"><path d="M21 11.5a9 9 0 0 1-9 9 10 10 0 0 1-4-.9L3 21l1.4-4.7a9 9 0 1 1 16.6-4.8Z" /><path d="M8 9h8M8 13h5" /></svg>
}

export function PublicHome({ onEnter, sandbox = whatsappSandbox }) {
  const href = sandboxLink(sandbox)
  useEffect(() => {
    const previous = document.title
    document.title = 'Kill Bichos | Control de plagas'
    return () => { document.title = previous }
  }, [])
  return <div className="public-home">
    <a className="public-skip" href="#contenido-publico">Saltar al contenido</a>
    <header className="public-header">
      <a className="public-brand" href="#contenido-publico" aria-label="Kill Bichos, inicio"><BrandLogo /><span><strong>Kill Bichos</strong><small>Control de plagas</small></span></a>
      <nav aria-label="Información de Kill Bichos"><a href="#servicios">Servicios</a><a href="#contacto">Contacto</a></nav>
      <button type="button" className="public-enter" onClick={onEnter}>Ingresar <span aria-hidden="true">↗</span></button>
    </header>
    <main id="contenido-publico" tabIndex={-1}>
      <section className="public-hero" aria-labelledby="public-title">
        <div className="public-intro">
          <p className="public-kicker"><span aria-hidden="true" />{companyInfo.district}</p>
          <h1 id="public-title">Kill Bichos<span>Control de plagas.</span></h1>
          <p className="public-lead">Desinsectación, desratización y sanitización.</p>
          <a className="public-text-link" href="#servicios">Conoce nuestros servicios <span aria-hidden="true">↓</span></a>
          <div className="public-about"><h2>Quiénes somos</h2><p>{companyInfo.about}</p></div>
        </div>
        <section className="public-chat" aria-labelledby="public-chat-title">
          <div className="public-chat-heading"><ChatIcon /><span>WHATSAPP · DEMOSTRACIÓN</span></div>
          <h2 id="public-chat-title">Hablemos por WhatsApp</h2>
          <p className="public-sandbox-note">Este WhatsApp es de prueba (Sandbox de Twilio). No es un servicio abierto al público.</p>
          {href ? <>
            <a className="public-qr-link" href={href} target="_blank" rel="noopener noreferrer" aria-label="Abrir WhatsApp de prueba desde el código QR"><SandboxQr href={href} /></a>
            <p className="public-qr-caption">Escanea el QR o usa el botón desde tu teléfono.</p>
            <a className="public-whatsapp" href={href} target="_blank" rel="noopener noreferrer"><ChatIcon />Hablemos por WhatsApp <span aria-hidden="true">↗</span></a>
          </> : <>
            <div className="public-chat-unavailable"><ChatIcon /><p>El WhatsApp de prueba no está disponible por el momento.</p><p>Puedes contactarnos por teléfono o correo.</p></div>
            <button type="button" className="public-whatsapp" disabled>Hablemos por WhatsApp</button>
          </>}
          <p className="public-send-note">El enlace prepara el mensaje de unión. Tú debes enviarlo desde WhatsApp.</p>
        </section>
      </section>
      <section className="public-services public-section" id="servicios" aria-labelledby="public-services-title">
        <div className="public-section-heading"><p className="public-kicker">SERVICIOS</p><h2 id="public-services-title">Control de plagas</h2></div>
        <div className="public-service-grid">{companyInfo.services.map((service, index) => <article key={service.name}>
          <span className="public-service-number" aria-hidden="true">0{index + 1}</span><h3>{service.name}</h3><p>{service.description}</p>
        </article>)}</div>
      </section>
      <section className="public-guide public-section" aria-labelledby="public-guide-title">
        <div className="public-section-heading"><p className="public-kicker">GUÍA DE PRUEBA</p><h2 id="public-guide-title">Tres pasos para conversar</h2></div>
        <ol><li><span aria-hidden="true">1</span><div><h3>Escanea o toca el botón</h3><p>Abre el chat del Sandbox de Twilio desde el QR o «Hablemos por WhatsApp».</p></div></li><li><span aria-hidden="true">2</span><div><h3>Envía el mensaje de unión</h3><p>Envía el mensaje que aparecerá escrito en WhatsApp. Espera la confirmación de unión.</p></div></li><li><span aria-hidden="true">3</span><div><h3>Escribe qué necesitas</h3><p>Por ejemplo: «quiero agendar una visita».</p></div></li></ol>
      </section>
      <section className="public-contact public-section" id="contacto" aria-labelledby="public-contact-title">
        <div className="public-section-heading"><p className="public-kicker">CONTACTO DE LA EMPRESA</p><h2 id="public-contact-title">Conversemos</h2><p>Para contactar a Kill Bichos, utiliza estos datos.</p></div>
        <dl><div><dt>Dirección · {companyInfo.district}</dt><dd>{companyInfo.address}</dd></div><div><dt>Teléfono</dt><dd><a href={companyInfo.phoneHref}>{companyInfo.phone}</a></dd></div><div><dt>Correo</dt><dd><a href={`mailto:${companyInfo.email}`}>{companyInfo.email}</a></dd></div><div><dt>Horarios</dt><dd>{companyInfo.hours || 'Consulta los horarios por teléfono o correo.'}</dd></div></dl>
      </section>
    </main>
    <footer className="public-footer"><strong>Kill Bichos</strong><span>Control de plagas · {companyInfo.district}</span><a href={companyInfo.website} target="_blank" rel="noopener noreferrer">Sitio de la empresa <span aria-hidden="true">↗</span></a></footer>
  </div>
}
