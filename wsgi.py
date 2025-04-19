# This file is the entry point for Render
# It imports the Flask app from app.py

import os
import sys

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(__file__))

# Import the Flask app
from app import app

# This is what Gunicorn will import
if __name__ == "__main__":
    app.run()
