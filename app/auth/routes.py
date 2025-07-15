from flask import Blueprint, render_template, redirect, url_for, flash
from flask_security import login_required, current_user
from app.auth.forms import ExtendedRegisterForm

bp = Blueprint('auth', __name__)

@bp.route('/login')
def login():
    return render_template('auth/login.html')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    form = ExtendedRegisterForm()
    
    if form.validate_on_submit():
        # O Flask-Security cuida do registro automaticamente
        flash('Registro realizado com sucesso!', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html', form=form)

@bp.route('/profile')
@login_required
def profile():
    return render_template('auth/profile.html', user=current_user)