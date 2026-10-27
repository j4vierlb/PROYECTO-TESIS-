# Integración de main en juan — PR #23 — 26/10/2026

Integración de `origin/main` en `juan`, sin crear ramas ni modificar `main`.
Padres del merge: entrega propia `19d7130` y main `52feff0`, que ya incorpora
las PR #21 (Android funcional) y #22 (WhatsApp saliente/bandeja).

## Resolución de los cuatro conflictos

- `backend/.env.example`: se conservan los comentarios de ejecución de main,
  el marcador seguro de JWT_SECRET y todas las variables de correo/WhatsApp.
  No se copia ningún secreto del `.env` privado.
- `backend/app/main.py`: importaciones de recuperación, conversaciones y
  recordatorios combinadas. Se conservan ambos routers y el lifespan que
  programa recordatorios; no se elimina ninguna funcionalidad de main.
- `frontend/src/main.jsx`: logo y recuperación se conservan junto con las
  tres vistas Agenda/Clientes/WhatsApp y el import de `chileDateTime`.
  El cuerpo de la bandeja, estados de entrega y acciones vienen de main.
- `frontend/src/styles.css`: paleta de marca más todas las clases de bandeja,
  mensajes y compositor. Los neutros y la selección de la bandeja usan las
  variables del tema; los estados semánticos se mantienen.

Los archivos de servicio `whatsapp_saliente.py` y routers `conversaciones.py`
y `whatsapp.py` conservan exactamente la versión de main: se comprobó que no
hay diferencias locales contra ese padre. No se resolvió aceptando un archivo
completo y descartando el otro.

## Resultados del código combinado

- **Backend: 210/210**, sin errores ni omisiones:
  [backend.log](backend.log). Incluye recuperación, sesiones, croquis, empresas,
  SQL real del panel y pruebas de WhatsApp saliente/bandeja de main.
- **Frontend: 122/122**: [frontend.log](frontend.log).
- Compilación web correcta: [frontend_build.log](frontend_build.log).
- **Flutter: 102/102**: [flutter_test.log](flutter_test.log).
- Análisis Flutter sin problemas: [flutter_analyze.log](flutter_analyze.log).

Los 176/113 de las evidencias anteriores son cortes previos a esta integración,
no se suman a los totales actuales. No se recompiló el APK en este paso porque
no cambió el código móvil con respecto al APK del corte visual anterior.

## Regresión nueva de la integración

`frontend/tests/merge-integration.test.jsx` añade cinco pruebas:

1. Logo y tres vistas presentes; bandeja muestra mensajes, fechas de Chile y
   estado de entrega sin realizar escrituras al abrir.
2. Composición y envío simulado de respuesta; se conserva estado «Enviado».
3. Tomar/devolver conversación y solicitar recordatorios manuales.
4. Cerrar sesión desde WhatsApp y abrir recuperación con correo y logo.
5. CSS combinado contiene los estilos de marca y bandeja, sin marcas de conflicto.

El navegador de pruebas usa respuestas sintéticas para estas interacciones:
ninguna de ellas contacta Twilio o un cliente real.

## Entorno y límites

PostgreSQL/PostGIS 16/3.4 en contenedor dedicado
`killbichos-pr23-merge-qa-20261026`, sin puertos publicados ni red externa.
Bases `panel_regression` y `croquis_regression` creadas desde schema y las
migraciones de Message SID, croquis, WhatsApp saliente y recuperación.
Se preservó la base de trabajo y la cuenta personal creada allí.
Preparación: [preparacion_bases.log](preparacion_bases.log).

El backend de pruebas usa la imagen existente con el código local montado en
solo lectura y Node Linux para las pruebas de utilidades del panel. Claves
OpenAI, Maps, Twilio y SMTP anuladas por variables de entorno; las llamadas
salientes están simuladas. No se enviaron mensajes ni correos reales.
Se detiene y elimina únicamente el contenedor de pruebas al finalizar, sin
eliminar volúmenes de trabajo.

No se desplegó ni se mezcló en main. SMTP y recepción real del enlace siguen
pendientes. Antes de desplegar, aplicar `migracion_password_reset.sql` y, si el
entorno aún no recibió PR #22, también `migracion_whatsapp_saliente.sql`.
No recrear la base ni borrar volúmenes. Continúan pendientes la rotación
coordinada del JWT_SECRET de ejemplo, la variante Wi-Fi del APK y la validación
manual en teléfono físico; no se presentan como resueltos por este merge.
