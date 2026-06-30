"""Excel and PDF export.

Excel uses pandas + OpenPyXL. PDF prefers WeasyPrint (HTML -> PDF, nicer
styling) but, because WeasyPrint needs native GTK libraries that are awkward on
Windows, it transparently falls back to ReportLab when WeasyPrint can't be
imported or fails at render time. Callers don't need to know which engine ran.
"""
import io
from datetime import date
from decimal import Decimal

import pandas as pd

from constants import CATEGORIES


# --- Detect WeasyPrint once at import time --------------------------------
try:  # pragma: no cover - depends on the host having GTK
    import weasyprint  # noqa: F401
    _WEASYPRINT_AVAILABLE = True
except Exception:
    _WEASYPRINT_AVAILABLE = False


def pdf_engine() -> str:
    """Which PDF engine will be used (for display / diagnostics)."""
    return "weasyprint" if _WEASYPRINT_AVAILABLE else "reportlab"


# ===========================================================================
# Excel
# ===========================================================================
def expenses_to_excel(expenses, summary: dict, title: str = "Expense Report") -> bytes:
    """Return an .xlsx workbook (bytes) with a data sheet and a summary sheet."""
    data = [{
        "Date": e.date.isoformat(),
        "Category": e.category,
        "Amount": float(e.amount),
        "Note": e.note or "",
    } for e in expenses]
    df = pd.DataFrame(data, columns=["Date", "Category", "Amount", "Note"])

    cat_df = pd.DataFrame(
        [{"Category": r["category"], "Total": float(r["total"])}
         for r in summary["category_totals"]]
    )
    summary_df = pd.DataFrame([
        {"Metric": "Report", "Value": title},
        {"Metric": "Generated", "Value": date.today().isoformat()},
        {"Metric": "Records", "Value": summary["count"]},
        {"Metric": "Total", "Value": float(summary["total"])},
        {"Metric": "Average", "Value": round(float(summary["average"]), 2)},
    ])

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Expenses", index=False)
        cat_df.to_excel(writer, sheet_name="By Category", index=False)
        summary_df.to_excel(writer, sheet_name="Summary", index=False)
        _autofit(writer.sheets["Expenses"], df)
        _autofit(writer.sheets["By Category"], cat_df)
    buf.seek(0)
    return buf.getvalue()


def _autofit(ws, df):
    """Best-effort column auto-width for readability."""
    from openpyxl.utils import get_column_letter
    for i, col in enumerate(df.columns, start=1):
        width = max(
            len(str(col)),
            *(len(str(v)) for v in df[col].tolist())
        ) if len(df) else len(str(col))
        ws.column_dimensions[get_column_letter(i)].width = min(width + 2, 50)


# ===========================================================================
# PDF
# ===========================================================================
def expenses_to_pdf(expenses, summary: dict, title: str,
                    subtitle: str = "") -> bytes:
    """Render a PDF, preferring WeasyPrint and falling back to ReportLab."""
    if _WEASYPRINT_AVAILABLE:
        try:
            return _pdf_weasyprint(expenses, summary, title, subtitle)
        except Exception:
            # Any render-time failure -> degrade gracefully to ReportLab.
            pass
    return _pdf_reportlab(expenses, summary, title, subtitle)


def render_report_html(expenses, summary: dict, title: str, subtitle: str = "") -> str:
    """The HTML used both for WeasyPrint and the printable browser view."""
    from flask import render_template
    return render_template(
        "reports/_pdf.html",
        expenses=expenses, summary=summary, title=title, subtitle=subtitle,
        categories=CATEGORIES, generated=date.today(),
    )


def _pdf_weasyprint(expenses, summary, title, subtitle) -> bytes:  # pragma: no cover
    html = render_report_html(expenses, summary, title, subtitle)
    return weasyprint.HTML(string=html).write_pdf()


def _pdf_reportlab(expenses, summary, title, subtitle) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    )

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
        title=title,
    )
    styles = getSampleStyleSheet()
    brand = colors.HexColor("#2c5f8f")
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], textColor=brand)
    meta = ParagraphStyle("meta", parent=styles["Normal"], textColor=colors.grey,
                          fontSize=9)

    story = [Paragraph(title, h1)]
    if subtitle:
        story.append(Paragraph(subtitle, meta))
    story.append(Paragraph(f"Generated: {date.today().isoformat()}", meta))
    story.append(Spacer(1, 8 * mm))

    # Summary line.
    story.append(Paragraph(
        f"<b>Total:</b> Rs. {summary['total']:,.2f} &nbsp;&nbsp; "
        f"<b>Records:</b> {summary['count']} &nbsp;&nbsp; "
        f"<b>Average:</b> Rs. {summary['average']:,.2f}",
        styles["Normal"],
    ))
    story.append(Spacer(1, 4 * mm))

    # Category totals table.
    cat_data = [["Category", "Total (Rs.)"]]
    for r in summary["category_totals"]:
        cat_data.append([r["category"], f"{r['total']:,.2f}"])
    cat_table = Table(cat_data, colWidths=[90 * mm, 50 * mm])
    cat_table.setStyle(_table_style(brand))
    story.append(cat_table)
    story.append(Spacer(1, 8 * mm))

    # Detail table.
    story.append(Paragraph("Expense Detail", styles["Heading3"]))
    detail = [["Date", "Category", "Amount (Rs.)", "Note"]]
    for e in expenses:
        detail.append([
            e.date.strftime("%d %b %Y"),
            e.category,
            f"{Decimal(str(e.amount)):,.2f}",
            (e.note or "")[:40],
        ])
    if len(detail) == 1:
        detail.append(["—", "No records", "—", "—"])
    detail_table = Table(detail, colWidths=[28 * mm, 38 * mm, 30 * mm, 54 * mm],
                         repeatRows=1)
    detail_table.setStyle(_table_style(brand))
    story.append(detail_table)

    doc.build(story)
    buf.seek(0)
    return buf.getvalue()


def _table_style(brand):
    from reportlab.lib import colors
    from reportlab.platypus import TableStyle
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), brand),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (-2, 0), (-2, -1), "RIGHT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f6f9")]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d0d7e2")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ])
