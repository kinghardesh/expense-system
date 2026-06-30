"""Seed the database with sample expenses for development/testing.

Run with:  flask seed   (after `set FLASK_APP=app.py`)
Idempotent-ish: it only seeds when the table is empty, so re-running is safe.
"""
from datetime import date, timedelta
from decimal import Decimal
import random

from extensions import db
from models import Expense
from constants import CATEGORIES


SAMPLE_NOTES = {
    "Stationary": ["Notebooks", "Printer paper", "Markers & chalk"],
    "Transport": ["Bus fuel", "Field-trip van", "Vehicle maintenance"],
    "Event": ["Annual day", "Sports day", "Science exhibition"],
    "Salary": ["Teaching staff", "Support staff", "Guest lecturer"],
    "Other expenditure": ["Electricity bill", "Water bill", "Misc repairs"],
}


def run_seed(num=40):
    db.create_all()

    if Expense.query.first() is not None:
        print("Expenses already exist — skipping seed.")
        return

    today = date.today()
    rng = random.Random(42)  # deterministic sample data
    created = 0
    for _ in range(num):
        category = rng.choice(CATEGORIES)
        days_ago = rng.randint(0, 150)
        amount = Decimal(rng.randint(50, 25000)) + Decimal(
            f"0.{rng.randint(0, 99):02d}"
        )
        db.session.add(Expense(
            amount=amount,
            category=category,
            date=today - timedelta(days=days_ago),
            note=rng.choice(SAMPLE_NOTES[category]),
        ))
        created += 1

    db.session.commit()
    print(f"Seeded {created} sample expenses.")


if __name__ == "__main__":
    # Allow `python seed.py` directly.
    from app import app
    with app.app_context():
        run_seed()
