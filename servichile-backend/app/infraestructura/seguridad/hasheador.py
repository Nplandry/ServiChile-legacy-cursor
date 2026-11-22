from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

class HasheadorArgon2:
    def __init__(self) -> None:
        self._argon2 = PasswordHasher()
        self._hash_ficticio = self._argon2.hash("servichile-dummy-password")

    def hashear(self, contrasena: str) -> str:
        return self._argon2.hash(contrasena)

    def verificar(self, hash_contrasena: str | None, contrasena: str) -> bool:
        try:
            self._argon2.verify(hash_contrasena or self._hash_ficticio, contrasena)
        except (VerifyMismatchError, InvalidHashError):
            return False
        return bool(hash_contrasena)
