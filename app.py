"""Application factory and entrypoint for the School Expense Management System."""
import os
from datetime import datetime

from flask import Flask, render_template

from config import Config
from extensions import db
from utils.helpers import format_currency


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)

    # Import models so db.create_all()/migrations can see them.
    from models import Expense  # noqa: F401

    # Blueprints
    from auth.routes import auth_bp
    from expenses.routes import expenses_bp
    from reports.routes import reports_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(expenses_bp)
    app.register_blueprint(reports_bp)

    # Template globals / filters.
    app.jinja_env.filters["currency"] = format_currency

    @app.context_processor
    def inject_globals():
        return {"now": datetime.utcnow()}

    # Error handlers.
    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        db.session.rollback()  # never leave a broken session behind
        return render_template("errors/500.html"), 500

    # CLI helpers.
    @app.cli.command("init-db")
    def init_db_command():
        """Create all database tables."""
        db.create_all()
        print("Database tables created.")

    @app.cli.command("seed")
    def seed_command():
        """Create tables and insert sample expenses (development only)."""
        from seed import run_seed
        run_seed()

    return app


# Resolve config from env so production uses ProductionConfig.
_config_name = os.environ.get("FLASK_CONFIG", "default")
if _config_name == "production":
    from config import ProductionConfig as _Config
else:
    _Config = Config

app = create_app(_Config)


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
