import os
from datetime import timedelta

class Config:
    # Basic Flask Config
    SECRET_KEY = os.getenv('SECRET_KEY', 'ufsOrYXqhAM2Uo5TOdfWE6SHRWRrNCcliNEMv4MXApI')
    SESSION_COOKIE_NAME = 'attendance_session'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    
    # Database Config
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///attendance.db')
    if SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace("postgres://", "postgresql://", 1)
    
    # Security Config
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # CORS Settings
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*').split(',')
    
    # Rate Limiting
    RATELIMIT_DEFAULT = "100 per minute"
    RATELIMIT_STORAGE_URL = os.getenv('REDIS_URL', 'memory://')
    
    # QR Code Settings
    QR_CODE_EXPIRY = timedelta(hours=24)
    MAX_QR_USES = 1000
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER = 'static/uploads'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
class DevelopmentConfig(Config):
    DEBUG = True
    DEVELOPMENT = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///attendance.db'
    
class ProductionConfig(Config):
    DEBUG = False
    DEVELOPMENT = False
    SESSION_COOKIE_SECURE = True
    PERMANENT_SESSION_LIFETIME = timedelta(hours=12)
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith('postgres://'):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('postgres://', 'postgresql://', 1)
    
class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
