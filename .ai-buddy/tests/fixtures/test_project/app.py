#!/usr/bin/env python3
"""Main application entry point."""

from flask import Flask, jsonify
from config.settings import Config
from src.auth import auth_bp
from src.models import db

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    @app.route('/')
    def index():
        return jsonify({
            'message': 'Welcome to Test API',
            'version': '1.0.0'
        })
    
    @app.route('/health')
    def health():
        return jsonify({'status': 'healthy'})
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)