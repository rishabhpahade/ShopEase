# ShopEase

A small e-commerce web application built with Flask and SQLite: product catalogue, search and category filtering, cart, checkout, order history, user profiles, and an admin area for products and orders.

## Stack

- **Flask 3** with server-rendered Jinja templates
- **SQLite** for storage (`schema.sql` + seeded sample catalogue)
- **Werkzeug** for password hashing and secure uploads
- No frontend build step — plain CSS and a little JavaScript

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python app.py                  # http://127.0.0.1:5000
```

The database is created and seeded on first start. Seeded admin account:
`admin` / `admin123` — change it before putting this anywhere public.

## Deploy to Vercel

The repository is already wired for Vercel:

- `api/index.py` — the WSGI entry point; the runtime imports `app` from it.
- `vercel.json` — builds that entry with `@vercel/python` and routes every request to it.
- `config.py` / `database.py` — on Vercel (`VERCEL=1`) the SQLite file and uploads are moved to `/tmp`, because the deployment itself is read-only. The committed `ecommerce.db` is copied there on cold start as the seed.

### Steps

1. Push this branch and merge it, so the deployable code is on the default branch.
2. In Vercel: **Add New → Project → Import Git Repository → `rishabhpahade/ShopEase`**.
3. Framework preset: **Other**. Leave build and output settings empty — `vercel.json` handles them.
4. Add one environment variable before the first deploy: `SECRET_KEY` (any long random string). Without it the app falls back to a development key, which means session cookies can be forged.
5. Deploy.

Every later push to the connected branch redeploys automatically.

### What behaves differently on Vercel

- **The database is ephemeral.** Serverless functions have no persistent disk; `/tmp` is per-instance and wiped on cold start, so accounts, carts and orders reset. The catalogue always comes back because it is seeded from the committed database. For a persistent store, point `DATABASE_PATH` at a hosted Postgres (Neon, Supabase) and swap `sqlite3` for a Postgres driver — the queries in `models.py` are plain SQL and port with minor placeholder changes.
- **Image uploads from the admin panel do not persist** — they land in `/tmp/uploads`, which is not served by the `/static/images/...` URLs the templates use, so an uploaded image falls back to `default.png`.
- **Cold starts** add a second or two to the first request after idle.

## Layout

```
app.py                  # routes: public, customer, admin
config.py               # paths, secret key, upload limits
database.py             # connection handling, schema init, seeding
models.py               # SQL queries for users, products, cart, orders
schema.sql              # tables + seed-compatible schema
templates/              # Jinja templates (customer + admin)
static/                 # CSS, JS and product images
api/index.py            # Vercel WSGI entry point
vercel.json             # Vercel build + routing
```
