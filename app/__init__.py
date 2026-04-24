from flask import Flask
from flask_login import LoginManager
from flask_migrate import Migrate
from config import config
from app.models import db, Usuario

login_manager = LoginManager()
migrate = Migrate()


def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Faça login para acessar esta página.'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        return Usuario.query.get(int(user_id))

    @app.context_processor
    def utility_processor():
        from datetime import date
        return dict(enumerate=enumerate, hoje_iso=date.today().isoformat())

    # Blueprints Consolidados
    from app.routes.auth import auth_bp
    from app.routes.agenda import agenda_bp
    from app.routes.clientes import clientes_bp
    from app.routes.mensalistas import mensalistas_bp
    from app.routes.financeiro import financeiro_bp
    from app.routes.ajustes import ajustes_bp
    from app.routes.usuarios import usuarios_bp  # <--- Nova Rota de Equipe

    app.register_blueprint(auth_bp)
    app.register_blueprint(agenda_bp)
    app.register_blueprint(clientes_bp)
    app.register_blueprint(mensalistas_bp)
    app.register_blueprint(financeiro_bp)
    app.register_blueprint(ajustes_bp)
    app.register_blueprint(usuarios_bp)          # <--- Registrado

    return app