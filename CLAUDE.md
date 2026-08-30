# Gig Finder

Web app for musicians to search live-music venues in an area and get scraped
contact info (email, phone, socials, booking page) for booking outreach.
Logged-in users maintain a saved venue shortlist.

Full planning spec: see `SPEC.md`. This file holds only what should load into
every session — architecture facts and conventions, not the full spec.

## Stack

- Backend: Python, FastAPI, SQLAlchemy, Alembic, httpx, pytest
- Frontend: React + Vite + TypeScript, Tailwind CSS, React Router, Vitest +
  React Testing Library
- DB & Auth: Supabase-hosted Postgres + Supabase Auth (email/password).
  FastAPI connects directly via SQLAlchemy and verifies the Supabase JWT
  itself. Does NOT use the Supabase client SDK, PostgREST, or RLS on the
  backend.
- External APIs: Nominatim (geocoding), Overpass API (OSM venue discovery) —
  both free, no key required

## Commands

- Backend commands (`uvicorn`, `alembic`, `pytest`, `pip`) require the venv
  active: `source backend/.venv/bin/activate`
- Backend dev server: `uvicorn app.main:app --reload` (port 8000)
- Frontend dev server: `npm run dev` (port 5173, from `frontend/`)
- Local Postgres: `supabase start` / `supabase stop`
- Migrations: `alembic upgrade head`, `alembic revision --autogenerate -m "..."`
- Backend tests: `pytest` (from `backend/`)
- Frontend tests: `npm test` (from `frontend/`)

## Directory layout

- `backend/app/main.py` — FastAPI app, CORS, router registration
- `backend/app/config.py` — settings, env-driven (see `.env.example`)
- `backend/app/db.py` — SQLAlchemy engine/session
- `backend/app/models.py` — Area, Venue, VenueContact, SavedVenue
- `backend/app/schemas.py` — Pydantic request/response models
- `backend/app/auth.py` — Supabase JWT verification dependency
- `backend/app/routers/` — one file per resource (`search.py`, `saved.py`)
- `backend/app/services/` — external integrations and business logic
  (`geocode.py`, `overpass.py`, `scraper.py`, `cache.py`)
- `backend/alembic/` — migrations
- `backend/tests/` — pytest, fixture HTML under `tests/fixtures/`
- `supabase/config.toml` — local Supabase CLI project config (from
  `supabase init`); governs the `supabase start`/`stop` local Postgres +
  Auth stack
- `frontend/src/pages/` — route-level components
- `frontend/src/components/` — reusable UI
- `frontend/src/api/client.ts` — fetch wrapper, attaches Supabase session JWT
- `frontend/src/context/AuthContext.tsx` — session state

## Conventions

- Routers stay thin: validation and orchestration only. Business logic
  (scraping, geocoding, caching) lives in `services/`.
- All request/response shapes go through Pydantic schemas in `schemas.py` —
  routers never return SQLAlchemy models directly.
- Auth-required routes depend on `auth.py`'s JWT-verification dependency;
  never re-implement token parsing in a router.
- Every external HTTP call (Nominatim, Overpass, venue scraping) goes through
  `httpx` with an explicit timeout — no un-timed requests.
- New Postgres schema changes go through an Alembic migration; never
  hand-edit the schema.

## Explicitly out of scope for v1

Do not implement these even if they seem like natural next steps — they're
deliberately deferred, not forgotten:

- Social login / OAuth (email/password only)
- Users submitting or editing venue data
- Outreach/CRM tracking (contacted/replied/booked status)
- Saved searches or alerts
- Manual "force refresh" (only automatic 30-day cache expiry)
- Admin role or panel
- `/api/v1/` versioning
- Websockets/SSE or streaming search progress
- Multi-page crawling per venue (homepage + one contact page only)
- Docker Compose local dev setup

## Testing

- Backend: mock external services (Nominatim, Overpass) in tests; scraper
  tests use fixture HTML files, never live network calls
- Frontend: React Testing Library, one test file per page/component under
  test
- Run `pytest` and `npm test` before considering a feature done; both must
  pass in CI (`.github/workflows/ci.yml`)

## Git workflow

- After finishing a logical unit of work (one module from the implementation
  plan, a bug fix, or a change that leaves tests passing), stop and ask
  whether to commit now, rather than letting unrelated changes pile up
  uncommitted.
- After a commit leaves the tree in a good state, ask whether to push. Don't
  push without asking even if the answer seems obvious — `git push` already
  requires approval per `.claude/settings.json`, so this is about prompting
  at the right moment, not bypassing that gate.
- If several files have changed with no commit yet, raise it proactively
  instead of waiting to be asked.
- Before ending a session (the user signals they're stopping for now), check
  whether there's uncommitted or unpushed work and ask about it once.

## Environment

- Real secrets live in `backend/.env` and `frontend/.env` (gitignored) —
  never read or print these; `.env.example` documents what's needed
- Local Postgres and auth run via the Supabase CLI (`supabase start`), not
  Docker Compose