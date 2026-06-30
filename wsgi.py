"""WSGI entrypoint for production servers (gunicorn).

    gunicorn wsgi:app

Tables are created on startup if they don't exist, so a fresh Render Postgres
database is usable immediately after the first deploy.
"""
from app import app
from extensions import db

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run()
