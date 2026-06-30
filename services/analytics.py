"""Query building and aggregation, shared by the dashboard, activity page,
reports, and exports so filtering/summarising logic lives in exactly one place.
"""
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlalchemy import func

from extensions import db
from models import Expense
from constants import CATEGORIES
from utils.helpers import parse_date

# Columns the activity table may be sorted by -> actual model columns.
SORTABLE = {
    "date": Expense.date,
    "amount": Expense.amount,
    "category": Expense.category,
}


@dataclass
class ExpenseFilter:
    """Normalised, validated filter parameters parsed from the query string."""
    start: date | None = None
    end: date | None = None
    category: str | None = None
    search: str = ""
    sort: str = "date"
    direction: str = "desc"

    @classmethod
    def from_args(cls, args) -> "ExpenseFilter":
        start = parse_date(args.get("start"))
        end = parse_date(args.get("end"))
        # Guard against an inverted range (swap rather than return nothing).
        if start and end and start > end:
            start, end = end, start

        category = (args.get("category") or "").strip() or None
        if category not in CATEGORIES:
            category = None

        sort = args.get("sort", "date")
        if sort not in SORTABLE:
            sort = "date"
        direction = args.get("dir", "desc")
        if direction not in ("asc", "desc"):
            direction = "desc"

        return cls(
            start=start,
            end=end,
            category=category,
            search=(args.get("q") or "").strip(),
            sort=sort,
            direction=direction,
        )

    def is_active(self) -> bool:
        return bool(self.start or self.end or self.category or self.search)

    def query_params(self) -> dict:
        """Re-usable params for url_for (preserves filters across pagination)."""
        p = {}
        if self.start:
            p["start"] = self.start.isoformat()
        if self.end:
            p["end"] = self.end.isoformat()
        if self.category:
            p["category"] = self.category
        if self.search:
            p["q"] = self.search
        if self.sort != "date":
            p["sort"] = self.sort
        if self.direction != "desc":
            p["dir"] = self.direction
        return p


def build_query(f: ExpenseFilter):
    """Return a SQLAlchemy query for `Expense` with the filter applied + sorted."""
    q = Expense.query
    if f.start:
        q = q.filter(Expense.date >= f.start)
    if f.end:
        q = q.filter(Expense.date <= f.end)
    if f.category:
        q = q.filter(Expense.category == f.category)
    if f.search:
        like = f"%{f.search}%"
        q = q.filter(Expense.note.ilike(like))

    col = SORTABLE[f.sort]
    q = q.order_by(col.asc() if f.direction == "asc" else col.desc())
    # Stable tiebreaker so pagination is deterministic.
    return q.order_by(Expense.id.desc())


def summarise(f: ExpenseFilter) -> dict:
    """Totals for the current filter: overall sum, count, average, per-category."""
    base = build_query(f).order_by(None)  # drop ORDER BY for aggregates
    subq = base.subquery()

    total = db.session.query(
        func.coalesce(func.sum(subq.c.amount), 0)
    ).scalar()
    count = db.session.query(func.count(subq.c.id)).scalar()

    cat_rows = dict(
        db.session.query(subq.c.category, func.sum(subq.c.amount))
        .group_by(subq.c.category)
        .all()
    )
    category_totals = [
        {"category": c, "total": Decimal(str(cat_rows.get(c, 0) or 0))}
        for c in CATEGORIES
    ]

    total = Decimal(str(total or 0))
    avg = (total / count) if count else Decimal("0")
    return {
        "total": total,
        "count": count,
        "average": avg,
        "category_totals": category_totals,
    }


def category_breakdown() -> list[dict]:
    """Unfiltered per-category totals, in CATEGORIES order (dashboard doughnut)."""
    rows = dict(
        db.session.query(Expense.category, func.sum(Expense.amount))
        .group_by(Expense.category)
        .all()
    )
    return [
        {"category": c, "total": Decimal(str(rows.get(c, 0) or 0))}
        for c in CATEGORIES
    ]


def monthly_breakdown(months: int = 12) -> list[dict]:
    """Total expense per calendar month for the last `months` months.

    Done in Python (not SQL date-truncation) so the same code works on both
    SQLite and PostgreSQL without dialect-specific functions.
    """
    today = date.today()
    # Build the ordered list of (year, month) buckets, oldest first.
    buckets: list[tuple[int, int]] = []
    y, m = today.year, today.month
    for _ in range(months):
        buckets.append((y, m))
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    buckets.reverse()

    earliest = date(buckets[0][0], buckets[0][1], 1)
    rows = (
        db.session.query(Expense.date, Expense.amount)
        .filter(Expense.date >= earliest)
        .all()
    )
    totals: dict[tuple[int, int], Decimal] = {b: Decimal("0") for b in buckets}
    for d, amt in rows:
        key = (d.year, d.month)
        if key in totals:
            totals[key] += Decimal(str(amt))

    labels_short = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return [
        {
            "label": f"{labels_short[mo - 1]} {yr}",
            "year": yr,
            "month": mo,
            "total": totals[(yr, mo)],
        }
        for (yr, mo) in buckets
    ]
