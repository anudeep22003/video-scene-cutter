# Backend scaffold

Hono + TypeScript API with Prisma 7 and PostgreSQL/Neon driver adapters. This is a working
metadata example, not the upload/processing pipeline.

## Run locally

Use Node 22.12+ (or a Prisma-supported newer LTS release), npm, and a running Docker
engine with Docker Compose.

```sh
# From the repository root:
make db-up
cd backend
npm ci
cp .env.example .env
npm run generate
npm run db:deploy
npm run dev
```

The root `compose.yaml` runs PostgreSQL 17 on `localhost:5432`, with local-only
database, user, and password all set to `video_slicer`. The port binds only to
loopback. `make db-up` waits for database readiness; migrations remain explicit.
If you already have a `.env`, update its database settings to match `.env.example`
rather than overwriting any other configuration.

From the repository root, `make db-down` stops the database and preserves data in
the named Docker volume; `make db-logs` follows its logs. If port 5432 is already
occupied, change the published port in `compose.yaml` and both URLs in `.env`.

`DATABASE_DRIVER=postgres` selects the TCP PostgreSQL adapter for Compose.
For Neon, use `DATABASE_DRIVER=neon` with a pooled `DATABASE_URL` and a direct
`DIRECT_URL`. The driver defaults to `neon` when unset for existing deployments.

`db:deploy` applies checked-in migrations to the configured database. Use a
development database. For subsequent schema changes, edit `prisma/schema.prisma`,
run `npm run db:migrate -- --name describe_change`, then `npm run generate`.
Migration development may require a separate shadow database with Neon.

## Follow the example through the layers

- `src/http/videos.ts`: request parsing, route parameters, HTTP status codes.
- `src/services/videos.ts`: metadata validation, object naming, public responses.
- `src/storage/videos.ts`: Prisma queries and unique-conflict recovery.
- `src/storage/prisma.ts`: lazy, reusable PostgreSQL/Neon Prisma client.
- `src/app.ts`: dependency wiring and consistent JSON errors.
- `src/index.ts`: Lambda handler; `src/dev.ts`: local HTTP server and dotenv loading.

Flow: HTTP route -> video service -> video storage -> Prisma -> PostgreSQL/Neon. Storage here
means database persistence. Future S3 access should live in its own storage module,
called by the service; routes should not contain Prisma or AWS SDK calls.
The small injected storage dependency also allows service/HTTP tests without a DB.

## Try it

```sh
curl http://localhost:3000/api/health
curl -i http://localhost:3000/api/videos \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"550e8400-e29b-41d4-a716-446655440000","file_hash":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","size_bytes":1000,"duration_sec":60,"mime_type":"video/mp4"}'
curl http://localhost:3000/api/videos/VIDEO_ID_FROM_RESPONSE
```

- `POST /api/videos`: validates declared metadata, creates `UPLOADING` metadata,
  returns `201` with `{ video_id, status }`. The same session/hash returns `200`
  and the existing record, including under concurrent registration.
- `GET /api/videos/:id`: returns status, cutpoints, and progress, or `404`.
  `size_bytes` is a decimal string because JSON cannot encode bigint.
- `GET /api/health`: process health only; does not contact Neon.
- Malformed JSON returns `400`; invalid metadata/UUIDs return `422`;
  unexpected errors return a generic `500` and are logged server-side.

Limits are 500,000,000 bytes and 1,800 seconds. Hashes are 64 hexadecimal characters,
normalized to lowercase. MOV inputs retain a `.mov` key; MP4 inputs use `.mp4`.
Metadata remains untrusted until a worker verifies the actual uploaded video.

## Extend next

The sample intentionally omits upload/playback/download URLs, S3 notifications,
slice-list and slicing endpoints, worker dispatch, email, session expiry, and asset expiry.
Python detection/slicing scaffolds live in [`../workers/README.md`](../workers/README.md);
their S3/database contact points still need wiring.
Registration creates metadata only; it cannot upload or advance processing yet.
Add real S3 signing to registration and status responses before connecting the SPA.
Implement slicing only once job dispatch is available; do not return a fake `202`.
Apply the access, retry, and retention decisions recorded in the root `AGENTS.md`
before exposing this scaffold publicly. Currently an unguessable video ID grants
access to its public status response; there is no account or session authorization.

## Verify and package

From the repository root, `make format` formats both projects and `make check`
runs backend schema validation, typechecking, tests, formatting checks, and build.
Tests use injected storage; they do not verify live database queries or migrations.

`npm run build` generates Prisma and creates an ESM Lambda bundle targeting Node 22.
The bundle includes a `createRequire` bridge for bundled CommonJS dependencies.
Use a compatible Lambda runtime and provide `DATABASE_URL` in its environment;
`.env` is loaded only by local development and Prisma CLI commands.
The existing `npm run deploy` still updates the function named `hello`; review that
target before deploying. No infrastructure is provisioned by this scaffold.

References: [Prisma configuration](https://www.prisma.io/docs/orm/v7/reference/prisma-config-reference)
and [Prisma connection setup](https://www.prisma.io/docs/orm/v7/prisma-client/setup-and-configuration/databases-connections).
