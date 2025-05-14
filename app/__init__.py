# Initialize app package
from flask import Flask
from app.routes.admin_settings import admin_settings

def create_app():
    app = Flask(__name__)
    app.register_blueprint(admin_settings)