# School Expense Management System

A Flask application for tracking school expenditure: single-admin login,
expense CRUD, a summary dashboard, and (from Phase 2) analytics, exports,
reports, and Render deployment.

## Tech stack

- **Flask** (application factory + blueprints)
- **SQLAlchemy** via Flask-SQLAlchemy — SQLite in dev, PostgreSQL in prod
- **Jinja2** templates + **Bootstrap 5** + Chart.js
- **Pandas / OpenPyXL** (Excel) and **WeasyPrint / ReportLab** (PDF) — Phase 2

## Project structure

```
expense_system/
├── app.py              # application factory + entrypoint
├── config.py           # env-driven config (dev/prod/test)
├── extensions.py       # shared SQLAlchemy instance
├── constants.py        # expense categories
├── models.py           # Expense model
├── auth/               # login/logout, password hashing, login_required
├── expenses/           # dashboard + CRUD routes (blueprint)
├── forms/              # server-side form validation
├── utils/              # helpers (currency, dates)
├── exports/            # generated Excel/PDF files (Phase 2)
├── templates/          # Jinja2 templates (base, auth, dashboard, expenses, errors)
├── static/             # css + js
├── seed.py             # sample data
└── requirements.txt
```

## Quick start (development)

```bash
cd expense_system
python -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate       # macOS/Linux
pip install -r requirements.txt

copy .env.example .env            # then edit credentials

set FLASK_APP=app.py              # Windows (PowerShell: $env:FLASK_APP="app.py")
flask init-db                     # create tables
flask seed                        # optional: sample expenses
python app.py                     # http://127.0.0.1:5000
```

Default dev credentials (override via `.env`): **admin / admin123**

## Configuration (environment variables)

| Variable | Purpose | Default |
|----------|---------|---------|
| `SECRET_KEY` | Flask session signing key | dev placeholder |
| `DATABASE_URL` | DB connection string | `sqlite:///expense.db` |
| `ADMIN_USERNAME` | Admin login name | `admin` |
| `ADMIN_PASSWORD` | Raw admin password (dev) | `admin123` |
| `ADMIN_PASSWORD_HASH` | Pre-hashed password (prod, preferred) | — |
| `FLASK_CONFIG` | `default` or `production` | `default` |
| `SESSION_COOKIE_SECURE` | `1` to require HTTPS cookies | `0` |

## Security notes

- The admin password is never stored in plain text — only a Werkzeug hash is
  kept in memory, and login uses a constant-time comparison.
- Sessions are HTTP-only, `SameSite=Lax`, and `Secure` in production.
- `next` redirects after login are validated to same-host paths only.
- All write routes require login; deletes are POST-only with confirmation.

## Features (Phase 2)

- **Dashboard analytics** — doughnut (spend by category) + bar (last 12 months) via Chart.js, plus summary cards.
- **Activity** — date-range filter, category filter, note search, sortable columns, live summary (total/count/average), and Excel/PDF export of the current view.
- **Reports** — Monthly, Category, Expense Statement, and a Printable view. Each exports to Excel/PDF and carries its filters into the export.
- **Export** — Excel via pandas + OpenPyXL (data + by-category + summary sheets). PDF via WeasyPrint with **automatic ReportLab fallback** when WeasyPrint's native libraries aren't available.

## Deployment (Render)

This repo includes a `render.yaml` Blueprint that provisions the web service and a free PostgreSQL database.

1. Push the repo to GitHub.
2. In Render: **New + → Blueprint**, select the repo (it reads `expense_system/render.yaml`).
3. Set the two `sync: false` env vars in the dashboard:
   - `ADMIN_USERNAME`
   - `ADMIN_PASSWORD_HASH` — generate locally with
     `python -c "from werkzeug.security import generate_password_hash as g; print(g('your-password'))"`
4. `SECRET_KEY` is auto-generated; `DATABASE_URL` is wired from the managed Postgres; HTTPS and `Secure` cookies are on in production.

Tables are created automatically on first boot (`wsgi.py`). To deploy manually instead of via Blueprint, set: Build `pip install -r requirements.txt`, Start `gunicorn wsgi:app`, Root Directory `expense_system`.

## Status

- **Phase 1 — Foundation:** ✅ auth, model, CRUD, dashboard, responsive UI.
- **Phase 2 — Analytics, reports, export, deployment:** ✅ charts, filters, Excel/PDF export, reports, Render config.
