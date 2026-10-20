-- =====================================================================
-- Migración: croquis en terreno (agregar trampas y fotos desde la app)
-- ---------------------------------------------------------------------
-- 1. Cada trampa puede tener una foto de referencia, tomada por el técnico
--    al instalarla. Se guarda la ruta del archivo en el servidor (no la
--    imagen dentro de la base).
-- 2. Una visita tiene a lo más un croquis, y dentro de un croquis cada
--    código de trampa (T-01, T-02...) es único. Así, si la app manda dos
--    veces la misma petición, no se duplican croquis ni códigos.
--
-- Se puede ejecutar más de una vez sin problema (IF NOT EXISTS).
-- Uso en una base que ya existe:
--   docker compose exec -T db psql -U killbichos -d killbichos < "Fase 2/Evidencias Proyecto/database/migracion_croquis_terreno.sql"
-- =====================================================================

ALTER TABLE dispositivos_trampa ADD COLUMN IF NOT EXISTS foto_path TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS uq_croquis_visita
    ON croquis (visita_id) WHERE visita_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_dispositivos_croquis_codigo
    ON dispositivos_trampa (croquis_id, codigo);
