"""Application configuration settings."""

import os
from datetime import timedelta

class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
    DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///app.db')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    
class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    TESTING = False
    
class TestingConfig(Config):
    """Testing configuration."""
    DEBUG = False
    TESTING = True
    DATABASE_URL = 'sqlite:///:memory:'
    
class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    TESTING = False