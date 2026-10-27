-- Ejecutar antes de desplegar el backend nuevo. Idempotente; no borra usuarios.
BEGIN;
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS session_version INTEGER NOT NULL DEFAULT 0;

CREATE TABLE IF NOT EXISTS password_reset_tokens (
    token_hash CHAR(64) PRIMARY KEY,
    usuario_id UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    session_version INTEGER NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS password_reset_expiry_idx ON password_reset_tokens(expires_at);

-- Contadores compartidos por todos los workers, incluso tras reiniciar la API.
-- Las claves son hashes con HMAC: no se guardan emails ni IP en esta tabla.
CREATE TABLE IF NOT EXISTS password_reset_limits (
    scope_hash CHAR(64) PRIMARY KEY,
    attempts INTEGER NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS password_reset_limits_expiry_idx ON password_reset_limits(expires_at);
COMMIT;
