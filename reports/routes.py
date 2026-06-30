"""Reporting: monthly report, category report, expense statement, printable view.

All four share the same analytics layer as the activity page, so totals are
always consistent across the app. Each report can be viewed on screen, printed,
or exported to Excel/PDF via the activity export endpoint (filters carry over).
"""
from datetime import date

from flask import Blueprint, render_template, request, abort

from extensions import db
from models import Expense
from constants import CATEGORIES
from auth.decorators import login_required
from services.analytics import (
    ExpenseFilter, build_query, summarise, monthly_breakdown,
)

reports_bp = Blueprint("reports", __name__, url_prefix="/reports")

MONTH_NAMES = ["", "January", "February", "March", "April", "May", "June",
               "July", "August", "September", "October", "November", "December"]


@reports_bp.route("/")
@login_required
def index():
    """Report hub: pick a report type."""
    years = _available_years()
    return render_template(
        "reports/index.html",
        categories=CATEGORIES,
        years=years,
        current_year=date.today().year,
        current_month=date.today().month,
    )


@reports_bp.route("/monthly")
@login_required
def monthly():
    """Expenses for a single month (year + month query params)."""
    today = date.today()
    year = request.args.get("year", today.year, type=int)
    month = request.args.get("month", today.month, type=int)
    if not (1 <= month <= 12):
        abort(404)

    start = date(year, month, 1)
    end = date(year + (month == 12), (month % 12) + 1, 1)  # first of next month
    f = ExpenseFilter(start=start, end=end_minus_one(end))
    expenses = build_query(f).all()
    summary = summarise(f)
    trend = monthly_breakdown(12)

    return render_template(
        "reports/monthly.html",
        title=f"Monthly Report — {MONTH_NAMES[month]} {year}",
        expenses=expenses, summary=summary, filter=f, trend=trend,
        year=year, month=month, month_name=MONTH_NAMES[month],
        years=_available_years(),
    )


@reports_bp.route("/category")
@login_required
def category():
    """All expenses for one category (category query param)."""
    cat = (request.args.get("category") or "").strip()
    if cat not in CATEGORIES:
        cat = CATEGORIES[0]
    f = ExpenseFilter(category=cat)
    expenses = build_query(f).all()
    summary = summarise(f)

    return render_template(
        "reports/category.html",
        title=f"Category Report — {cat}",
        expenses=expenses, summary=summary, filter=f,
        selected=cat, categories=CATEGORIES,
    )


@reports_bp.route("/statement")
@login_required
def statement():
    """Full expense statement over an arbitrary date range (defaults to all)."""
    f = ExpenseFilter.from_args(request.args)
    expenses = build_query(f).all()
    summary = summarise(f)

    return render_template(
        "reports/statement.html",
        title="Expense Statement",
        expenses=expenses, summary=summary, filter=f,
        categories=CATEGORIES,
    )


@reports_bp.route("/print")
@login_required
def printable():
    """Clean, print-optimised version of any report (uses the same HTML as PDF)."""
    f = ExpenseFilter.from_args(request.args)
    expenses = build_query(f).all()
    summary = summarise(f)
    title = request.args.get("title", "Expense Statement")
    subtitle = _subtitle(f)

    return render_template(
        "reports/_pdf.html",
        title=title, subtitle=subtitle, expenses=expenses, summary=summary,
        categories=CATEGORIES, generated=date.today(), printable=True,
    )


# --- helpers ---------------------------------------------------------------
def end_minus_one(d: date) -> date:
    from datetime import timedelta
    return d - timedelta(days=1)


def _available_years() -> list[int]:
    rows = db.session.query(Expense.date).all()
    years = sorted({r[0].year for r in rows}, reverse=True)
    this_year = date.today().year
    if this_year not in years:
        years.insert(0, this_year)
    return years


def _subtitle(f: ExpenseFilter) -> str:
    parts = []
    if f.start or f.end:
        parts.append(f"{f.start or '…'} to {f.end or '…'}")
    if f.category:
        parts.append(f"Category: {f.category}")
    if f.search:
        parts.append(f'Search: "{f.search}"')
    return "  |  ".join(parts) if parts else "All expenses"
