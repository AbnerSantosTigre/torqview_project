from hashlib import sha256
from .settings import ADMIN_HASH

def verificar_admin(senha_input):
    salt = "torqview_salt_secure" # Mesmo salt usado em settings.py
    input_hash = sha256((salt + senha_input).encode()).hexdigest()
    return input_hash == ADMIN_HASH