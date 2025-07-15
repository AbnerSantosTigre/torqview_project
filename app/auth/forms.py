from flask_security.forms import RegisterForm
from wtforms import StringField, validators

class ExtendedRegisterForm(RegisterForm):
    username = StringField('Username', [validators.DataRequired()])