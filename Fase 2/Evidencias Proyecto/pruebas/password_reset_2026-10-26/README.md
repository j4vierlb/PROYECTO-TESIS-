# Evidencia: recuperación de contraseña del panel — 26/10/2026

Entrega preparada en `juan`. Las pruebas de este corte se realizaron en bases
aisladas, sin modificar el `.env` ni las contraseñas de trabajo. Posteriormente
se creó una cuenta personal de administrador en la base local por autorización
del usuario, sin alterar la cuenta compartida; ese registro no se exporta a Git.
SMTP está simulado; no se enviaron correos reales. La recuperación todavía no
está desplegada en el backend de trabajo.

## Resultados verificados

- **Backend: 176/176**, sin errores ni omisiones en la ejecución final.
  Incluye **20 pruebas nuevas** de recuperación (no sumar de nuevo).
  Evidencia: [backend_regression.log](backend_regression.log).
- Ejecución adicional del módulo nuevo: **20/20**.
  Evidencia: [backend_reset.log](backend_reset.log).
- **Frontend: 107/107**, incluidas **9 nuevas** del flujo de recuperación.
  Evidencia: [frontend.log](frontend.log).
- Compilación de producción del panel: correcta.
  Evidencia: [frontend_build.log](frontend_build.log).
- Migración aplicada dos veces a una copia del esquema anterior con una cuenta
  sintética: cuenta y hash conservados, versión inicial 0 y ambas tablas creadas.
  También se comprobó crear una base desde el `schema.sql` nuevo.
  Evidencia: [migration.log](migration.log), resultado final de las verificaciones.

Total de la regresión final: **283 pruebas**, no 303. Las 20 del módulo nuevo
ya están incluidas entre las 176 del backend. Las pruebas y la compilación
no equivalen a una prueba de entrega SMTP real.

## Cobertura nueva

Backend (`backend/tests/test_password_reset.py`):

- Cambio efectivo de clave con login antiguo rechazado y nuevo aceptado.
- Tokens aleatorios guardados únicamente como hash, vigencia de 15 minutos.
- Rechazo de enlace vencido, alterado, usado o de cuenta desactivada.
- Canje de un enlace invalida todos los enlaces previos de la misma cuenta.
- **Dos conexiones concurrentes** canjeando el mismo token: exactamente una
  obtiene éxito; la otra es rechazada. Se usa PostgreSQL real, no un mock.
- Invalidación de access/refresh antiguos, incluidos JWT anteriores sin versión;
  acceso y renovación nuevos siguen funcionando.
- Recuperación de coordinador conserva su rol.
- Cuenta inexistente, inactiva y de operador móvil: mismo mensaje neutro, sin envío.
- Normalización de correo; enlace usa la URL configurada y no el Host del request.
- Validación de longitud de contraseña, bytes UTF-8, carácter nulo y tokens.
- Límites persistentes por correo y por IP; recuperación del cupo tras vencimiento.
- Servicio deshabilitado: 503 para todas las cuentas.
- Configuración exige TLS SMTP y HTTPS excepto loopback; transporte SMTP
  simulado verifica STARTTLS y autenticación. Error de envío no registra secretos.

Frontend (`frontend/tests/password-recovery.test.jsx`):

- Acceso a recuperación desde el login y solicitud con correo, no contraseña.
- Apertura del enlace aun si existía una sesión; fragmento retirado del historial.
- Confirmación coincidente y límite de bytes UTF-8 antes de enviar.
- Canje por POST sin Authorization ni token en la URL de la API.
- Regreso al login sin autoautenticación ni token persistido.
- Mensaje de enlace vencido, límite de intentos y servicio no habilitado.
- Controles bloqueados durante el envío, sin duplicar solicitudes.

## Entorno y reproducibilidad

Backend en la imagen Docker existente (Python 3.12 y requirements del backend),
montando el código local en solo lectura. PostgreSQL/PostGIS 16/3.4 dedicado:
`killbichos-password-reset-qa-20261026`, **sin puertos publicados y sin red externa**.
Bases `panel_regression` y `croquis_regression` para las pruebas; transacciones
con rollback y datos sintéticos. Una tercera base se usó para la migración antigua.
El test de concurrencia usa UUID propios, commit para compartir entre conexiones
y limpieza de esas filas exclusivamente.

La regresión histórica del panel ejecuta también `panel-utils.js`: se montó un
binario Linux de Node **22.23.4**, descargado de nodejs.org y verificado contra
su SHASUMS256. La primera ejecución no tenía Node y falló por esa dependencia;
se resolvió el entorno y se repitió toda la suite. No se alteraron esos tests
para hacerlos pasar. El warning de deprecación de `datetime.utcnow()` proviene
de python-jose existente y no impidió los resultados.

Desde el backend, en un entorno con Python, dependencias y Node disponibles,
preparar ambas bases aisladas con el esquema y migraciones. Configurar
`PANEL_TEST_DATABASE_URL` y `CROQUIS_TEST_DATABASE_URL` hacia sus bases respectivas
(nunca a `killbichos` ni a una base de trabajo) y ejecutar:

```text
python -m unittest discover -s tests -v
python -m unittest discover -s tests -p test_password_reset.py -v
```

Desde el frontend:

```text
npm test -- --reporter=dot
npm run build
```

## Pendientes de habilitación (no son pruebas aprobadas)

1. Confirmar con Javier proveedor SMTP, remitente y URL del panel; credenciales
   solo en `.env` privado.
2. Aplicar migración **antes** del backend nuevo en el entorno del equipo.
3. Configurar correo, activar recuperación y reconstruir backend/panel.
4. Probar recepción y uso del enlace desde un buzón real controlado; validar
   HTTPS, spam/entregabilidad y cierre de sesiones en navegadores reales.

Guía completa: [recuperacion_password_panel.md](../../backend/docs/recuperacion_password_panel.md).
