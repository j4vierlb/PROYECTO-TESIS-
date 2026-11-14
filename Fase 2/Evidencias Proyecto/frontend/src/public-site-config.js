// Servicios y contacto publicados en https://killbichos.cl/, consultada el 28/10/2026.
// Presentación breve basada en la información entregada por Juan el mismo día.
// Horario y número confirmados por Juan el 29/10/2026; mensaje leído del QR enviado.
// No se infieren cobertura ni certificaciones.
// Plagas, garantía, seguridad e Instagram: textos tomados de https://killbichos.cl/ el 14/11/2026.
export const companyInfo = {
  name: 'Kill Bichos',
  activity: 'Control de plagas',
  about: 'Somos una empresa chilena especializada en control de plagas para hogares y espacios comerciales. Nuestros servicios incluyen fumigación, desinsectación, desratización y sanitización ambiental, además del control de insectos rastreros, voladores y roedores.',
  services: [
    { name: 'Desinsectación', description: 'Control de plagas urbanas mediante productos y equipos adecuados para cada necesidad.' },
    { name: 'Desratización', description: 'Instalación de estaciones cebadoras para formar un perímetro de control de roedores.' },
    { name: 'Sanitización', description: 'Tratamiento para reducir microorganismos en espacios como cocinas, duchas y camarines.' },
  ],
  district: 'Macul, Santiago',
  address: 'Av. Luis Valenzuela Aris 3273, Macul, Santiago, Chile.',
  phone: '+56 9 9093 0634',
  phoneHref: 'tel:+56990930634',
  email: 'ventas@killbichos.cl',
  hours: 'Lunes a sábado, de 08:00 a 18:00 horas.',
  website: 'https://killbichos.cl/',
  instagram: 'https://www.instagram.com/killbichos/',
}

// Datos públicos del Sandbox, separados del teléfono comercial. No son credenciales.
// El enlace coincide con el QR proporcionado por Javier a través de Juan.
export const whatsappSandbox = { phone: '+14155238886', joinMessage: 'join example-primitive' }

// Plagas que controla la empresa, agrupadas como en su sitio. La app móvil muestra
// la misma lista en app-movil/lib/models/plagas.dart: si cambia aquí, cambiarla allá.
export const pestGroups = [
  { name: 'Voladores', examples: 'Moscas, mosquitos, polillas y otros insectos voladores.', photo: { src: '/plagas/mosquito.jpg', alt: 'Mosquito Aedes aegypti posado sobre la piel', position: 'center' } },
  { name: 'Rastreros', examples: 'Cucarachas, pulgas, hormigas, tijeretas y similares.', photo: { src: '/plagas/cucaracha.jpg', alt: 'Cucaracha americana sobre fondo blanco', position: 'center' } },
  { name: 'Arácnidos', examples: 'Arañas, garrapatas y ácaros.', photo: { src: '/plagas/arana.jpg', alt: 'Araña de casa sobre una pared blanca', position: 'center 35%' } },
]

// Garantía y seguridad, con las palabras del sitio de la empresa.
export const serviceAssurance = {
  guaranteeTitle: 'Garantía de 30 días',
  guaranteeText: 'Las plagas rastreras y los arácnidos deben desaparecer casi al 100 %, y las voladoras bajan su población considerablemente. Si no quedas satisfecho, puedes pedir reforzar una zona particular o una re-aplicación total.',
  safetyTitle: 'Productos seguros',
  safetyText: 'Los productos son seguros para las personas, las mascotas y las plantas, y no manchan los muros.',
}
