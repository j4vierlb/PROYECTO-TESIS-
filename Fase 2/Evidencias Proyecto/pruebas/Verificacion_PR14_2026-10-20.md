# Verificación del arreglo de permisos del PR 14

Fecha: 20 de octubre de 2026. Rama: `juan`. Base integrada: `7f635f9`, merge
del PR #14, con la corrección `6519d51` de Javier.

## Resultado actual

**205 pruebas aprobadas: 107 backend y 98 frontend, sin fallas, errores ni
omisiones.** Las 30 pruebas de aislamiento están incluidas en las 107 del
backend, no son adicionales al total de 205.

La suite que antes obtenía 22/30 ahora obtiene **30/30**. Los ocho accesos
ajenos a visitas y croquis que antes entregaban datos con HTTP 200 ahora se
rechazan con 403. CR-EXT-02 queda aprobado para el código y entorno probados.

| Control | Resultado |
| --- | --- |
| Admin y coordinador acceden a su empresa | 12 respuestas 200 con el recurso propio correcto |
| Admin y coordinador acceden a la otra empresa | 12 respuestas 403, sin devolver el recurso ajeno |
| Acceso sin token | 6 respuestas 401 |
| Sentidos de consulta | A hacia B y B hacia A |
| Regresión de Javier | 6 pruebas nuevas de test_acceso_empresa.py incluidas en el backend, con subcasos de roles, operadores, PATCH ajeno y recursos inexistentes |
| Frontend | 98 aprobadas; compilación de producción correcta |
| Docker backend | Reconstruido; health correcto y conexión con la base de trabajo validada |

## Integración sin pérdida de cambios locales

Se ejecutó `git fetch origin` y se actualizó `juan` mediante
`git merge --ff-only origin/main`. No se cambió de rama, no se creó una rama
nueva ni se generó un commit propio de merge. Se verificaron hashes SHA256:
los 58 archivos locales existentes conservaron exactamente su contenido y
el `.env` no cambió. Las evidencias y notas se actualizaron después de esa
verificación.

El PR agrega empresa_id a la selección interna de visitas y compara la
empresa antes de aplicar el control de asignación del operador. No se
reescribió esa corrección ni se modificó el contrato público para exponer
la empresa. El servidor QA también se reinició para cargar el código nuevo.

## Pruebas y evidencias

Las pruebas se ejecutaron contra FastAPI con login y JWT reales y dos bases
PostgreSQL/PostGIS aisladas: `panel_regression` y `croquis_regression`, en el
contenedor temporal `killbichos-pr14-tests-20261020`. No se usó la base de
trabajo para sembrar datos. Las transacciones se revirtieron por caso.

- `resultados_backend_pr14_2026-10-20.json`: 107 pruebas backend aprobadas.
- `resultados_frontend_pr14_2026-10-20.json`: 98 pruebas frontend aprobadas.
- `resultados_aislamiento_empresas_pr14_2026-10-20.json`: los 30 casos de aislamiento con códigos HTTP e identidad del recurso comprobada, sin JWT ni credenciales.

Se conservan el reporte y JSON anteriores con los ocho fallos como historial.
No se cambiaron las expectativas de las pruebas para aprobarlas ni se
marcaron casos como expectedFailure. La validación de Maps real del 20/10
se mantiene como prueba manual separada y no incrementa el conteo automatizado.

## Reproducción

Desde backend, con ambas bases aisladas inicializadas mediante schema.sql y
migracion_croquis_terreno.sql:

```powershell
$env:PANEL_TEST_DATABASE_URL = '<URL aislada de panel_regression>'
$env:CROQUIS_TEST_DATABASE_URL = '<URL aislada de croquis_regression>'
python -B -m unittest discover -s tests -v
```

Para repetir únicamente el control de acceso solicitado:

```powershell
python -B -m unittest discover -s tests -p test_company_access_postgis.py -v
```

Desde frontend: `npm test` y `npm run build`. La aprobación de las suites
PostGIS exige definir sus variables; una ejecución que omite casos no
equivale a este resultado.

## Cierre de esta verificación

Se comprobó que las bases de pruebas quedaron vacías después de los
rollbacks y se eliminó únicamente su contenedor temporal. Se conservaron
la base de trabajo, el QA del panel y sus datos. El backend Docker usa el
arreglo integrado. No se hizo staging, commit ni push de los cambios de Juan.

Los 11 Word se actualizaron al 20/10 con los resultados actuales de Maps y
permisos. Se comprobó contenido, coherencia e integridad de sus paquetes;
queda completar la revisión visual antes de considerarlos documentos finales,
porque el renderizador empaquetado no tiene LibreOffice disponible.
La prueba no equivale a una auditoría de seguridad exhaustiva ni acredita
un despliegue remoto distinto del entorno local probado.
