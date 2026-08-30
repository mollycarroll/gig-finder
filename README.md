# Gig Finder

A web app for musicians to search live-music venues in an area and get
scraped contact info (email, phone, socials, booking page) for booking
outreach. Logged-in users can save venues to a personal shortlist.

See [SPEC.md](./SPEC.md) for the full data model, API design, and edge
cases, and [CLAUDE.md](./CLAUDE.md) for architecture conventions.

## Stack

- **Backend**: Python (FastAPI, SQLAlchemy, Alembic, httpx, pytest)
- **Frontend**: React + Vite + TypeScript, Tailwind CSS, React Router,
  Vitest
- **Database & Auth**: Supabase (Postgres + Supabase Auth). The backend
  connects directly via SQLAlchemy and verifies Supabase JWTs itself — it
  does not use the Supabase client SDK, PostgREST, or RLS for its own
  authorization (RLS is enabled on the tables purely to lock down
  Supabase's auto-exposed REST API; see the migration that adds it).
- **External APIs**: Nominatim (geocoding), Overpass API (venue discovery)
  — both free, no key required

## Prerequisites

- Python 3.14+
- Node 20+ (this project was built against Node 26)
- [Supabase CLI](https://supabase.com/docs/guides/cli) — for local
  Postgres + Auth
- Docker — the Supabase CLI runs Postgres/Auth in containers

## Setup

### 1. Supabase

You need either a **local** Supabase stack or a **hosted** Supabase
project. Local is simplest for day-to-day development:

```bash
supabase init   # only needed once, already done in this repo
supabase start
```

This prints a `DB_URL`, `API_URL`, and `ANON_KEY` (or `PUBLISHABLE_KEY`)
you'll need below. Run `supabase status` any time to see them again.
`supabase stop` shuts it down (data persists across stop/start).

To use a **hosted** project instead: create one at
[supabase.com](https://supabase.com), then from its dashboard grab the
**Project URL**, **anon/publishable key** (Settings → API), and a
**direct connection string** (Settings → Database — use the direct
connection on port 5432, not the transaction pooler, since this is a
persistent server, not serverless).

### 2. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `backend/.env`:

- `DATABASE_URL` — from `supabase status` (local) or your project's
  direct connection string (hosted)
- `SUPABASE_URL` — `http://127.0.0.1:54321` (local) or your project's
  URL (hosted)
- the rest of the defaults in `.env.example` are fine as-is

Apply migrations:

```bash
alembic upgrade head
```

### 3. Frontend

```bash
cd frontend
npm install
cp .env.example .env
```

Edit `frontend/.env`:

- `VITE_SUPABASE_URL` — same URL as `SUPABASE_URL` above
- `VITE_SUPABASE_ANON_KEY` — the anon/publishable key from step 1

## Running locally

Two processes, in separate terminals (from each directory, with the
backend venv active):

```bash
# backend/
uvicorn app.main:app --reload   # http://localhost:8000
```

```bash
# frontend/
npm run dev                      # http://localhost:5173
```

Vite proxies `/api/*` requests to the backend automatically. Visit
`http://localhost:8000/docs` for interactive API docs.

**Note on hosted Supabase**: new users must confirm their email before
they can log in (email confirmation is on by default). For local dev,
Supabase's local Auth auto-confirms signups, so this isn't an issue there.

## Tests

```bash
cd backend && pytest
cd frontend && npm test
```

Backend tests use a real Postgres connection (the one in `DATABASE_URL`)
wrapped in a rolled-back transaction per test — no separate test database
needed. All external HTTP calls (Nominatim, Overpass, venue scraping,
Supabase's JWKS endpoint) are mocked; no live network calls happen in
tests.

## CI

`.github/workflows/ci.yml` runs both test suites on push/PR against a
throwaway Postgres service container — no Supabase instance needed in CI.
