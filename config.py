import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'uma-chave-secreta-muito-forte'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///torqview.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECURITY_PASSWORD_SALT = os.environ.get('SECURITY_PASSWORD_SALT') or 'salto-seguro'
    
    # Configurações de segurança
    SECURITY_PASSWORD_HASH = 'bcrypt'
    SECURITY_PASSWORD_COMPLEXITY_CHECKER = 'zxcvbn'
    SECURITY_REGISTERABLE = True
    SECURITY_SEND_REGISTER_EMAIL = False
    SECURITY_USERNAME_ENABLE = True
    SECURITY_USERNAME_REQUIRED = True