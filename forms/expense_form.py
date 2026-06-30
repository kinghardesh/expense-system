"""Server-side validation for the expense add/edit forms.

A tiny hand-rolled validator (no WTForms dependency). `validate_expense_form`
takes the raw request form dict and returns a `(cleaned, errors)` pair:

    cleaned : dict with typed values (Decimal amount, date object, str fields)
    errors  : dict mapping field name -> human-readable message

The route treats a non-empty `errors` dict as a failed submission and re-renders
the form with the user's input preserved.
"""
from datetime import datetime, date
from decimal import Decimal, InvalidOperation

from constants import CATEGORY_SET

MAX_AMOUNT = Decimal("99999999.99")  # fits Numeric(12, 2)
NOTE_MAX_LEN = 255


def validate_expense_form(form) -> tuple[dict, dict]:
    cleaned: dict = {}
    errors: dict = {}

    # --- amount -------------------------------------------------------------
    raw_amount = (form.get("amount") or "").strip().replace(",", "")
    if not raw_amount:
        errors["amount"] = "Amount is required."
    else:
        try:
            amount = Decimal(raw_amount).quantize(Decimal("0.01"))
            if amount <= 0:
                errors["amount"] = "Amount must be greater than zero."
            elif amount > MAX_AMOUNT:
                errors["amount"] = "Amount is too large."
            else:
                cleaned["amount"] = amount
        except (InvalidOperation, ValueError):
            errors["amount"] = "Amount must be a valid number."

    # --- category -----------------------------------------------------------
    category = (form.get("category") or "").strip()
    if not category:
        errors["category"] = "Please select a category."
    elif category not in CATEGORY_SET:
        errors["category"] = "Invalid category selected."
    else:
        cleaned["category"] = category

    # --- date ---------------------------------------------------------------
    raw_date = (form.get("date") or "").strip()
    if not raw_date:
        errors["date"] = "Date is required."
    else:
        try:
            parsed = datetime.strptime(raw_date, "%Y-%m-%d").date()
            if parsed > date.today():
                errors["date"] = "Date cannot be in the future."
            else:
                cleaned["date"] = parsed
        except ValueError:
            errors["date"] = "Date must be in YYYY-MM-DD format."

    # --- note (optional) ----------------------------------------------------
    note = (form.get("note") or "").strip()
    if len(note) > NOTE_MAX_LEN:
        errors["note"] = f"Note cannot exceed {NOTE_MAX_LEN} characters."
    else:
        cleaned["note"] = note or None

    return cleaned, errors
