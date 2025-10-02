import os
from datetime import timedelta

class ProductionConfig:
    # Use PostgreSQL for production (you'll need to set up a database)
    # For now, we'll use a demo PostgreSQL database
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'taskflow-mindscape-production-key-2024'

    # You can use a free PostgreSQL database from:
    # - Supabase: https://supabase.com
    # - Neon: https://neon.tech
    # - Railway: https://railway.app
    # Or use Vercel Postgres

    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///tmp/taskflow.db'

    # Fix for SQLAlchemy compatibility
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace("postgres://", "postgresql://", 1)

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None