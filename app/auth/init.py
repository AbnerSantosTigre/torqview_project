from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_security import Security, SQLAlchemyUserDatastore
from config import Config

db = SQLAlchemy()
bcrypt = Bcrypt()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    db.init_app(app)
    bcrypt.init_app(app)
    
    from app.auth.models import User, Role
    user_datastore = SQLAlchemyUserDatastore(db, User, Role)
    security = Security(app, user_datastore)
    
    with app.app_context():
        db.create_all()
        
        # Cria roles padrão se não existirem
        if not Role.query.first():
            user_datastore.create_role(name='user', description='Usuário comum')
            user_datastore.create_role(name='admin', description='Administrador')
            db.session.commit()
            
            # Cria admin padrão (altere as credenciais)
            if not User.query.first():
                admin_user = user_datastore.create_user(
                    username='admin',
                    email='admin@torqview.com',
                    password=bcrypt.generate_password_hash('admin123').decode('utf-8'),
                    active=True
                )
                user_datastore.add_role_to_user(admin_user, 'admin')
                db.session.commit()
    
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    return app