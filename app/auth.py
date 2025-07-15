from PyQt5.QtWidgets import QMessageBox
from .settings import SENHA_ADMIN

def verificar_admin(senha_input):
    if senha_input == SENHA_ADMIN:
        return True
    return False