"""Shared Flask extensions, initialised in the application factory."""
from flask_sqlalchemy import SQLAlchemy

# Single shared SQLAlchemy instance. Bound to the app inside create_app().
db = SQLAlchemy()
