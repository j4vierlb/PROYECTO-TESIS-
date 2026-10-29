import React, { useEffect, useMemo, useRef } from 'react'
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

// Insignia de WhatsApp con la marca: cuadro negro, burbuja amarilla y tres puntos
// que "escriben". Es decorativa (el texto de al lado ya dice qué es).
function ChatBadge() {
  return <span className="public-chat-badge" aria-hidden="true">
    <svg viewBox="0 0 48 48" width="52" height="52" focusable="false">
      <rect width="48" height="48" rx="14" fill="#1A1A1A" />
      <path d="M24 10.5c-7.9 0-14.3 5.3-14.3 11.9 0 3.5 1.9 6.7 4.8 8.8L13.3 38l6.6-3.4c1.3.3 2.7.5 4.1.5 7.9 0 14.3-5.3 14.3-11.9S31.9 10.5 24 10.5Z" fill="#F5C518" />
      <circle className="public-typing public-typing-1" cx="17.8" cy="22.6" r="2" fill="#1A1A1A" />
      <circle className="public-typing public-typing-2" cx="24" cy="22.6" r="2" fill="#1A1A1A" />
      <circle className="public-typing public-typing-3" cx="30.2" cy="22.6" r="2" fill="#1A1A1A" />
    </svg>
  </span>
}

// Hace aparecer los bloques marcados con data-reveal cuando entran en pantalla
// al hacer scroll (una sola vez). Sin IntersectionObserver, o con movimiento
// reducido, todo se muestra de inmediato: nunca queda contenido oculto.
function useReveal() {
  const ref = useRef(null)
  useEffect(() => {
    const root = ref.current
    if (!root) return undefined
    const items = [...root.querySelectorAll('[data-reveal]')]
    const reducido = typeof window.matchMedia === 'function' && window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (typeof IntersectionObserver === 'undefined' || reducido) {
      items.forEach(el => el.classList.add('is-visible'))
      return undefined
    }
    root.classList.add('reveal-ready')
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return
        entry.target.classList.add('is-visible')
        observer.unobserve(entry.target)
      })
    }, { threshold: 0.12, rootMargin: '0px 0px -6% 0px' })
    items.forEach(el => observer.observe(el))
    return () => observer.disconnect()
  }, [])
  return ref
}

function ChatIcon() {
  return <svg aria-hidden="true" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7"><path d="M21 11.5a9 9 0 0 1-9 9 10 10 0 0 1-4-.9L3 21l1.4-4.7a9 9 0 1 1 16.6-4.8Z" /><path d="M8 9h8M8 13h5" /></svg>
}

// La araña del logo colgando de su hilo, dibujada en el mismo cuadro negro y
// amarillo. Va dentro del título como si fuera una palabra más y baja una vez
// al abrir la página. Es decorativa: el título ya dice "Control de plagas".
function SpiderFrame() {
  const legs = 'M60 36 48 28 40 18M60 38 44 36 34 34M60 40 45 46 36 54M60 42 49 54 44 62M60 36 72 28 80 18M60 38 76 36 86 34M60 40 75 46 84 54M60 42 71 54 76 62'
  return <svg className="public-spider-frame" aria-hidden="true" focusable="false" viewBox="0 0 120 70">
    <rect width="120" height="70" rx="16" fill="#1A1A1A" />
    <g className="public-spider">
      <line x1="60" y1="-60" x2="60" y2="27" stroke="#F5C518" strokeWidth="1.6" />
      <path d={legs} fill="none" stroke="#F5C518" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
      <ellipse cx="60" cy="42" rx="9" ry="11" fill="#F5C518" />
      <circle cx="60" cy="30" r="6" fill="#F5C518" />
    </g>
  </svg>
}

const archivo = {
  Desinsectación: { src: '/archivo/cucaracha.jpg', alt: 'Grabado antiguo de una cucaracha americana', fit: 'center' },
  Desratización: { src: '/archivo/rata.jpg', alt: 'Aguafuerte de 1823 con una cacería de ratas', fit: 'center 62%' },
  Sanitización: { src: '/archivo/microbios.jpg', alt: 'Afiche francés de 1897 con el lema «Plus de microbes»', fit: 'center 12%' },
}

const creditos = [
  ['Cucaracha americana', 'ilustrador desconocido, dominio público', 'https://commons.wikimedia.org/wiki/File:American_cockroach_(Blatta_Americana).jpg'],
  ['Cacería de ratas', 'Edwin Landseer, 1823, dominio público', 'https://commons.wikimedia.org/wiki/File:Rat_catching_etching_E_Landseer_SLNSW.jpg'],
  ['Plus de microbes', 'Firmin Bouisset, 1897, dominio público', 'https://commons.wikimedia.org/wiki/File:Plus_de_microbes._Toutes_les_eaux_min%C3%A9rales._Entrep%C3%B4t_d%27Ivry_affiche,_Firmin_Bouisset.jpg'],
  ['Una araña, ampliada y en tamaño real', 'grabado coloreado, Wellcome Collection, CC BY 4.0', 'https://commons.wikimedia.org/wiki/File:A_spider,_both_enlarged_and_life_size._Coloured_engraving._Wellcome_V0022389.jpg'],
]

export function PublicHome({ onEnter, sandbox = whatsappSandbox }) {
  const href = sandboxLink(sandbox)
  const rootRef = useReveal()
  useEffect(() => {
    const previous = document.title
    document.title = 'Kill Bichos | Control de plagas'
    return () => { document.title = previous }
  }, [])
  return <div className="public-home" ref={rootRef}>
    <a className="public-skip" href="#contenido-publico">Saltar al contenido</a>
    <div className="public-stage">
      <header className="public-header">
        <a className="public-brand" href="#contenido-publico" aria-label="Kill Bichos, inicio"><BrandLogo /><span><strong>Kill Bichos</strong><small>Control de plagas</small></span></a>
        <nav aria-label="Información de Kill Bichos"><a href="#servicios">Servicios</a><a href="#contacto">Contacto</a></nav>
        <button type="button" className="public-enter" onClick={onEnter}>Ingresar <span aria-hidden="true">↗</span></button>
      </header>
      <section className="public-hero" aria-labelledby="public-title">
        <div className="public-intro">
          <p className="public-kicker"><span aria-hidden="true" />{companyInfo.district}</p>
          <h1 id="public-title">Kill Bichos<span>Control de <SpiderFrame />plagas.</span></h1>
          <p className="public-lead">Desinsectación, desratización y sanitización.</p>
          <a className="public-text-link" href="#servicios">Conoce nuestros servicios <span aria-hidden="true">↓</span></a>
        </div>
      </section>
    </div>
    <main id="contenido-publico" tabIndex={-1}>
      <section className="public-chat" aria-labelledby="public-chat-title">
        <div className="public-chat-copy">
          <div className="public-chat-heading"><ChatBadge /><span>WHATSAPP · DEMOSTRACIÓN</span></div>
          <h2 id="public-chat-title">Hablemos por WhatsApp</h2>
          <p className="public-sandbox-note">Este WhatsApp es de prueba (Sandbox de Twilio). No es un servicio abierto al público.</p>
          <p className="public-send-note">El enlace prepara el mensaje de unión. Tú debes enviarlo desde WhatsApp.</p>
        </div>
        <div className="public-chat-card">
          {href ? <>
            <a className="public-qr-link" href={href} target="_blank" rel="noopener noreferrer" aria-label="Abrir WhatsApp de prueba desde el código QR"><SandboxQr href={href} /></a>
            <p className="public-qr-caption">Escanea el QR o usa el botón desde tu teléfono.</p>
            <a className="public-whatsapp" href={href} target="_blank" rel="noopener noreferrer"><ChatIcon />Hablemos por WhatsApp <span aria-hidden="true">↗</span></a>
          </> : <>
            <div className="public-chat-unavailable"><ChatIcon /><p>El WhatsApp de prueba no está disponible por el momento.</p><p>Puedes contactarnos por teléfono o correo.</p></div>
            <button type="button" className="public-whatsapp" disabled>Hablemos por WhatsApp</button>
          </>}
        </div>
      </section>
      <section className="public-about" aria-labelledby="public-about-title">
        <div className="public-about-text"><h2 id="public-about-title">Quiénes somos</h2><p>{companyInfo.about}</p></div>
        <img src="/archivo/arana.jpg" alt="Grabado coloreado de una araña, ampliada y en tamaño real" width="1000" height="1177" loading="lazy" />
      </section>
      <section className="public-services public-section" id="servicios" aria-labelledby="public-services-title">
        <div className="public-section-heading" data-reveal><p className="public-kicker">SERVICIOS</p><h2 id="public-services-title">Control de plagas</h2></div>
        <div className="public-service-grid">{companyInfo.services.map((service, index) => {
          const foto = archivo[service.name]
          return <article key={service.name} data-reveal style={{ '--i': index }}>
            <div className="public-service-text"><h3>{service.name}</h3><p>{service.description}</p></div>
            {foto && <img src={foto.src} alt={foto.alt} style={{ objectPosition: foto.fit }} width="900" height="600" loading="lazy" />}
          </article>
        })}</div>
      </section>
      <section className="public-guide public-section" aria-labelledby="public-guide-title">
        <div className="public-section-heading" data-reveal><p className="public-kicker">GUÍA DE PRUEBA</p><h2 id="public-guide-title">Tres pasos para conversar</h2></div>
        <ol><li data-reveal style={{ '--i': 0 }}><span aria-hidden="true">1</span><div><h3>Escanea o toca el botón</h3><p>Abre el chat del Sandbox de Twilio desde el QR o «Hablemos por WhatsApp».</p></div></li><li data-reveal style={{ '--i': 1 }}><span aria-hidden="true">2</span><div><h3>Envía el mensaje de unión</h3><p>Envía el mensaje que aparecerá escrito en WhatsApp. Espera la confirmación de unión.</p></div></li><li data-reveal style={{ '--i': 2 }}><span aria-hidden="true">3</span><div><h3>Escribe qué necesitas</h3><p>Por ejemplo: «quiero agendar una visita».</p></div></li></ol>
      </section>
      <section className="public-contact public-section" id="contacto" aria-labelledby="public-contact-title">
        <div className="public-section-heading" data-reveal><p className="public-kicker">CONTACTO DE LA EMPRESA</p><h2 id="public-contact-title">Conversemos</h2><p>Para contactar a Kill Bichos, utiliza estos datos.</p></div>
        <dl data-reveal style={{ '--i': 1 }}><div><dt>Dirección · {companyInfo.district}</dt><dd>{companyInfo.address}</dd></div><div><dt>Teléfono</dt><dd><a href={companyInfo.phoneHref}>{companyInfo.phone}</a></dd></div><div><dt>Correo</dt><dd><a href={`mailto:${companyInfo.email}`}>{companyInfo.email}</a></dd></div><div><dt>Horarios</dt><dd>{companyInfo.hours || 'Consulta los horarios por teléfono o correo.'}</dd></div></dl>
      </section>
    </main>
    <footer className="public-footer">
      <div className="public-footer-main"><strong>Kill Bichos</strong><span>Control de plagas · {companyInfo.district}</span><a href={companyInfo.website} target="_blank" rel="noopener noreferrer">Sitio de la empresa <span aria-hidden="true">↗</span></a></div>
      <details className="public-credits"><summary>Créditos de las imágenes</summary><div>{creditos.map(([titulo, autor, enlace]) => <p key={titulo}><a href={enlace} target="_blank" rel="noopener noreferrer">{titulo}</a>, {autor}, vía Wikimedia Commons.</p>)}</div></details>
    </footer>
  </div>
}
