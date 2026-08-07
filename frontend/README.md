# OxiQ Dashboard (Phase 10)

React + TypeScript + Tailwind, consuming the backend REST API from `../app`.

## Local development

```bash
cp .env.example .env   # leave VITE_API_BASE_URL blank to use the dev proxy
npm install
npm run dev
```

Runs on `http://localhost:5173`. Requests to `/api/*` are proxied to `http://localhost:8000`
(the FastAPI backend - see `vite.config.ts`), so no CORS setup is needed in dev. For a production
build pointed at a deployed API, set `VITE_API_BASE_URL` in `.env` to that API's origin.

```bash
npm run build     # type-checks (tsc -b) then builds to dist/
npm run lint       # eslint
```

## Pages

- **`/`** - the intake console (submit a domain, watch the job get scanned) plus the dossier
  index (paginated list of previously analyzed companies)
- **`/company/:id`** - a company's full dossier: purchase score dial, the six pillar scores as a
  radar chart, the sales recommendation, and the evidence log (every matched signal, grouped by
  pillar, shown as a sourced excerpt)

`POST /analyze` is asynchronous on the backend (a Celery job), so submitting a domain here polls
`GET /jobs/{job_id}` every 2s and navigates to the dossier once the job completes.

## Design direction

Built around what this product actually does - turn public evidence into a scored, sourced
verdict - rather than a generic SaaS-dashboard look: a dark "analyst's dossier" aesthetic (deep
ink background, a single signal-cyan accent), Source Serif 4 for headlines paired with IBM Plex
Sans/Mono for UI and data readouts, stamped priority badges (`HIGH PRIORITY` / `DISQUALIFIED`),
and a hexagonal radar chart for the six pillar scores - a shape that falls directly out of there
being exactly six pillars, not a decorative choice.

## What's not done

- **No auth** - matches the backend, which also has none yet
- **No company search/filter UI** - the backend's `/companies?industry=` filter exists but isn't
  exposed in the dossier index yet, just plain pagination
- **Disqualified detection is inferred, not explicit** - `CompanyPage.tsx` infers a company was
  disqualified from `purchase_score === 0 && confidence === 0`, since that's the only condition
  the current Rule Engine disqualifier produces and there's no dedicated `disqualified` field on
  `GET /scores/{id}`. A cleaner fix would be exposing that flag directly from the backend.
- **No loading skeletons** - `CompanyPage` shows a single "Pulling dossier..." line rather than
  skeleton placeholders for the dial/radar/evidence sections
- **Never run against a live backend** - built and screenshot-tested against mock data only (no
  Postgres/Redis/Celery running in the environment this was built in); the API client is written
  to the documented contract but hasn't been exercised against the real endpoints end-to-end
- **No tests** - no Vitest/Testing Library setup yet
