"""La clave de los tokens de ejemplo o muy corta se detecta para avisar en el log."""
import unittest

from app.config import jwt_secret_inseguro


class JwtSecretTest(unittest.TestCase):
    def test_las_claves_de_ejemplo_son_inseguras(self):
        self.assertTrue(jwt_secret_inseguro('desarrollo-cambia-esta-clave'))
        self.assertTrue(jwt_secret_inseguro('REEMPLAZAR_CON_UN_SECRETO_ALEATORIO'))

    def test_una_clave_corta_es_insegura(self):
        self.assertTrue(jwt_secret_inseguro('abc123'))
        self.assertTrue(jwt_secret_inseguro('a' * 31))

    def test_una_clave_aleatoria_larga_es_segura(self):
        self.assertFalse(jwt_secret_inseguro('a3f9c2d84b7e1056a3f9c2d84b7e1056'))
        self.assertFalse(jwt_secret_inseguro('x' * 64))


if __name__ == '__main__':
    unittest.main()
