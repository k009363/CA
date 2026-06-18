from flask import Flask
from flask_cors import CORS
from extensions import mongo
from config import Config


def create_app():
    app = Flask(__name__, template_folder="templates")
    app.config.from_object(Config)

    CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)
    mongo.init_app(app)

    # Ensure indexes and default settings document exist
    with app.app_context():
        mongo.db.users.create_index("phone", unique=True)
        mongo.db.chats.create_index("participants")
        mongo.db.messages.create_index([("chat_id", 1), ("created_at", 1)])
        # Ensure app_settings document exists
        from utils.settings_helper import get_settings
        get_settings()

    from routes.auth import auth_bp
    from routes.chat import chat_bp
    from routes.messages import messages_bp
    from routes.files import files_bp
    from routes.admin import admin_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(chat_bp, url_prefix="/api/chats")
    app.register_blueprint(messages_bp, url_prefix="/api/messages")
    app.register_blueprint(files_bp, url_prefix="/api/files")
    # Admin UI served at /admin; admin API at /admin/api/*
    app.register_blueprint(admin_bp, url_prefix="/admin")

    return app


if __name__ == "__main__":
    application = create_app()
    application.run(debug=True, port=5000)
