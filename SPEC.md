# Gig Finder — v1 Specification

## Overview
A web app for musicians to search for live-music venues in a given area and get
contact info (email, phone, socials, booking page) scraped from each venue's
website, so they can reach out about booking gigs. Logged-in users can save
venues to a personal shortlist.

## Stack

- **Backend**: Python, FastAPI, SQLAlchemy, Alembic (migrations), httpx (async
  HTTP client for scraping/geocoding/Overpass), pytest.
- **Frontend**: React + Vite + TypeScript, Tailwind CSS, React Router, Vitest +
  React Testing Library.
- **Database & Auth**: Supabase-hosted Postgres + Supabase Auth (email/password).
  FastAPI connects to Postgres directly via SQLAlchemy and verifies the
  Supabase-issued JWT on each authenticated request — the backend does not use
  the Supabase client SDK, PostgREST, or Postgres RLS. This keeps a single
  familiar ORM/migration workflow in Python while still getting a zero-ops
  hosted Postgres instance and ready-made auth, at the cost of hand-writing
  authorization checks in FastAPI instead of leaning on RLS policies.
- **External services**: Nominatim (geocoding), Overpass API (OSM venue
  discovery) — both free, no API key required.

### Why this stack
The user is Python-strong and JS-weak but explicitly wants real React
experience, so a FastAPI JSON API + React SPA fits better than a Python-only
server-rendered frontend. Scale is personal/small with hosting undecided, so
Supabase is chosen over bare SQLite specifically because it resolves the
"where does Postgres live" question for free (generous free tier) without
committing to a PaaS, and its local CLI (`supabase start`) gives Postgres-in-
Docker locally that matches prod — avoiding the SQLite-locally/Postgres-in-
prod drift a smaller default might introduce. No real-time features are
needed, so websockets/SSE and their added complexity are avoided in favor of
concurrent server-side scraping with timeouts.

## Out of scope for v1
- Social login / OAuth providers (email/password only)
- Venues or users submitting/editing venue data
- Outreach/CRM tracking (contacted, replied, booked, declined status)
- Saved searches or alerts for new venues in an area
- Manual "force refresh" of cached area data (only automatic 30-day expiry)
- Admin role or admin panel
- API versioning (`/api/v1/...`) — add only when a breaking change requires it
- Real-time/streaming search progress (websockets/SSE)
- Deep multi-page crawling per venue site (homepage + one contact page only)
- Docker Compose–based local dev environment

## Data model (Postgres, via SQLAlchemy models in `backend/app/models.py`)

- **Area** — a geocoded, cacheable search region.
  `id, query_text, display_name, lat, lon, radius_m, last_scraped_at, created_at`.
  Unique constraint on `(round(lat, 4), round(lon, 4), radius_m)` to avoid
  duplicate rows for the same effective search.
- **Venue** — a place discovered via Overpass for a given Area.
  `id, area_id (FK), osm_id, name, address, lat, lon, website_url (nullable),
  osm_phone (nullable), osm_tags (jsonb), created_at, updated_at`.
- **VenueContact** — scraped contact info for a Venue (one-to-one).
  `id, venue_id (FK, unique), email (nullable), phone (nullable),
  social_links (jsonb: {instagram?, facebook?, twitter?}),
  booking_url (nullable), scrape_status (enum: success, no_website, timeout,
  disallowed_by_robots, error), scraped_at`.
- **SavedVenue** — a musician's shortlist entry.
  `id, user_id (Supabase auth user id, uuid), venue_id (FK), created_at`.
  Unique constraint on `(user_id, venue_id)`.

User accounts themselves live in Supabase Auth (`auth.users`); the app schema
only stores `user_id` as a foreign key, never duplicates auth data.

## API design (plain REST, no versioning, `backend/app/routers/`)

- `GET /api/geocode?q=<text>` → list of candidate places from Nominatim
  (`place_id, display_name, lat, lon`), for the disambiguation picker.
- `POST /api/search` — body `{lat, lon, display_name, radius_m?}` (radius
  capped server-side at 25km). Finds-or-creates the Area row; if cached data
  is younger than 30 days, returns it as-is; otherwise runs the Overpass query,
  scrapes new/changed venues concurrently, upserts Venue/VenueContact rows,
  updates `Area.last_scraped_at`, and returns the venue list (each with its
  `scrape_status`).
- `GET /api/saved-venues` (auth required) — the current user's shortlist.
- `POST /api/saved-venues` — body `{venue_id}` (auth required, idempotent).
- `DELETE /api/saved-venues/{venue_id}` (auth required).

Auth: `backend/app/auth.py` provides a FastAPI dependency that verifies the
Supabase JWT (signature + expiry) from the `Authorization: Bearer <token>`
header and extracts `user_id`; routes requiring login use it, `POST/DELETE
/api/saved-venues` reject unauthenticated requests with 401, `POST /api/search`
and `GET /api/geocode` do not require it.

## Local dev wiring
Two local processes: `uvicorn app.main:app --reload` (FastAPI, :8000) and
`npm run dev` (Vite, :5173). `frontend/vite.config.ts` proxies `/api/*` to
`localhost:8000`; FastAPI's CORS middleware allows the Vite origin as a
fallback. Local Postgres via `supabase start` (Supabase CLI), migrations
applied with Alembic.

## Modules/files

Backend (`backend/app/`):
- `main.py` — FastAPI app, CORS, router registration
- `config.py` — settings: `DATABASE_URL`, Supabase JWT verification config,
  `OVERPASS_API_URL`, `NOMINATIM_URL`, `CACHE_REFRESH_DAYS=30`,
  `SCRAPE_TIMEOUT_SECONDS=5`, `SCRAPE_CONCURRENCY=10`, `MAX_SEARCH_RADIUS_M=25000`
- `db.py` — SQLAlchemy engine/session
- `models.py` — Area, Venue, VenueContact, SavedVenue
- `schemas.py` — Pydantic request/response models
- `auth.py` — Supabase JWT verification dependency
- `routers/search.py` — `/api/geocode`, `/api/search`
- `routers/saved.py` — `/api/saved-venues` (GET/POST/DELETE)
- `services/geocode.py` — Nominatim client + disambiguation logic
- `services/overpass.py` — Overpass query builder/client, OSM tag filtering
  for live-music-relevant venues (bars, pubs, nightclubs, music venues)
- `services/scraper.py` — httpx concurrent scraper: `robots.txt` check
  (`urllib.robotparser`), homepage fetch, contact-page link detection,
  email/phone/social-link extraction, per-site timeout
- `services/cache.py` — Area freshness check against the 30-day window
- `alembic/` — migrations
- `tests/` — `test_geocode.py`, `test_overpass.py`, `test_scraper.py` (fixture
  HTML: has-email, has-phone, no-contact-info, robots-disallowed),
  `test_search_route.py` (cache hit vs miss), `test_saved_venues.py`
  (401 without token, CRUD with a test JWT), `conftest.py`

Frontend (`frontend/src/`):
- `main.tsx`, `App.tsx` — routes: `/`, `/login`, `/signup`, `/saved`
- `lib/supabaseClient.ts` — Supabase JS client (auth only)
- `api/client.ts` — fetch wrapper attaching the Supabase session JWT
- `context/AuthContext.tsx` — current session state
- `pages/SearchPage.tsx` — area input, disambiguation picker, results list
- `pages/LoginPage.tsx`, `pages/SignupPage.tsx` — Supabase email/password forms
- `pages/SavedVenuesPage.tsx` — shortlist view
- `components/VenueCard.tsx` — venue result (name, address, contact info,
  save/remove button; handles missing-contact-info state)
- `components/AreaDisambiguationPicker.tsx`
- `vite.config.ts` — dev proxy config
- `tests/`: `VenueCard.test.tsx`, `SearchPage.test.tsx`

CI:
- `.github/workflows/ci.yml` — runs `pytest` and `npm test` (Vitest) on
  push/PR

Env:
- `backend/.env.example` — `DATABASE_URL`, Supabase JWT verification settings,
  `OVERPASS_API_URL`, `NOMINATIM_URL`, cache/scrape/radius settings above
- `frontend/.env.example` — `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`

## Edge cases and failure modes

- **Broad/slow search area**: radius capped server-side at 25km regardless of
  client input; Overpass timeout/error surfaces as a clear "try a smaller
  area" message, not a hang or raw error.
- **Venue site down, slow, or blocking scrapers**: per-site 5s timeout,
  concurrent fetch (bounded concurrency), each venue gets a `scrape_status`
  (`success`/`no_website`/`timeout`/`disallowed_by_robots`/`error`) rather
  than failing the whole search; UI shows "no contact info found" gracefully.
- **`robots.txt` disallows scraping**: skip that venue's scrape, record
  `disallowed_by_robots`, still show the venue with OSM-sourced info.
- **Ambiguous area name** (e.g. "Springfield"): `/api/geocode` returns
  multiple candidates; frontend shows a disambiguation picker before
  searching.
- **Duplicate save**: unique `(user_id, venue_id)` constraint; `POST
  /api/saved-venues` is idempotent (already-saved is not an error).
  **Stale cache**: automatic 30-day expiry per Area; no manual refresh in v1.
- **Concurrent identical searches** (two users searching the same new area at
  once): mitigated by the unique constraint on `(lat, lon, radius_m)` plus an
  upsert-on-conflict when creating the Area row, rather than distributed
  locking.
- **Invalid/expired Supabase JWT**: 401 from the `auth.py` dependency.

## Testing — "done" per feature

- Geocoding: mocked Nominatim responses covering single match, multiple
  match, and no match.
- Venue discovery: mocked Overpass response, verifies OSM tag filtering and
  Venue upsert logic.
- Scraper: fixture HTML pages covering has-email, has-phone, no-contact-info,
  and robots-disallowed cases, asserting correct extraction and
  `scrape_status`.
- Search route: integration test verifying cache-hit (no re-scrape) vs
  cache-miss (re-scrape + `last_scraped_at` update) behavior.
- Saved venues: 401 without a token; authenticated CRUD with a test JWT;
  duplicate-save idempotency.
- Frontend: `VenueCard` renders contact fields and the missing-data state
  correctly; `SearchPage` shows the disambiguation picker when
  `/api/geocode` returns multiple candidates; `SavedVenuesPage` reflects
  save/remove.

## End-to-end verification

This is the acceptance check that the whole v1 feature set works together:

1. Start local Postgres (`supabase start`), apply Alembic migrations, run
   `uvicorn app.main:app --reload` and `npm run dev`.
2. In the browser, search a real small city (e.g. "Asheville, NC"). Confirm
   the venue list populates within a reasonable time, with contact info
   populated for at least some venues that have websites.
3. Search the same city again immediately. Confirm the response is fast
   (served from the 30-day cache, no re-scrape) and results match.
4. Sign up a new account via email/password, then log in.
5. From search results, save 2–3 venues; navigate to the Saved Venues page
   and confirm they appear.
6. Remove one saved venue; confirm it disappears from the list.
7. Log out; confirm search still works without login, but saving is
   unavailable/redirects to login.
8. Search an oversized area (e.g. "Texas"); confirm a clear "try a smaller
   area" error rather than a hang or crash.
9. Run `pytest` (backend) and `npm test` (frontend) — all tests pass.
10. Push a branch/PR and confirm the GitHub Actions CI workflow passes.
