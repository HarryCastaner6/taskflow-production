import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from config_prod import ProductionConfig

app = create_app(ProductionConfig)

# Vercel expects a callable named 'app' or 'application'
# This is the WSGI application object
application = app