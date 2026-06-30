"""Expense CRUD, dashboard, and export routes."""
from decimal import Decimal

from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, current_app,
    abort, Response,
)
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import Expense
from constants import CATEGORIES, CATEGORY_COLORS
from forms.expense_form import validate_expense_form
from auth.decorators import login_required
from utils.helpers import today_iso
from services.analytics import (
    ExpenseFilter, build_query, summarise, category_breakdown, monthly_breakdown,
)

expenses_bp = Blueprint("expenses", __name__)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@expenses_bp.route("/")
@login_required
def dashboard():
    category_totals = category_breakdown()
    monthly = monthly_breakdown(12)
    total = sum((r["total"] for r in category_totals), Decimal("0"))

    recent = (
        Expense.query.order_by(Expense.date.desc(), Expense.id.desc())
        .limit(8)
        .all()
    )
    count = Expense.query.count()

    # Pre-shaped data for Chart.js (kept JSON-friendly: floats + hex colours).
    # `urls` lets a click on a slice/bar drill into the matching report.
    doughnut = {
        "labels": [r["category"] for r in category_totals],
        "data": [float(r["total"]) for r in category_totals],
        "colors": [CATEGORY_COLORS[r["category"]] for r in category_totals],
        "urls": [url_for("reports.category", category=r["category"])
                 for r in category_totals],
    }
    bar = {
        "labels": [m["label"] for m in monthly],
        "data": [float(m["total"]) for m in monthly],
        "urls": [url_for("reports.monthly", year=m["year"], month=m["month"])
                 for m in monthly],
    }

    return render_template(
        "dashboard/index.html",
        total=total,
        category_totals=category_totals,
        recent=recent,
        count=count,
        doughnut=doughnut,
        bar=bar,
    )


# ---------------------------------------------------------------------------
# List / Activity (with filtering, search, sorting, summary)
# ---------------------------------------------------------------------------
@expenses_bp.route("/expenses")
@login_required
def activity():
    f = ExpenseFilter.from_args(request.args)
    page = request.args.get("page", 1, type=int)
    per_page = current_app.config["PER_PAGE"]

    pagination = build_query(f).paginate(
        page=page, per_page=per_page, error_out=False
    )
    summary = summarise(f)

    return render_template(
        "expenses/activity.html",
        pagination=pagination,
        expenses=pagination.items,
        filter=f,
        summary=summary,
        categories=CATEGORIES,
    )


# ---------------------------------------------------------------------------
# Exports (respect the active activity filter)
# ---------------------------------------------------------------------------
@expenses_bp.route("/expenses/export/<string:fmt>")
@login_required
def export(fmt):
    from services.export_service import expenses_to_excel, expenses_to_pdf

    f = ExpenseFilter.from_args(request.args)
    expenses = build_query(f).all()
    summary = summarise(f)
    title = "Expense Report"
    subtitle = _filter_subtitle(f)
    stamp = today_iso()

    if fmt == "excel":
        data = expenses_to_excel(expenses, summary, title)
        return Response(
            data,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=expenses_{stamp}.xlsx"},
        )
    if fmt == "pdf":
        data = expenses_to_pdf(expenses, summary, title, subtitle)
        return Response(
            data,
            mimetype="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=expenses_{stamp}.pdf"},
        )
    abort(404)


def _filter_subtitle(f: ExpenseFilter) -> str:
    parts = []
    if f.start or f.end:
        parts.append(f"{f.start or '…'} to {f.end or '…'}")
    if f.category:
        parts.append(f"Category: {f.category}")
    if f.search:
        parts.append(f'Search: "{f.search}"')
    return "  |  ".join(parts) if parts else "All expenses"


# ---------------------------------------------------------------------------
# Add
# ---------------------------------------------------------------------------
@expenses_bp.route("/expenses/add", methods=["GET", "POST"])
@login_required
def add():
    if request.method == "POST":
        cleaned, errors = validate_expense_form(request.form)
        if errors:
            return render_template(
                "expenses/form.html",
                mode="add",
                categories=CATEGORIES,
                errors=errors,
                data=request.form,
            ), 400

        expense = Expense(**cleaned)
        try:
            db.session.add(expense)
            db.session.commit()
            flash("Expense added successfully.", "success")
            return redirect(url_for("expenses.activity"))
        except SQLAlchemyError:
            db.session.rollback()
            current_app.logger.exception("Failed to add expense")
            flash("Could not save the expense. Please try again.", "danger")

    return render_template(
        "expenses/form.html",
        mode="add",
        categories=CATEGORIES,
        errors={},
        data={"date": today_iso()},
    )


# ---------------------------------------------------------------------------
# Edit
# ---------------------------------------------------------------------------
@expenses_bp.route("/expenses/<int:expense_id>/edit", methods=["GET", "POST"])
@login_required
def edit(expense_id):
    expense = db.session.get(Expense, expense_id)
    if expense is None:
        abort(404)

    if request.method == "POST":
        cleaned, errors = validate_expense_form(request.form)
        if errors:
            return render_template(
                "expenses/form.html",
                mode="edit",
                expense=expense,
                categories=CATEGORIES,
                errors=errors,
                data=request.form,
            ), 400

        try:
            expense.amount = cleaned["amount"]
            expense.category = cleaned["category"]
            expense.date = cleaned["date"]
            expense.note = cleaned["note"]
            db.session.commit()
            flash("Expense updated successfully.", "success")
            return redirect(url_for("expenses.activity"))
        except SQLAlchemyError:
            db.session.rollback()
            current_app.logger.exception("Failed to update expense %s", expense_id)
            flash("Could not update the expense. Please try again.", "danger")

    # GET (or failed POST falls through to add-form path above) — prefill.
    data = {
        "amount": f"{expense.amount:.2f}",
        "category": expense.category,
        "date": expense.date.isoformat(),
        "note": expense.note or "",
    }
    return render_template(
        "expenses/form.html",
        mode="edit",
        expense=expense,
        categories=CATEGORIES,
        errors={},
        data=data,
    )


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------
@expenses_bp.route("/expenses/<int:expense_id>/delete", methods=["POST"])
@login_required
def delete(expense_id):
    expense = db.session.get(Expense, expense_id)
    if expense is None:
        abort(404)
    try:
        db.session.delete(expense)
        db.session.commit()
        flash("Expense deleted.", "success")
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Failed to delete expense %s", expense_id)
        flash("Could not delete the expense. Please try again.", "danger")
    return redirect(url_for("expenses.activity"))
