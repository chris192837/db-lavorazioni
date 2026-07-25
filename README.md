# Dashboard Lavorazioni

A Flask web app for tracking daily work items ("lavorazioni" — documents and phone calls) per user, with role-based access and an admin reporting dashboard.

## Features

- Email/password authentication with hashed passwords (Werkzeug) and CSRF protection (Flask-WTF)
- Login throttling: blocks an account for 15 minutes after 5 failed attempts
- Role-based access (`admin` / `lavoratore`); the first registered user becomes admin
- Daily dashboard showing each user's calls/documents logged today
- Record history grouped by date, with single and bulk delete
- Admin-only reports: totals by type, per-user breakdown, and role management with a safeguard against removing the last remaining admin

## Tech stack

Python, Flask, PostgreSQL (psycopg2, raw SQL — no ORM), Flask-WTF, Gunicorn. Deployed on Render.

## Running locally

```bash
pip install -r requirements.txt
```

Create a `.env` with `SECRET_KEY` and either `DATABASE_URL` or the individual `PG_HOST` / `PG_PORT` / `PG_DB` / `PG_USER` / `PG_PASSWORD` variables, then:

```bash
python app.py
```

## Deployment

Configured for [Render](https://render.com) via `render.yaml` and `Procfile` (`gunicorn app:app`), with a managed Postgres database wired through `DATABASE_URL`.
