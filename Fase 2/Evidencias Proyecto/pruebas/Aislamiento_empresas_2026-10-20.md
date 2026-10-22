# Verificación del aislamiento entre empresas

**Actualización tras el PR #14: 30/30 casos aprobados.** Ver
`Verificacion_PR14_2026-10-20.md` y
`resultados_aislamiento_empresas_pr14_2026-10-20.json`. El contenido siguiente
conserva el hallazgo y la ejecución anteriores al arreglo; no describe el
estado actual del código integrado en `7f635f9`.

Fecha: 20 de octubre de 2026. Rama: `juan`. HEAD y origin/main revisados en
`78fe755`. Se ejecutó `git fetch origin` antes de probar; la corrección de
ensure_visit_access no estaba integrada en main al momento de esta ejecución.

## Resultado

**No aprobado: 30 pruebas ejecutadas, 22 aprobadas y 8 fallidas, sin errores
de ejecución ni omisiones.** Los ocho fallos corresponden a respuestas 200
con el recurso ajeno efectivamente devuelto, donde se esperaba rechazo 403
o 404. No se deben presentar las 169 pruebas históricas como cobertura de
esta comprobación nueva.

| Recurso | Misma empresa | Otra empresa | Sin token |
| --- | --- | --- | --- |
| GET /visitas/{id} | 200, correcto | 200 con la visita ajena, falla | 401, correcto |
| GET /croquis/{visita_id} | 200, correcto | 200 con el croquis ajeno, falla | 401, correcto |
| GET /dispositivos-trampa/{id}/foto | 200 con foto, correcto | 403, correcto | 401, correcto |

Se verificaron admin y coordinador de A y B, contra recursos de ambas empresas:
24 casos autenticados, más 6 sin token. Hay 4 fallas de visitas y 4 de croquis.
El acceso a recursos propios permite descartar que los rechazos de fotos sean
causados simplemente por un recurso inexistente o una sesión inválida.

## Entorno y evidencia

La suite usa FastAPI TestClient, login real y JWT emitido por la aplicación,
consultas SQL y PostgreSQL/PostGIS reales. Solo se sustituye la conexión de
base por una conexión aislada; no se simulan respuestas ni se altera la
autorización. Las fotos y todos los registros son sintéticos.

Se utilizó el contenedor temporal `killbichos-tenant-tests-20261020`, con base
`croquis_regression`, inicializada con `schema.sql` y
`migracion_croquis_terreno.sql`. Cada prueba se ejecuta dentro de una
transacción con rollback; las fotos viven en una carpeta temporal por caso.
No se consultaron registros de clientes reales ni se modificó la base de
trabajo. La comprobación de solo lectura conservó sus 2 clientes y 1 visita.

- Suite: `backend/tests/test_company_access_postgis.py`.
- Resultado detallado: `resultados_aislamiento_empresas_2026-10-20.json`.
- El JSON registra rol, empresa de origen/destino, endpoint, HTTP esperado y
  obtenido y si retornó el recurso ajeno. No incluye tokens, claves ni las
  respuestas completas.

Los 30 casos se repitieron para registrar explícitamente la identidad del
recurso retornado, además del código HTTP. La repetición no se suma como
otros 30 casos distintos.

## Causa observada y condición de cierre

`ensure_visit_access` solo restringe al rol operador; admin y coordinador no
tienen comparación de empresa en esa función. `fetch_visit` busca por ID y
su selección interna tampoco incluye empresa_id. Ambos endpoints consultados
reutilizan ese control. Las fotos usan ensure_device_access, que sí compara
la empresa y por eso sus rechazos funcionan.

La corrección funcional sigue a cargo de Javier. No se modificaron
`dependencies.py`, `repositories.py` ni los routers de visitas/croquis/fotos.
Estas pruebas deben pasar después de integrar su corrección. La aceptación
exige mantener los 12 accesos propios en 200, rechazar los 12 accesos ajenos
con 403/404 y mantener los 6 sin token en 401.

**No liberar el visor como seguro entre empresas mientras esta suite falle.**
La prueba no evalúa PATCH, otros endpoints, el despliegue remoto ni equivale
a una auditoría completa. No se corrige ocultando datos solo en el frontend.

## Reproducción

Desde la carpeta backend, con una base exclusivamente de pruebas llamada
`croquis_regression`, inicializada con el esquema y la migración mencionados:

```powershell
$env:CROQUIS_TEST_DATABASE_URL = '<URL de la base aislada croquis_regression>'
python -B -m unittest discover -s tests -p test_company_access_postgis.py -v
```

Si no se define la variable, los casos se omiten; no considerar esa ejecución
como validación aprobada. Con el código probado, el comando termina con ocho
fallas de aserción. No se marcaron como expectedFailure ni se flexibilizó la
expectativa de rechazo para ocultar el problema.

El contenedor temporal de esta suite se eliminó tras registrar resultados y
comprobar los rollbacks. Se conservaron la base de trabajo y el QA del panel.
La actualización posterior de los 11 Word conserva este hallazgo como
historial y registra su cierre con 30/30 tras PR #14 y el mapa real aprobado.
La revisión visual de los Word continúa pendiente.
