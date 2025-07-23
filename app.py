from flask import Flask
from flask_wtf import CSRFProtect
import os
from config import Config
from extensions import db, login_manager, migrate
from utils.filters import register_filters

def create_app():
    # Create and configure the app
    app = Flask(__name__)
    app.config.from_object(Config)
    csrf = CSRFProtect(app)

    @app.template_filter('format_datetime')
    def format_datetime(value, format='short'):
        if format == 'short':
            return value.strftime('%Y-%m-%d %H:%M')
        elif format == 'long':
            return value.strftime('%A, %d %B %Y at %I:%M%p')
        return value.strftime('%Y-%m-%d')

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)  # Initialize Flask-Migrate
    
    # Register custom template filters
    register_filters(app)
    
    # Import User model here to avoid circular imports
    from models.user import User
    
    # Configure login manager
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.journal import journal_bp
    from routes.repository import repo_bp as repository_bp

    app.register_blueprint(auth_bp, url_prefix='/')
    app.register_blueprint(dashboard_bp, url_prefix='/')
    app.register_blueprint(journal_bp, url_prefix='/journal')
    app.register_blueprint(repository_bp, url_prefix='/repository')

    # Create database tables
    with app.app_context():
        db.create_all()

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
