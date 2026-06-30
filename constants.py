"""Application-wide constants.

Expense categories are a fixed, ordered list. Storing them here (rather than in
a database table) keeps validation simple and guarantees that reports always
render every category, even ones with no expenses yet.
"""

CATEGORIES = [
    "Stationary",
    "Transport",
    "Event",
    "Salary",
    "Other expenditure",
]

# Fast membership checks during validation.
CATEGORY_SET = set(CATEGORIES)

# A stable colour per category, reused by Chart.js on the dashboard so the same
# category is always the same colour across charts.
CATEGORY_COLORS = {
    "Stationary": "#4e79a7",
    "Transport": "#f28e2b",
    "Event": "#e15759",
    "Salary": "#76b7b2",
    "Other expenditure": "#9c755f",
}
