# backend/app/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_cors import CORS
from flask_bcrypt import Bcrypt

from config import app_config # Use the selected config (Dev/Prod)

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'api_auth.login' # Blueprint name . function name
# To handle cases where frontend expects JSON error for unauthorized
login_manager.login_message_category = 'danger' # Optional: category for flash messages if used
bcrypt = Bcrypt()
cors = CORS()

# User loader callback for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    # Import here to avoid circular imports
    from app.models.user import User
    return User.query.get(int(user_id))

def create_app(config_name='development'):
    app = Flask(__name__)
    # Correctly reference app_config loaded from config module
    # app.config.from_object(config.config_by_name[config_name]) # Original might be error-prone if config_name isn't exactly 'development' or 'production'
    app.config.from_object(app_config) # Use the already selected config object

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    # Allow frontend origin (adjust in production)
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

    # Register Blueprints
    # Import blueprints inside the factory function to avoid circular imports
    from .api.auth_routes import auth_bp
    from .api.user_routes import user_bp
    from .api.assistant_routes import assistant_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(user_bp, url_prefix='/api/users')
    app.register_blueprint(assistant_bp, url_prefix='/api/assistant')

    @app.route('/api/hello') # Example basic route
    def hello():
        return "Hello from Nexus Backend!"

    # Add error handler for unauthorized access if login_manager sends back non-JSON
    @login_manager.unauthorized_handler
    def unauthorized():
        # Return a JSON response appropriate for APIs
        return jsonify(error="Unauthorized access"), 401

    return app
