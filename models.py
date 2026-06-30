"""Database models."""
from datetime import datetime, date

from extensions import db


class Expense(db.Model):
    """A single expenditure record.

    `amount` is stored as Numeric to avoid binary floating-point rounding
    errors on money. `date` is the date the expense was incurred (chosen by the
    user); `created_at` is when the row was inserted (set automatically).
    """
    __tablename__ = "expense"

    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    category = db.Column(db.String(50), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    note = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"<Expense {self.id} {self.category} {self.amount}>"

    def to_dict(self):
        return {
            "id": self.id,
            "amount": float(self.amount),
            "category": self.category,
            "date": self.date.isoformat() if self.date else None,
            "note": self.note,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
