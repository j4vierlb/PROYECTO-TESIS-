# Portada pública y Sandbox configurado — 29/10/2026

Trabajo exclusivamente en `juan`. Las pruebas se ejecutaron sobre `0329ec2`
más los cambios de la portada. Antes de publicar se incorporó por fast-forward
`origin/main` en `1520c4b` (PR #27 fusionada), cuyo árbol de archivos es idéntico
al de `0329ec2`: no cambió el código probado. La portada se entrega en una PR
propia, separada de la geocodificación nacional. Este registro no acredita un
despliegue en Docker.

## Contenido y procedencia

- Servicios, dirección de contacto en Macul, teléfono comercial y correo:
  [killbichos.cl](https://killbichos.cl/), consultado el 28/10/2026.
- Presentación breve: resumen de la información entregada por Juan. No se
  publican garantías, números de resoluciones sanitarias ni afirmaciones de
  cobertura no verificadas. La dirección de la tienda de Estación Central no
  sustituye el contacto del sitio corporativo.
- Horario confirmado por Juan el 29/10: lunes a sábado, de 08:00 a 18:00 horas.
- Sandbox confirmado: `whatsapp:+14155238886`. Se usa `+14155238886` para formar
  un enlace `wa.me`; se mantiene separado del teléfono comercial de Kill Bichos.
- Mensaje de unión leído localmente del JPEG aportado por Juan:
  `join example-primitive`. El enlace del QR original es exactamente
  `https://wa.me/14155238886?text=join%20example-primitive`.

El mensaje de unión y el número son públicos, no credenciales. La imagen se
decodificó localmente mediante Pillow y jsQR; no se envió a un servicio externo.
El QR de la portada se genera como SVG, con margen blanco y contraste negro,
sin copiar la imagen JPEG ni llamar a una API de generación de QR.

## Resultados automatizados

| Comprobación | Resultado | Evidencia |
|---|---|---|
| Frontend completo, incluidos panel, recuperación, croquis y portada | **161/161**, 10 archivos | [frontend.log](frontend.log) |
| Compilación de producción | Correcta | [frontend_build.log](frontend_build.log) |
| Decodificación del QR renderizado | Coincide exactamente con el QR de Juan y con el botón | Caso incluido en `frontend.log` |

Se conservan los contadores originales de los cortes del 28/10 en su carpeta;
no se suman a los 161 casos actuales. Las respuestas de autenticación/API en
Vitest están simuladas. Las pruebas no envían WhatsApp, correos ni llamadas a
Google/OpenAI y no modifican la base de trabajo.

Los casos de portada cubren: información y marca, guía de tres pasos, horario,
entrada por botón y teclado, sesión activa directa al panel, vencimiento y cierre
en otra pestaña, prioridad de recuperación con/sin sesión y por `hashchange`,
limpieza del token de la URL, enlace de WhatsApp codificado, mismo destino para
botón y QR, decodificación real del QR SVG y configuración inválida sin enlaces
ni QR ficticios. Los tests anteriores de login se adaptaron para pasar primero
por Ingresar; el componente Login y su contrato HTTP permanecen iguales.

## Comprobación manual en navegador

Se sirvió la compilación de producción en `http://localhost:5173/`, sin cambiar
los contenedores de trabajo ni sus variables. La sesión que ya existía abrió
el panel; tras cerrar sesión y recargar apareció la portada.

| Caso | Resultado observado | Evidencia |
|---|---|---|
| PUB-01 Portada, marca, presentación y QR | Correcto en escritorio | [portada_escritorio.png](portada_escritorio.png) |
| PUB-02 Guía, contacto y horario | Horario confirmado y contactos visibles | [guia_horario_contacto.png](guia_horario_contacto.png) |
| PUB-03 Destino del botón | WhatsApp redirige a `api.whatsapp.com`, muestra **Twilio Sandbox** y `join example-primitive` preparado | [destino_whatsapp.png](destino_whatsapp.png) |
| PUB-04 Ingresar y recuperación | Ingresar abre el login; Olvidé mi contraseña abre su formulario | Observación de interfaz; no se solicitó correo ni se cambió contraseña |
| PUB-05 Enlace de restablecimiento | Abre Nueva contraseña y retira el fragmento de la URL | [restablecer_token_sintetico.png](restablecer_token_sintetico.png); token sintético, sin envío |
| PUB-06 Vistas estrechas | Marca, textos, QR y botón se adaptan a 390 y 320 px | [responsive_inicio.png](responsive_inicio.png), [responsive_qr.png](responsive_qr.png) |

Las vistas estrechas son iframes en un navegador de escritorio, no pruebas de
hardware ni de Safari/Chrome móvil. El auxiliar de QA se copió temporalmente a
`dist/__qa_portada_responsive.html` desde el registro del 28/10 y se retira al
terminar; no es parte de la compilación de producción ni del producto.

El navegador integrado no mostró una nueva pestaña inmediatamente después del
clic en el enlace con `target="_blank"`; se verificó el destino abriendo en una
pestaña de prueba la misma URL observada en el botón. No se envió el mensaje ni
se inició sesión en WhatsApp Web. La apertura y envío desde el dispositivo real
se distingue en la confirmación del usuario siguiente.

## Confirmación del usuario en teléfono

El 29/10 Juan informó: «cuando Javier me mandó el QR lo escaneé y funcionó todo
y conversamos». Esto confirma por declaración del usuario que el QR original
permitió llegar al Sandbox y conversar con el agente desde su teléfono.

El QR regenerado en la portada codifica exactamente ese enlace, comprobado por
decodificación automatizada. No se presenta la confirmación anterior como un
escaneo físico del QR nuevo ni como una prueba automatizada de la conversación.

## Alcance y pendientes de entrega

Solo se cambian frontend, sus dependencias, tests y documentación. No hay cambios
de backend, migraciones, datos, llaves, `.env` ni configuración de Docker. No se
incorporan scripts, trackers ni formularios de contacto del sitio corporativo.
La portada y sus estilos están separados de los estilos del panel.

El número comercial continúa como enlace telefónico; el WhatsApp de la portada
apunta al Sandbox. Ambos enlaces externos usan `noopener noreferrer`, sin
agregar datos de sesión ni tokens al destino.

Primer avance disponible antes del viernes 6/11. Juan solicitó el 29/10 hacer
commit, push y la PR de esta entrega. La integración en main queda condicionada
a la revisión y al funcionamiento de la demo completa; la aprobación de estos
tests no equivale a una fusión de PR.
