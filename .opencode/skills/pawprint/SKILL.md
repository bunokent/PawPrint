---
name: pawprint
description: Engineering and UI conventions for PawPrint. Always follow the `taste` skill for UI design. Every code change MUST ship with tests, a regenerated documentation.pdf, an updated Tutorial section, and a clean git commit.
---

# PawPrint Engineering & Design Skill

## UI & Visual Design Mandate (`taste` skill)
- **Read and enforce the `taste` skill** on every frontend task and A4 flyer layout:
  - Craft an editorial, trustworthy, emotionally resonant aesthetic tailored to pet rescue and emergency recovery.
  - Maintain clear visual distinction between **Emergency Lost-Pet Mode** (urgent crimson/amber accents, high-contrast scannability, prominent reward & last-seen badges) and **Adoption Outreach Mode** (warm sage/teal/terracotta accents, personality tags, welcoming shelter/foster framing).
  - Enforce strict typographic hierarchy, balanced padding, accessible contrast ratios, tactile hover/focus states, and clean skeleton/empty/error states.

## User Access Model (STRICT — 2 Modes Only)
- **No Admin System**: Do NOT include `django.contrib.admin`, admin dashboards, staff flags, or moderation strike/ban systems.
- **Guest Mode**: Unauthenticated visitors (`AllowAny` on read-only endpoints) can browse lost/adoptable flyers, search/filter pets, view flyer details, and scan QR codes.
- **Registered Mode**: Single unified user model (`User`) supporting both standard email registration and **Google/Gmail OAuth 2.0 registration & login**. Any authenticated user (`IsAuthenticated`) can create lost-pet alerts, post adoptable pets (acting as owner, foster, or shelter volunteer), generate flyers, and fund rewards. Object-level mutations (`PATCH`/`DELETE`) are restricted to the flyer's creator (`IsOwnerOrReadOnly`).

## Django 5.2+ & ORM Best Practices (MANDATORY)
- **Strict Type Annotations (Python 3.12+)**: Type-annotate all services, selectors, DTOs (`@dataclass(frozen=True)`), and views.
- **Selector + Service Layer Pattern**:
  - `selectors/` handles ALL database reads using optimized QuerySets: `select_related()` for FKs/OneToOne, `prefetch_related()` for reverse/M2M, `only()`/`defer()` where appropriate, PostgreSQL `SearchVector` + GIN index for full-text search (never `icontains` table scans), and cursor pagination.
  - `services/` handles ALL writes wrapped in `@transaction.atomic`, external API calls, and Celery task dispatches.
  - Views/ViewSets (`APIView` / `GenericViewSet`) stay thin (≤15 lines): validate via Serializer → call Selector/Service → return Serialized response. Zero raw ORM queries in views.
- **Database Integrity**: Use `UniqueConstraint`, `CheckConstraint`, composite indexes, and `select_for_update()` on financial/idempotency writes.
- **OpenAPI Schema**: `drf-spectacular` generates `schema.yml` automatically for `openapi-typescript`.
- **Celery Routing**: Centralized `CELERY_TASK_ROUTES` in `config/settings.py` (`flyers`, `webhooks`, `images`).

## React 19 + TypeScript + Axios Best Practices (MANDATORY)
- **Centralized Axios Instance (`src/lib/api/client.ts`)**:
  - Single configured `axios.create({ baseURL: '/api', withCredentials: true, xsrfCookieName: 'csrftoken', xsrfHeaderName: 'X-CSRFToken' })`.
  - Typed request/response interceptors for global error normalization (`ApiError`) and automatic 401 session-expiry handling.
  - All API calls go through domain API modules (`src/features/{domain}/api.ts`) using the Axios client — never raw `fetch` or inline URLs in components.
- **React 19 Modern Idioms**:
  - `useActionState` for form submissions with pending/error state.
  - `useOptimistic` for optimistic UI updates (instant flyer card insert on create).
  - React Compiler enabled in `vite.config.ts` (auto-memoization — avoid redundant `useMemo`/`useCallback`).
  - Ref as prop (no `forwardRef` in React 19).
- **TanStack Query v5 + Type Safety**:
  - Use `queryOptions` factories for type-safe query keys and Axios fetchers.
  - Use `useMutation` with `onMutate` + `onError` context rollback for optimistic mutations.
  - Generate all API DTOs via `openapi-typescript` from `drf-spectacular` schema (`src/lib/api/schema.d.ts`) — never hand-write backend DTOs.
  - Zod + React Hook Form for all forms.

## AI Pet Detection Gatekeeper (YOLOv8 — Replaces Moderation/Bans)
- Every uploaded pet photo passes `PetDetectionService.validate_pet_image(image_bytes)` BEFORE uploading to S3.
- Uses `ultralytics.YOLO("yolov8n.pt")` (singleton/cached model instance) checking COCO animal/pet class IDs:
  - `14`: bird, `15`: cat, `16`: dog, `17`: horse, `18`: sheep, `19`: cow (configurable confidence threshold, default `>= 0.45`).
- **If a pet is detected**: Strip EXIF metadata via Pillow, generate thumbnail, and upload to private S3.
- **If NO pet is detected**: Discard immediately (never save to S3) and raise `NoPetDetectedError` → HTTP `422 Unprocessable Entity` with clear message (`"No pet detected in the photo. Please upload a clear photo of your pet."`) and detected labels so the user can retry.
- **Zero penalties**: No user strikes, no suspensions, no banning. Users can immediately select another photo.

## Git Commit Discipline (MANDATORY)
- Commit after EVERY phase AND after EVERY major/minor impactful change (e.g., new service, model migration, API integration, UI feature, or test suite milestone).
- Never batch multiple phases into one giant commit. Keep git history clean, atomic, and bisectable.

## Testing & Living Documentation (MANDATORY)
- Backend: `pytest -n auto --cov=apps --cov-fail-under=80` (100% coverage on Services, Drivers, and `PetDetectionService`). Assert query count ceilings (`django_assert_max_num_queries`) on list/detail endpoints.
- Frontend: `npm run test:run` (≥70% overall, 100% on `features/rewards`) + Playwright E2E for all 6 critical journeys.
- Update all 12 sections of `docs/DOCUMENTATION.md` (including the **Tutorial** build log) and regenerate `docs/documentation.pdf` via `npm run docs:pdf` before committing each phase.
