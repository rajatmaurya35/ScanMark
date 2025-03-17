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
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'postgresql://neondb_owner:npg_iaL8ckJzYN7X@ep-shy-smoke-a5mn2t1d-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require')
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 5,
        'max_overflow': 2,
        'pool_timeout': 30,
        'pool_recycle': 1800,
    }
    if SQLALCHEMY_DATABASE_URI:
        # Neon provides standard postgresql:// URLs
        if SQLALCHEMY_DATABASE_URI.startswith('postgres://'):
            SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('postgres://', 'postgresql://', 1)
        # Enable SSL mode for Neon
        if 'sslmode=' not in SQLALCHEMY_DATABASE_URI:
            SQLALCHEMY_DATABASE_URI += '?sslmode=require'
    
class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
