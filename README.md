# Scene Slice & Download

A video scene-slicing application with a TypeScript React frontend, a TypeScript
Hono API, PostgreSQL with Prisma, and Python Lambda workers using PySceneDetect
and FFmpeg.

The intended experience is: upload a video directly to S3, detect scene boundaries,
preview virtual cuts in the browser, then request physical clips and a ZIP download
with an email notification. No accounts are planned for V1.

**Current state:** the repository has a frontend starter, working video metadata
endpoints, a local database, and tested worker media operations. Uploads, browser
previews, cloud storage, and the end-to-end processing flow still need integration.

## Where to look

| Piece                                           | Responsibility and starting point                                                                                                      |
| ----------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| [Frontend](frontend/README.md)                  | React + Vite + shadcn/ui starter. Begin with [App.tsx](frontend/src/App.tsx). The video UI and TanStack Query integration are pending. |
| [Backend](backend/README.md)                    | Hono API with HTTP, service, and database storage layers. Includes sample requests and migration instructions.                         |
| [Database schema](backend/prisma/schema.prisma) | Video lifecycle, scene cutpoints, slice metadata, and uniqueness constraints. Checked-in migrations live alongside it.                 |
| [Local database](compose.yaml)                  | PostgreSQL 17 with a readiness check, loopback-only port, and persistent named volume.                                                 |
| [Workers](workers/README.md)                    | Python detection and slicing handlers, media operations, integration contracts, tests, and a Lambda container recipe.                  |
| [Makefile](Makefile)                            | Database lifecycle, formatting, dependency installation for workers, and verification commands.                                        |
| [Project guidance](AGENTS.md)                   | Coding/commit conventions, V1 architecture, API contracts, and known design risks.                                                     |

## Run locally

Use Node 22 (22.13+), npm, and Python 3.12, as declared in `.nvmrc` and `.python-version`.
Run `nvm install && nvm use` if you use nvm. Install
Docker with Compose, and FFmpeg/ffprobe on your PATH. Start the Docker engine first.
Docker currently runs only PostgreSQL; the API and frontend run on your machine.

From the repository root:

```sh
make db-up
npm ci --prefix backend
npm ci --prefix frontend
make workers-install
```

Configure the backend and apply its migrations:

```sh
cd backend
cp .env.example .env
npm run generate
npm run db:deploy
npm run dev
```

If `.env` already exists, update its database settings rather than overwriting it.
The example selects local PostgreSQL at `localhost:5432`; the database, user, and
password are all `video_slicer`. For Neon, select `DATABASE_DRIVER=neon` and provide
pooled runtime and direct migration URLs as described in the backend guide.

In a separate terminal, from the repository root:

```sh
cd frontend
npm run dev
```

The API listens on `http://localhost:3000`; Vite prints the frontend URL.
Check API health with `curl http://localhost:3000/api/health`.
The frontend is not connected to the API yet. Worker tests can run locally, but
invoking the handlers requires implementing their storage contact points first.

Use `make db-logs` from the root to follow PostgreSQL logs and `make db-down` to
stop it. Stopping preserves the database volume. If port 5432 is occupied, change
the published port in Compose and both database URLs in the backend `.env`.

## Follow the backend example

The request flow is **HTTP route → service → database storage → Prisma → PostgreSQL**.

1. [HTTP routes](backend/src/http/videos.ts) parse requests and map results to HTTP responses.
2. [Video service](backend/src/services/videos.ts) validates metadata, selects object keys, and shapes public responses.
3. [Video storage](backend/src/storage/videos.ts) runs Prisma queries and recovers duplicate registrations using the session/file uniqueness constraint.
4. [Database client](backend/src/storage/prisma.ts) lazily creates and reuses the PostgreSQL or Neon adapter/client.

[Application wiring](backend/src/app.ts) connects those layers and handles errors.
[The Lambda entry point](backend/src/index.ts) exports the handler;
[the development server](backend/src/dev.ts) loads local environment variables.
“Storage” in this backend example means database persistence; S3 access is pending.

| Endpoint              | Implemented behavior                                                                                                                    |
| --------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| `GET /api/health`     | Process health without a database query.                                                                                                |
| `POST /api/videos`    | Validate metadata and create or recover an `UPLOADING` record. Returns `201` for a new record or `200` for recovery; no upload URL yet. |
| `GET /api/videos/:id` | Return public status, cutpoints, and progress, or `404` for a missing record.                                                           |

See the backend guide for a complete registration request. Declared file limits
are 500,000,000 bytes and 1,800 seconds; workers verify the actual media later.

## Follow the workers

- [Detection handler](workers/detect.py): downloads input, probes it, detects cuts,
  and persists the results. It produces boundaries, not physical clips.
- [Slicing handler](workers/slice.py): loads persisted cuts and checkpoints, cuts
  new clips, reuses completed ones, and builds an uncompressed ZIP.
- [Media operations](workers/media.py): ffprobe validation, PySceneDetect boundary
  detection, interval validation, and FFmpeg splitting, independent of AWS access.
- [Storage contacts](workers/storage.py): explicit `WIRE` comments and
  `NotImplementedError` placeholders for S3 downloads/uploads and database writes.

Both Lambda handlers accept `{ "video_id": "<uuid>" }`. The worker guide explains
their contracts, retry boundaries, and shared image configuration. Job ownership,
durable dispatch, failure reporting, and email delivery remain to be wired.

## Format and verify

After installing backend, frontend, and worker dependencies, run from the root:

```sh
make format          # Prettier for TypeScript; Ruff for Python
make check           # Formatting, lint, types, tests, and builds across the project
make backend-check   # Backend checks alone
make frontend-check  # Frontend checks alone
make workers-check   # Worker checks alone; requires FFmpeg/ffprobe
```

Formatting rules are committed in the root `prettier.config.mjs`; the frontend
extends them with Tailwind class sorting. `.editorconfig` provides editor defaults,
including tabs for Makefiles and four spaces for Python. ESLint checks both
TypeScript projects, and Ruff settings live in `workers/pyproject.toml`.
These rules are shared project settings; editor extensions and format-on-save
remain personal choices. No Git hooks or editor-specific settings are required.

GitHub Actions runs `make check` on pull requests and pushes to `main`, using the
declared Node/Python versions. It installs FFmpeg and needs no cloud credentials
or running database. Frontend typechecking checks both referenced TS projects.

Backend tests use injected database storage; worker tests use real
PySceneDetect/FFmpeg with generated videos and local
substitutes for cloud storage. These tests do not verify live Neon or S3 integration.

## Remaining integration and deployment

Next work includes the video UI and TanStack Query, direct S3 uploads and signed
playback/download URLs, worker storage/database implementations, event adapters
and dispatch, slicing/download endpoints, email, and session/asset expiry.
Use the design risks in the project guidance when making those decisions.

The backend can build a Lambda bundle, and the workers include a Dockerfile with
FFmpeg and AWS's Python runtime interface client. Cloud infrastructure, permissions,
triggers, and frontend hosting are not provisioned. The existing backend deploy
script targets a function named `hello`; review it before using it. Worker image
builds and live database migrations have not been verified in this environment.
