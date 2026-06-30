"""Small presentation helpers shared across routes and templates."""
from datetime import date, datetime
from decimal import Decimal


def format_currency(value) -> str:
    """Render a money value with a rupee sign and thousands separators.

    Accepts Decimal/float/int/None. None or invalid input renders as the
    zero amount rather than raising, so templates never blow up on bad data.
    """
    try:
        amount = Decimal(str(value or 0))
    except Exception:
        amount = Decimal("0")
    return f"₹{amount:,.2f}"


def parse_date(raw: str, default: date | None = None) -> date | None:
    """Parse a YYYY-MM-DD string, returning `default` on empty/invalid input."""
    if not raw:
        return default
    try:
        return datetime.strptime(raw.strip(), "%Y-%m-%d").date()
    except (ValueError, AttributeError):
        return default


def today_iso() -> str:
    return date.today().isoformat()
