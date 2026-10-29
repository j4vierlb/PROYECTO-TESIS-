# Portada pública: borrador histórico — 28/10/2026

Esta carpeta conserva el primer avance de la portada, cuando aún no se habían
confirmado los horarios ni los datos del Sandbox. Las capturas muestran ese
estado anterior y no describen la configuración vigente.

El resultado final, el QR configurado, el horario confirmado, las pruebas y
capturas actuales están en el [registro del 29/10](../portada_publica_2026-10-29/README.md).

## Comprobaciones de este borrador

- `frontend.log`: 158 pruebas aprobadas en el avance inicial.
- `frontend_integrado_main26.log`: 160 aprobadas después de integrar los dos
  casos de direcciones fuera de Santiago. Estos contadores no se suman entre sí
  ni al resultado vigente de 161 pruebas.
- `frontend_build.log` y `frontend_build_integrado_main26.log`: compilaciones
  correctas de los cortes correspondientes.
- `npm_ci_integrado_main26.log`: restauración de dependencias del borrador.
- `npm_audit.json`: dos avisos de seguridad en Vite y Undici ya presentes en
  el lock anterior a la portada. No proceden de qrcode/jsqr ni se presentan
  como resueltos por esta entrega.
- `vista_responsive.html`: auxiliar manual para revisar 390 y 320 píxeles en
  iframes de escritorio. Se copia temporalmente al `dist` de QA; no se incluye
  en el producto ni acredita pruebas en un teléfono real.

No se realizaron cambios en el backend o la base de datos durante este borrador.
