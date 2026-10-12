"""Datos sintéticos; solo permite una base llamada panel_regression."""
import os

from sqlalchemy import create_engine, text

from app.security import hash_password

COMPANY_ID = '11111111-1111-1111-1111-111111111111'
USER_ID = '22222222-2222-2222-2222-222222222222'
CLIENT_ID = '33333333-3333-3333-3333-333333333333'
OPERATOR_ID = '44444444-4444-4444-4444-444444444444'
OTHER_COMPANY_ID = '66666666-6666-6666-6666-666666666666'
OTHER_CLIENT_ID = '77777777-7777-7777-7777-777777777777'
EMAIL = 'juan@panel.test'
PASSWORD = 'PanelDemo123!'
PASSWORD_HASH = hash_password(PASSWORD)


def test_engine():
    url = os.environ['PANEL_TEST_DATABASE_URL']
    engine = create_engine(url)
    if engine.url.database != 'panel_regression':
        engine.dispose()
        raise RuntimeError('La prueba solo admite la base aislada panel_regression')
    return engine


def seed(db):
    if db.execute(text('SELECT current_database()')).scalar_one() != 'panel_regression':
        raise RuntimeError('No se permite sembrar datos en una base de trabajo')
    db.execute(text("INSERT INTO empresas(id, nombre) VALUES (:id, 'Panel QA'), (:other, 'Otra empresa QA')"),
               dict(id=COMPANY_ID, other=OTHER_COMPANY_ID))
    db.execute(text("""INSERT INTO usuarios(id, empresa_id, nombre, email, password_hash, rol)
                       VALUES (:id, :company, 'Juan QA', :email, :password, 'admin')"""),
               dict(id=USER_ID, company=COMPANY_ID, email=EMAIL, password=PASSWORD_HASH))
    db.execute(text("""INSERT INTO operadores(id, empresa_id, nombre, email, password_hash)
                       VALUES (:id, :company, 'Operador QA', 'operador@panel.test', :password)"""),
               dict(id=OPERATOR_ID, company=COMPANY_ID, password=PASSWORD_HASH))
    db.execute(text("""INSERT INTO clientes(id, empresa_id, nombre, telefono_whatsapp, direccion, ubicacion)
                       VALUES (:id, :company, 'Cliente WhatsApp QA', '+00000000001', NULL, NULL),
                              (:other, :other_company, 'Cliente externo QA', '+00000000002', NULL, NULL)"""),
               dict(id=CLIENT_ID, company=COMPANY_ID, other=OTHER_CLIENT_ID, other_company=OTHER_COMPANY_ID))


if __name__ == '__main__':
    engine = test_engine()
    with engine.begin() as db:
        seed(db)
    engine.dispose()
    print('Datos sintéticos preparados en panel_regression; ninguna base de trabajo modificada.')
