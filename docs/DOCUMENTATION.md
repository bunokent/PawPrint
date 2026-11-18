# PawPrint — Documentation

PawPrint is a dual-mode lost-pet alert + adoption flyer generator. Guests can browse alerts
and scan QR codes; one unified registered account (email or Google/Gmail OAuth) can post
lost-pet emergencies, publish adoptable pets, generate print-ready A4 flyers, and fund
rewards via Stripe (test mode) or GCash/QR Ph via PayMongo.

---

## 1. Overview & Product Vision

PawPrint helps a lost pet come home and helps a shelter pet find one. Two modes share one
product:

- **Emergency Lost-Pet Mode** — urgent, high-contrast alerts with last-seen details,
  distinctive markings, an optional reward, and a scannable QR code on a print-ready A4 flyer.
- **Adoption Outreach Mode** — warm, welcoming adoption flyers with personality tags and
  shelter/foster framing.

Every uploaded pet photo passes a YOLOv8 pet-detection gatekeeper before it ever reaches
storage. Non-pet photos are rejected with a friendly 422 — no strikes, no bans. The web app
(`frontend/`, React 19 + TS + Vite) implements the full product in the browser, and
Playwright E2E covers the 6 critical journeys end-to-end.

## 2. Architecture & Stack

- **Backend**: Django 5.2+ (Python 3.12+), DRF, drf-spectacular (OpenAPI), PostgreSQL 16,
  Redis 7, Celery, Django Channels (WebSockets), django-allauth (email + Google OAuth 2.0).
  **No Django Admin** — `django.contrib.admin` is completely removed.
- **Frontend**: React 19 + TypeScript + Vite, React Router v7, TanStack Query v5, Axios,
  Zustand, React Hook Form + Zod, Shadcn/UI, Tailwind v4. React Compiler enabled.
- **Storage**: Cloudinary (private delivery type, HMAC-signed URLs only) via the `cloudinary`
  SDK, wrapped in a Django `Storage` backend (`apps/common/cloudinary_storage.py`).
- **Payments**: Stripe Python SDK (test mode) + PayMongo REST via httpx (GCash Checkout, QR Ph).
- **AI Vision**: YOLOv8 (`ultralytics`, `yolov8n.pt`) pet detection gatekeeper.
- **Exports**: WeasyPrint A4@300dpi PNG/PDF flyers + Pillow thumbnails; Playwright for
  browser-side exports.
- **Infra**: `docker-compose.yml` provides `postgres:16`, `redis:7`, `mailpit` (storage is
  Cloudinary, so no MinIO service). Host-side `python manage.py ...` auto-loads the root
  `.env` via python-dotenv (compose sets real env vars, which always win inside containers;
  web/celery additionally pin the in-network `postgres:5432` via `environment:`). For tests
  and Playwright E2E, `PAWPRINT_TESTING=1` (or running under pytest) switches to locmem
  cache, in-memory channel layer, eager Celery, `memory://` broker and filesystem storage —
  no Redis/Cloudinary needed.

## 3. Access Model (Guest vs Registered — STRICT 2 Modes)

| Capability | Guest | Registered |
|---|---|---|
| Browse lost-pet alerts & adoptable pets | ✅ | ✅ |
| Full-text search / filter flyers | ✅ | ✅ |
| View flyer detail (incl. QR scan landing) | ✅ | ✅ |
| Download / print A4 flyer exports | ✅ (active flyers) | ✅ |
| Create / edit / delete own flyers | ❌ | ✅ |
| Upload pet photos (YOLOv8-gated) | ❌ | ✅ |
| Fund rewards (Stripe / GCash) | ❌ | ✅ |

There is **no admin role, no staff flag, no strike/ban system**. Object-level mutations are
restricted to the creator via `IsOwnerOrReadOnly`. The frontend enforces the same split in
the UI: guests see browse/scan actions, registered users additionally see New flyer, My
flyers, photo upload and Fund reward.

## 4. Backend — Models & ORM

Apps under `backend/apps/`: `users`, `pets`, `flyers`, `rewards`, `webhooks`, `vision`.

- `users.User` — AbstractUser, UUID PK, email login, `display_name`, `phone`, `avatar_path`,
  `google_id` (nullable unique), `email_verified`, `stripe_customer_id`.
- `pets.Pet` — UUID PK, `owner` FK, species/breed/color/age, `temperament_tags` & `health_tags`
  JSON (GIN indexes), `photo_path`, `status` (`lost|adoptable|reunited|adopted`),
  `SearchVector` GIN index on `(name, breed, color)`, composite index `(status, created_at)`.
- `flyers.Flyer` — UUID PK, `pet` FK, `creator` FK, `mode` (`emergency|outreach`), last-seen
  fields, contact fields, reward fields, QR target, export paths, `status`
  (`draft|generating|active|resolved`); indexes `(mode, status, created_at)`, `(creator, mode)`.
- `rewards.RewardTransaction` — UUID PK, `flyer`/`user` FKs, `provider` (`stripe|gcash`),
  unique `provider_reference`, `amount_cents`, `currency`, `status`, `metadata` JSON.
- `webhooks.WebhookEvent` — `UniqueConstraint(provider, event_id)` for idempotency.
- `vision.PetDetectionLog` — detection audit trail (classes, max confidence, passed).

Layering: `selectors/` (all reads, optimized QuerySets, SearchVector FTS, cursor pagination),
`services/` (all writes in `@transaction.atomic`, external calls, task dispatch), thin views
(≤15 lines, zero raw ORM). Verified with `EXPLAIN ANALYZE` (see §11): gallery list runs on
`flyer_status_created_idx` in ~0.2 ms; FTS uses `pet_search_vector_gin`; reward writes use
`select_for_update` + the unique `provider_reference` for idempotency.

## 5. API Reference (OpenAPI)

Schema generated by drf-spectacular: `python manage.py spectacular --file schema.yml`,
consumed by the frontend via `openapi-typescript` → `frontend/src/lib/api/schema.d.ts`.

| Endpoint | Auth | Purpose |
|---|---|---|
| `POST /api/auth/register` | Guest | Create unified account (email) |
| `POST /api/auth/login` | Guest | HttpOnly session + CSRF cookie |
| `POST /api/auth/logout` | Auth | End session |
| `GET /api/auth/me` | Any | Profile or 401 |
| `GET /api/auth/google/url` + `POST /api/auth/google/callback` | Guest | Google/Gmail OAuth 2.0 |
| `GET /api/flyers` | Guest | Cursor-paginated gallery, FTS `?q=`, mode filter `?mode=` |
| `GET /api/flyers/{id}` | Guest | Public flyer detail (QR scan landing) |
| `POST /api/flyers/new` | Auth | Create flyer (dispatches A4 asset generation) |
| `PATCH/DELETE /api/flyers/{id}/edit` | Auth (owner) | Update / resolve / delete own flyer |
| `GET /api/flyers/mine` | Auth | Creator's own flyers |
| `POST /api/pets/photos` | Auth | YOLOv8-gated photo upload (10/min) |
| `POST /api/pets` | Auth | Create pet record (links an uploaded photo) |
| `POST /api/rewards` | Auth | Create reward payment (Stripe/GCash) → checkout URL / QR payload |
| `GET /api/rewards/{id}/status` | Auth (payer/creator) | Poll payment status |
| `GET /api/rewards/mine` | Auth | Own reward history |
| `POST /api/webhooks/stripe` / `POST /api/webhooks/paymongo` | Signature | Idempotent webhooks |
| `GET /api/health` | Public | Liveness probe |
| `GET /api/schema` | Public | drf-spectacular OpenAPI schema |

## 6. Auth & OAuth Flow

- Email registration & login issue an HttpOnly session cookie plus a CSRF cookie; the
  frontend axios client sends `X-CSRFToken` on mutations (`src/lib/api/client.ts`).
- Google/Gmail OAuth 2.0 via django-allauth: one click registers a new Gmail account,
  links an existing email account, or signs in an existing Google user. The SPA handles the
  redirect at `/auth/login?code=…` (`LoginPage` exchanges the code via
  `POST /api/auth/google/callback`).
- Auth mutations are rate-limited to 20/min (`auth_write` scope; 429 on the 21st request).
- Guests hitting an auth-only endpoint get 401 with `error.session_expired: true`
  (`SessionAuthenticationWith401`), which the SPA uses to reset the auth store.

## 7. Flyers, QR & A4 Export

- `QrService` mints a QR code targeting the public flyer URL —
  `qr_target_value = {FRONTEND_BASE_URL}/flyers/{id}` (set on create and by `seed_demo`), so a
  printed QR lands a scanner directly on the guest-accessible flyer page. The SPA renders the
  same target as an SVG data-URL QR (`QrImage`) on the detail page and inside the A4 export.
- On create/update, `FlyerService` dispatches Celery task `generate_flyer_assets` (queue
  `flyers`): renders the HTML flyer template with WeasyPrint to A4 PDF + Playwright A4@300dpi
  PNG, uploads to private Cloudinary, marks the flyer `active`, then broadcasts `flyer.generated`
  over Django Channels (`ws/flyers/`).
- Flyer templates (`templates/flyers/{emergency,outreach}.html`) and the on-screen
  `.print-sheet` follow the `taste` skill print typography (`@page { size: A4; margin: 0 }`,
  `.no-print` chrome hidden): emergency mode uses crimson/amber high-contrast scannability;
  outreach mode uses sage/teal/terracotta warmth. The detail page's Print button uses the
  same sheet.

## 8. AI Pet Detection (YOLOv8 Gatekeeper)

- `PetDetectionService.validate_pet_image(image_bytes)` runs a singleton
  `ultralytics.YOLO("yolov8n.pt")` against COCO pet classes (14 bird, 15 cat, 16 dog,
  17 horse, 18 sheep, 19 cow) at confidence ≥ 0.45 (configurable).
- **Pass**: EXIF stripped via Pillow, thumbnail generated, upload to private Cloudinary
  (delivery type `private`), `PetDetectionLog(passed=True)`, signed preview URL returned.
- **Fail**: bytes discarded before any storage write, `PetDetectionLog(passed=False)`,
  `NoPetDetectedError` → HTTP 422 `{"error":{"code":"no_pet_detected","message":…,
  "detected_labels":[…]}}` so the user can retry instantly. Zero penalties.
- Frontend UX (`PhotoUpload`): the 422 renders a friendly `no-pet-error` box ("No strikes, no
  bans — just pick another photo") and the picker stays open for an immediate retry; a passing
  photo shows a "Pet detected ✓" badge. E2E journey ④ drives both photos through the real
  YOLOv8n model (`e2e/fixtures/dog.jpg` passes @ ~0.81, `landscape.jpg` → 422).

## 9. Payments — Rewards (Stripe Test + GCash / QR Ph)

- `PaymentDriver` protocol with `StripeDriver` (SDK, test mode) and `PayMongoDriver`
  (httpx Basic auth; GCash Checkout + QR Ph Payment Intent).
- `RewardService` creates `RewardTransaction(status='pending')` atomically with
  `select_for_update`, then delegates to the driver.
- Webhooks (`/api/webhooks/stripe`, `/api/webhooks/paymongo`) are CSRF-exempt, signature-
  verified (Stripe `Stripe-Signature`; PayMongo HMAC-SHA256 of `{t}.{payload}` in
  `Paymongo-Signature: t=…,te=…`), deduplicated via `WebhookEvent(provider, event_id)`, and
  acknowledged with 200 in <50 ms while `process_reward_webhook` runs on the `webhooks`
  Celery queue with `select_for_update`.
- Frontend UX: `RewardCheckoutModal` (amount + provider) → Stripe redirects off-site, or
  GCash shows the QR payload in `GcashQrModal` and polls `GET /api/rewards/{id}/status` every
  2 s until terminal, showing "Payment received — thank you!" on `succeeded`.
  `POST /api/webhooks/paymongo` is exercised end-to-end in E2E journey ⑤ against a local stub
  (valid signature → 200 + `succeeded`; forged signature → 400).

## 10. Frontend (React 19 + TS) Guide

- Centralized axios client at `src/lib/api/client.ts` (`baseURL: '/api'`, credentials, CSRF
  headers, `ApiError` normalization incl. `no_pet_detected` labels, 401/`session_expired`
  handling). All calls via `src/features/{domain}/api.ts`; DTOs come only from the generated
  `src/lib/api/schema.d.ts` (`npm run typegen` over `backend/schema.yml`).
- Pages: `/` Home (emergency + outreach rails), `/flyers` Gallery (mode filter + FTS search +
  cursor pagination), `/flyers/:id` Public Flyer + QR + print/export + owner resolve/delete +
  reward checkout, `/builder` 3-step wizard (photo gate → pet form → details/reward),
  `/my-flyers`, `/rewards/success`, `/rewards/cancel`, `/auth/login` (also handles the Google
  `?code=` callback), `/auth/register`.
- React 19 idioms: `useActionState` forms (dispatch wrapped in `startTransition` so `pending`
  works), `useOptimistic` publishing card on flyer create, ref-as-prop, React Compiler in
  `vite.config.ts` (disabled under Vitest so coverage maps to source). TanStack Query
  `queryOptions` factories; reward status polls every 2 s while `pending`. Zod + RHF forms.
  QR codes rendered as SVG data-URLs via the `qrcode` package (`src/components/QrImage.tsx`).
  `@media print` A4-exact stylesheet (`@page { size: A4 }`, `.print-sheet`, `.no-print`) +
  Print button.
- Dev proxy: Vite proxies `/api`, `/media`, `/ws` to the backend; the origin is env-driven
  (`PAWPRINT_API_URL`, default `http://127.0.0.1:8000`) so Playwright E2E can run the API on
  another port.
- Visual system per the `taste` skill: one type scale, one card recipe, equal edges,
  tactile hover/press, skeleton/empty/error states, dual palette (emergency crimson/amber vs
  outreach sage/teal/terracotta).

## 11. Testing & Coverage

- Backend: `cd backend && .venv/bin/python -m pytest tests/ -q --cov=apps --cov-fail-under=80`
  → **90 passed, 94.2% total** (100% on all `services.py`, `drivers.py`, `PetDetectionService`,
  the Cloudinary storage driver);
  `django_assert_max_num_queries` ceilings on list/detail endpoints; 429 tests for the
  `auth_write` (20/min) and `upload` (10/min) throttles; webhook idempotency tests (duplicate
  `(provider, event_id)` → single processing); 422-before-storage tests (non-pet bytes never
  reach Cloudinary); Cloudinary driver unit tests (SDK mocked, 100% on the driver);
  `responses`/MockTransport for Stripe/PayMongo HTTP; `factory-boy` factories.
- Frontend: `npm run test:run` → **65 Vitest tests, 6 files** (RTL + MSW, jsdom);
  `npm run test:coverage` → **88.5% stmts / 81.0% branches / 85.4% funcs / 89.2% lines**
  (thresholds 70/60/70/70) with **`src/features/rewards/**` at 100%** (per-glob threshold).
  `npx tsc -b --noEmit` clean; `npm run build` green.
- E2E: `npm run test:e2e` (Playwright, `frontend/playwright.config.ts`) → **6 journeys /
  7 tests, all green**, fully self-contained: a stub PayMongo API (`e2e/stub-paymongo.mjs` on
  :9100), the Django backend on :8010 with `PAWPRINT_TESTING=1` (eager Celery, locmem, local
  PG :5433), and the Vite dev server on :5173 proxying to :8010. Journeys: ① guest browse →
  filter → search → detail+QR, ② register → logout → login (demo account), ③ create an
  emergency flyer through the 3-step wizard (YOLOv8-gated upload) → public detail page,
  ④ landscape photo → 422 `no_pet_detected` retry UX → dog photo passes, ⑤ GCash reward
  checkout → QR modal → HMAC-signed PayMongo webhook flips status to `succeeded` (and a
  forged signature is 400), ⑥ open the flyer's `qr_target_value` like a scanner → public
  detail page with SVG QR.
- Static analysis: `mypy apps`, `ruff check apps`, `npm run build` (0 TS errors).
- Performance spot-check (Phase 7, local PG :5433): `EXPLAIN ANALYZE` on the public gallery
  query shows an index scan on `flyer_status_created_idx` + PK lookups for pet/owner/creator —
  **0.21 ms execution, 14 shared buffer hits** at seed scale; FTS uses the
  `pet_search_vector_gin` GIN index (planner seq-scans the 2-row seed table, switches to the
  bitmap index at scale); the reward webhook path holds `select_for_update` inside a short
  transaction and dedupes on the unique `(provider, event_id)`.

## 12. Tutorial (Living Build Log)

- **Phase 0** — Repo initialized. `pawprint` skill created at `.opencode/skills/pawprint/SKILL.md`;
  `AGENTS.md` points to it and the `taste` skill (`.agents/skills/design-taste-frontend`).
  `docs/DOCUMENTATION.md` (these 12 sections) + root `package.json` with
  `docs:pdf` (md-to-pdf) → `docs/documentation.pdf` generated and committed.
- **Phase 1** — Backend foundation in `backend/`: `pyproject.toml` (Django 5.2 LTS, DRF,
  drf-spectacular, psycopg, redis, celery, channels(+redis), django-allauth[socialaccount],
  django-cors-headers, cloudinary, Pillow, qrcode, stripe, httpx, ultralytics,
  weasyprint + pytest/factory-boy/responses/ruff/mypy dev deps). `django.contrib.admin`
  fully removed. `docker-compose.yml` (postgres:16, redis:7, mailpit, celery, web) +
  `.env.example`. Models with constraints/indexes: `users.User` (UUID PK, email login,
  google_id, stripe_customer_id), `pets.Pet` (SearchVector GIN, JSON GIN, composite
  `(status, created_at)`), `flyers.Flyer` (CheckConstraint reward>0, `(mode,status,created_at)`,
  `(creator,mode)`), `rewards.RewardTransaction` (unique provider_reference, select_for_update
  in service), `webhooks.WebhookEvent` (unique `(provider, event_id)`), `vision.PetDetectionLog`.
  factory-boy factories + `seed_demo` command. Tests: `test_health.py` (incl. admin-absent
  assertion, 0-query health) + `test_factories.py`. Local PG on :5433 used for tests;
  pytest switches to locmem cache / in-memory channels / eager Celery / filesystem storage.
- **Phase 2** — Auth: `POST /api/auth/register|login|logout`, `GET /api/auth/me` (401 +
  `session_expired` for guests via custom `SessionAuthenticationWith401`),
  `GET|POST /api/auth/google/url|callback` — Google/Gmail OAuth 2.0 via django-allauth
  SocialAccount with one-click Gmail registration, email-account linking, and existing
  sign-in. `auth_write` scope throttle 20/min (verified 429 on the 21st request).
  14 auth integration tests.
- **Phase 3** — Flyer core: cursor-paginated public `GET /api/flyers` (Guest allowed,
  `select_related('pet','creator')` + `only()`, SearchVector FTS `?q=`, `?mode=` filter,
  `django_assert_max_num_queries` ceilings), public `GET /api/flyers/{id}` (QR landing),
  creator-only `POST /api/flyers/new`, `PATCH/DELETE /api/flyers/{id}/edit`
  (`IsOwnerOrReadOnly`), `GET /api/flyers/mine`. `FlyerService` dispatches Celery
  `generate_flyer_assets` (queue `flyers`) → WeasyPrint A4 PDF + Playwright A4@300dpi PNG →
  private cloud storage → `flyer.generated` broadcast over Channels (`ws/flyers/`). A4
  templates `templates/flyers/{emergency,outreach}.html` with dual palettes.
- **Phase 3.5** — YOLOv8 gatekeeper: `PetDetectionService` singleton `YOLO("yolov8n.pt")`,
  COCO pet classes {14,15,16,17,18,19} @ conf ≥ 0.45 (configurable). Pass → EXIF stripped
  (Pillow) → private cloud storage → thumbnail task (queue `images`) → signed URL + detected
  labels. Fail → bytes discarded before any storage write, `PetDetectionLog(passed=False)`, HTTP 422
  `no_pet_detected` with detected labels; zero strikes/bans. `POST /api/pets/photos`
  (auth, `upload` throttle 10/min — 429 on 11th). ultralytics 8.4.215 + torch 2.15 CPU
  installed in the venv.
- **Phase 4** — Rewards: `PaymentDriver` protocol + `StripeDriver` (Checkout Session, test
  mode) + `PayMongoDriver` (httpx Basic auth; GCash checkout session + QR Ph payment intent;
  injectable client for MockTransport tests). `RewardService.create_reward` creates a
  pending `RewardTransaction` atomically then delegates to the driver.
  `POST /api/rewards`, `GET /api/rewards/{id}/status` (payer/creator only),
  `GET /api/rewards/mine`. Webhooks `POST /api/webhooks/stripe|paymongo` — CSRF-exempt,
  signature-verified (Stripe `Stripe-Signature`, PayMongo HMAC-SHA256 `te=`),
  deduped via `WebhookEvent(provider, event_id)`, 200 in <50 ms, processing on the
  `webhooks` queue with `select_for_update`.

- **Phase 5** — Frontend app in `frontend/` (React 19 + TS + Vite + Router v7 + TanStack Query
  v5 + Axios + Zustand + RHF/Zod + Tailwind v4, React Compiler on for app builds): pages Home,
  Gallery (mode filter + FTS + cursor), Flyer detail (SVG QR, print/PDF/PNG, owner
  resolve/delete double-click, reward modal), 3-step Builder wizard
  (`useActionState` + `useOptimistic` publishing card), My flyers, Login (incl. Google
  `?code=` callback), Register, Reward success/cancel. Features: `auth`, `pets`
  (`PhotoUpload` 422-retry UX), `flyers`, `rewards` (`RewardCheckoutModal` + `GcashQrModal`
  with 2 s status polling). DTOs generated via `openapi-typescript` →
  `src/lib/api/schema.d.ts`; `@/` alias; `@media print` A4 sheet + `.no-print` chrome.
  Backend contract tweaks: `@extend_schema` on reward status endpoints so `RewardStatus` is in
  the generated schema; `seed_demo` now writes real `qr_target_value`s; `PAWPRINT_TESTING=1`
  env switch in `config/settings.py`.
- **Phase 6** — Tests. Backend re-verified: **79 passed, 94.0%** (100% services/drivers/
  vision), ruff + mypy clean. Frontend: 6 Vitest files / **65 tests** (MSW handlers in
  `src/test/`), coverage **88.5% stmts / 81.0% br / 85.4% fn / 89.2% lines** with
  **`features/rewards` at 100%** (per-glob threshold in `vite.config.ts`); `tsc -b` clean;
  `npm run build` green. Playwright E2E (`playwright.config.ts`, `npm run test:e2e`): 6
  journeys / 7 tests green, self-contained — stub PayMongo on :9100
  (`e2e/stub-paymongo.mjs`), backend on :8010 with `PAWPRINT_TESTING=1` (eager Celery, locmem,
  PG :5433), Vite on :5173 proxying `/api`+`/media` (`PAWPRINT_API_URL`). Fixtures verified
  against real YOLOv8n (`e2e/fixtures/dog.jpg` → dog @0.81, `landscape.jpg` → 422). Vite proxy
  origin is env-driven; vitest excludes `e2e/**`.
- **Phase 7** — Hardening verification + docs. `EXPLAIN ANALYZE` on the public gallery: index
  scan on `flyer_status_created_idx`, PK joins, **0.21 ms / 14 buffer hits** at seed scale; FTS
  GIN index `pet_search_vector_gin`; reward webhook path = short transaction +
  `select_for_update` + unique `(provider, event_id)` dedupe. Confirmed by tests: throttles
  429 (auth 20/min, upload 10/min), webhook idempotency, 422-before-storage (non-pet bytes
  never stored), print CSS (`@page A4`, `.print-sheet`, `.no-print`), 401 `session_expired`
  flag. Docs updated (all 12 sections) + `docs/documentation.pdf` regenerated.
- **Phase 8** — Storage migration: MinIO/S3 → **Cloudinary**. `docker-compose.yml` drops the
  `minio`/`minio-setup` services and volume; `django-storages[s3]` + `boto3` replaced by the
  `cloudinary` SDK. New Django `Storage` backend `apps/common/cloudinary_storage.py`
  (`CloudinaryStorage`): uploads with delivery `type="private"`, `overwrite=True`; reads and
  URLs are HMAC-signed (`cloudinary_url(..., sign_url=True, expires_at=…)`); pdf/png/jpg map to
  resource_type `image`. Config via `CLOUDINARY_URL` (or discrete `CLOUDINARY_CLOUD_NAME` /
  `CLOUDINARY_API_KEY` / `CLOUDINARY_API_SECRET`) in `.env`; `PAWPRINT_TESTING=1` still uses
  filesystem storage. 11 new driver unit tests (SDK mocked) → driver at **100%**; suite:
  **90 passed @ 94.2%**, ruff + mypy clean. (The "p variable is not set" compose warnings were
  an unquoted `$` in `DJANGO_SECRET_KEY` inside `.env`, fixed by regenerating the key as hex.)
- **Phase 9** — `manage.py` hardening: (1) added `django.contrib.postgres` to
  `INSTALLED_APPS` — `pets.Pet` uses `SearchVectorField`/`GinIndex`, and without the app every
  `manage.py` command aborted with `postgres.E005` (pytest never caught it because
  pytest-django skips system checks); (2) settings now `load_dotenv(root .env)`
  (python-dotenv), so host-side `cd backend && python manage.py migrate` just works —
  compose containers are unaffected (real env vars win; web/celery also pin
  `POSTGRES_HOST=postgres`/`PORT=5432` via a compose `environment:` anchor, so a
  host-oriented `.env` can't break them); (3) Playwright backend server env pins
  `postgres`/`postgres` @ `127.0.0.1:5433` + `whsec_dev` webhook secrets so E2E stays
  self-contained. Verified: `manage.py check` → 0 errors (only the intentional urls.W002
  warnings), `migrate` + `seed_demo` exit 0, **90 pytest passed @ 94.2%**, ruff + mypy
  clean, **Playwright 7/7 green**.
- **Phase 10** — Host-side run fixes. With dotenv loading the root `.env`, host-side
  `python manage.py runserver` must point at **host-published** services: `.env` /
  `.env.example` now use `REDIS_URL=redis://127.0.0.1:6379/0` and `EMAIL_HOST=127.0.0.1`
  (compose's `redis`/`mailpit` hostnames don't resolve on the host); the compose
  `x-app-environment` anchor pins `redis:6379` / `mailpit:1025` inside web/celery so one
  `.env` serves both worlds. Verified host-side (no `PAWPRINT_TESTING`): `/api/health` →
  ok, demo login + `/api/auth/me` → 200 (throttle cache on Redis works). Google OAuth
  `redirect_uri_mismatch` is console config, not code: the frontend sends
  `redirect_uri = <origin>/auth/login`, so register exactly `http://localhost:5173/auth/login`
  (and the `127.0.0.1` variant) as an Authorized redirect URI of the OAuth client in
  Google Cloud Console. Health route is `/api/health` (bare `/health` is a 404).
- **Phase 11** — Upload hardening (no offline fallback; Cloudinary only): (1) Cloudinary
  SDK ≥1.47 `cloudinary_url()` returns a `(url, options)` tuple — the storage driver now
  unpacks it (it was returning a stringified tuple in API responses; fixed + regression
  tested with both return shapes, driver still 100%); (2) storage failures (e.g. wrong
  `CLOUDINARY_URL`) now return a JSON **502 `storage_unavailable`** envelope instead of an
  HTML 500 page (`apps/common/exceptions.py`); (3) the 422 `no_pet_detected` message is
  exactly "No pet detected in the photo. Please upload a clear photo of your pet." (asserted
  verbatim in backend tests, and the frontend asserts it renders exactly once); (4) the
  axios client never shows raw "Request failed with status code 500" anymore — non-JSON
  errors fall back to "Something went wrong. Please try again.". Verified live against real
  Cloudinary creds: pet photo → 201 signed URL; non-pet → 422 single message; celery
  thumbnail task → succeeded. Suite: **93 pytest passed @ 94.3%**, 66 vitest, Playwright
  7/7, ruff + mypy + tsc clean.

- **Phase 12** — A4 flyer print redesign (single page, unique per pet): both
  `templates/flyers/emergency.html` (lost pet) and `templates/flyers/outreach.html`
  (adoption) rebuilt for print fidelity: full-bleed A4 (210×297mm, zero margin),
  equal 15mm side edges, bold header band, large pet photo leading (no image
  captions), oversized pet name, detail cards, QR code + contact footer, bottom
  strip. Each flyer gets a deterministic design variant (1–4 derived from the flyer
  UUID) so every print looks unique — a different colored corner accent badge and a
  unique seal number — while keeping the same clear information hierarchy.
  `config/settings.py` / `apps/flyers/tasks.py` pass `design_variant` to the template
  context. Verified live: both modes render exactly **1 page at A4** via WeasyPrint.
- **Public visibility on create**: newly created flyers are now `ACTIVE` immediately
  (`apps/flyers/services.py`), so they appear in the lost/adoption public gallery
  right away instead of being hidden while assets generate. QR target is set after
  the flyer id exists. Assets (PDF/PNG) still generate in the background via Celery.
  Suite: **97 pytest passed @ 94.0%**, 66 vitest, Playwright 7/7, ruff + mypy + tsc
  clean.

**Final status:** backend **97 passed @ 94.0%** (100% services/drivers/vision/storage);
frontend **66 vitest tests** @ 88.5/81.0/85.4/89.2 (rewards 100%) + **7 Playwright tests
green**; `ruff` + `mypy` clean; `tsc -b` + `vite build` green; `npm run docs:pdf` regenerated.