-- Ejecutar SOLO contra la base desechable del entorno QA Android.
DO $$ BEGIN
  IF current_database() <> 'android_regression' THEN
    RAISE EXCEPTION 'Este fixture solo admite android_regression';
  END IF;
END $$;

INSERT INTO visitas(id,empresa_id,cliente_id,operador_id,fecha_hora,estado,origen_agendamiento)
VALUES ('99999999-9999-4999-8999-999999999999',
 '11111111-1111-1111-1111-111111111111',
 '44444444-4444-4444-4444-444444444444',
 '33333333-3333-3333-3333-333333333333',
 ((now() AT TIME ZONE 'America/Santiago')::date + interval '1 day 10 hours') AT TIME ZONE 'America/Santiago',
 'agendada','manual');
INSERT INTO empresas(id,nombre) VALUES ('bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb','Empresa externa QA Android');
INSERT INTO usuarios(id,empresa_id,nombre,email,password_hash,rol)
SELECT 'cccccccc-cccc-4ccc-8ccc-cccccccccccc','bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
 'Admin externo QA','externo@android.test',password_hash,'admin'
FROM operadores WHERE id='33333333-3333-3333-3333-333333333333';
