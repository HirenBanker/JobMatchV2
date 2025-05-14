# Initialize app package
try:
    from flask import Flask
    from app.routes.admin_settings import admin_settings
    
    def create_app():
        app = Flask(__name__)
        app.register_blueprint(admin_settings)
        return app
except ImportError:
    # Flask is not installed, provide a dummy create_app function
    def create_app():
        print("Warning: Flask is not installed. API routes will not be available.")
        return None