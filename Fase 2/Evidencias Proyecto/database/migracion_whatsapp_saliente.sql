-- =====================================================================
-- Migración: mensajes de WhatsApp enviados por el sistema
-- ---------------------------------------------------------------------
-- 1. Bandeja del panel: un operador puede tomar una conversación
--    (atendida_por_humano) y escribirle al cliente (emisor 'operador').
--    Mientras la conversación está tomada, la IA no responde, salvo que el
--    operador lleve WHATSAPP_OPERADOR_MAX_HORAS sin actividad
--    (atendida_por_humano_desde y sus mensajes).
-- 2. Estado de entrega: cada mensaje enviado al cliente guarda lo que
--    informa Twilio (queued, sent, delivered, read, failed, undelivered).
-- 3. Recordatorio del día anterior: recordatorio_enviado_at evita que una
--    visita reciba dos recordatorios.
--
-- Se puede ejecutar más de una vez sin problema (IF NOT EXISTS).
-- Uso en una base que ya existe:
--   docker compose exec -T db psql -U killbichos -d killbichos < "Fase 2/Evidencias Proyecto/database/migracion_whatsapp_saliente.sql"
-- =====================================================================

ALTER TABLE conversaciones_whatsapp
    ADD COLUMN IF NOT EXISTS atendida_por_humano BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE conversaciones_whatsapp
    ADD COLUMN IF NOT EXISTS atendida_por_humano_desde TIMESTAMPTZ;

ALTER TABLE mensajes_whatsapp DROP CONSTRAINT IF EXISTS mensajes_whatsapp_emisor_check;
ALTER TABLE mensajes_whatsapp ADD CONSTRAINT mensajes_whatsapp_emisor_check
    CHECK (emisor IN ('cliente', 'agente_ia', 'sistema', 'operador'));

ALTER TABLE mensajes_whatsapp ADD COLUMN IF NOT EXISTS estado_entrega VARCHAR(20);
ALTER TABLE mensajes_whatsapp ADD COLUMN IF NOT EXISTS error_entrega TEXT;

ALTER TABLE visitas ADD COLUMN IF NOT EXISTS recordatorio_enviado_at TIMESTAMPTZ;
