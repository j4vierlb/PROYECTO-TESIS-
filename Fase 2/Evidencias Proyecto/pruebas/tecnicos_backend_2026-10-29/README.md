# Evidencia: gestión de técnicos desde el panel (backend) — 29/10/2026

Entrega preparada en la rama `pedro`, actualizada con `main`. Corresponde solo
a la parte del backend (PR 1). El panel (PR 2) se hará después de la fusión.

Las pruebas se realizaron en un PostgreSQL/PostGIS 16-3.4 aislado, levantado
solo para esta prueba (contenedor `killbichos-tecnicos-test`, bases
`panel_regression` y `croquis_regression` creadas con el `schema.sql` nuevo).
No se tocó la base de trabajo ni el `.env`. Cada prueba se deshace con rollback.

## Resultados verificados

- **Backend: 251/251**, sin errores ni omisiones. Incluye las **9 pruebas
  nuevas** de técnicos. Se ejecutó en un contenedor `python:3.12-slim` con
  Node instalado, porque varias pruebas del panel llaman a `node` para usar
  la misma utilidad del frontend.
  Evidencia: [backend_regression.log](backend_regression.log).
- Ejecución aparte del módulo nuevo: **9/9**.
  Evidencia: [backend_tecnicos.log](backend_tecnicos.log).
- Migración `migracion_sesion_tecnicos.sql` aplicada dos veces sobre una base
  creada con el `schema.sql` anterior (el de `origin/main`) y un técnico
  sintético: la columna se agrega con valor 0, la segunda vez no hace nada y
  el técnico conserva su hash y su estado.
  Evidencia: [migracion.log](migracion.log).

## Cobertura nueva (`backend/tests/test_operadores_panel.py`)

- Crear técnico: 201, respuesta sin la clave, correo normalizado a
  minúsculas, nombre sin espacios sobrantes, clave guardada como hash bcrypt
  y el técnico nuevo puede iniciar sesión y ver sus visitas.
- Teléfono opcional; un teléfono en blanco se guarda como nulo.
- Validaciones: clave menor a 12 o mayor a 72 caracteres, más de 72 bytes
  UTF-8, carácter nulo, correo inválido y nombre vacío responden 422.
- Correo repetido responde 409, tanto si está en `operadores` (de esta u otra
  empresa, con otras mayúsculas) como en `usuarios` (admin o coordinador).
- Otra empresa: su técnico no aparece en la lista y editarlo responde 404
  sin modificarlo.
- Desactivar: el técnico ya no puede iniciar sesión, su token deja de servir,
  desaparece de la lista normal y aparece con `incluir_inactivos=true`. La
  fila no se borra. Al reactivarlo puede volver a entrar.
- Cambio de clave: el access y el refresh token anteriores dejan de servir,
  la clave antigua es rechazada y la nueva funciona.
- Editar nombre y borrar el teléfono no cambia la clave. Enviar `null` en
  nombre, activo o clave responde 422.
- Permisos: un técnico recibe 403 en los cuatro usos; un coordinador puede
  ver la lista normal (los desplegables del panel la necesitan) pero recibe
  403 al pedir inactivos, crear o editar. Sin sesión responde 401.

## Pendiente antes de desplegar

Una base creada antes de este cambio necesita la migración, porque el login
ahora lee `session_version` de `operadores`:

```bash
docker compose exec -T db psql -U killbichos -d killbichos < "Fase 2/Evidencias Proyecto/database/migracion_sesion_tecnicos.sql"
```

En una base nueva no hace falta: la columna ya viene en `schema.sql`.
