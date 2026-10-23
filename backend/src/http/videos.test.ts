import assert from "node:assert/strict"
import { test } from "node:test"
import { createApp } from "../app"
import type { Video } from "../generated/prisma/client"
import { VideoService } from "../services/videos"

const id = "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d"
const input = {
  session_id: "550e8400-e29b-41d4-a716-446655440000",
  file_hash: "a".repeat(64),
  size_bytes: 1000,
  duration_sec: 60,
  mime_type: "video/mp4",
}
const video: Video = {
  id,
  sessionId: input.session_id,
  fileHash: input.file_hash,
  status: "UPLOADING",
  errorMessage: null,
  sizeBytes: 1000n,
  durationSec: 60,
  mimeType: "video/mp4",
  rawObjectKey: `raw/${id}.mp4`,
  zipObjectKey: null,
  detectedCuts: null,
  totalSlices: 0,
  slicesCompleted: 0,
  userEmail: "private@example.com",
  createdAt: new Date(),
  updatedAt: new Date(),
}

function fixture(created = true, storedVideo: Video | null = video) {
  let writes = 0
  const service = new VideoService({
    async createOrRecover(data) {
      writes++
      assert.equal(data.sizeBytes, 1000n)
      assert.equal(data.fileHash, input.file_hash)
      assert.match(data.rawObjectKey, /^raw\/[\da-f-]+\.mp4$/)
      return { video, created }
    },
    async findById(requestedId) {
      assert.equal(requestedId, id)
      return storedVideo
    },
  })
  return { app: createApp(service), writes: () => writes }
}

test("registration maps metadata to storage and reports creation/recovery", async () => {
  for (const created of [true, false]) {
    const { app, writes } = fixture(created)
    const response = await app.request("/api/videos", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        ...input,
        file_hash: input.file_hash.toUpperCase(),
      }),
    })
    assert.equal(response.status, created ? 201 : 200)
    assert.deepEqual(await response.json(), {
      video_id: id,
      status: "UPLOADING",
    })
    assert.equal(writes(), 1)
  }
})

test("invalid metadata never reaches storage", async () => {
  const { app, writes } = fixture()
  for (const invalid of [
    { size_bytes: 500_000_001 },
    { duration_sec: 1800.1 },
    { duration_sec: 0 },
    { mime_type: "text/plain" },
    { session_id: "invalid" },
    { file_hash: "invalid" },
  ]) {
    const response = await app.request("/api/videos", {
      method: "POST",
      body: JSON.stringify({ ...input, ...invalid }),
    })
    assert.equal(response.status, 422)
  }
  assert.equal(writes(), 0)
})

test("malformed JSON is a bad request", async () => {
  const { app, writes } = fixture()
  const response = await app.request("/api/videos", {
    method: "POST",
    body: "{",
  })
  assert.equal(response.status, 400)
  assert.equal(writes(), 0)
})

test("status serializes bigint and excludes private fields", async () => {
  const { app } = fixture()
  const response = await app.request(`/api/videos/${id}`)
  assert.equal(response.status, 200)
  assert.deepEqual(await response.json(), {
    video_id: id,
    status: "UPLOADING",
    error_message: null,
    size_bytes: "1000",
    duration_sec: 60,
    detected_cuts: null,
    progress: { total_slices: 0, slices_completed: 0 },
  })
})

test("missing video and invalid identifiers have explicit errors", async () => {
  const { app } = fixture(true, null)
  assert.equal((await app.request(`/api/videos/${id}`)).status, 404)
  assert.equal((await app.request("/api/videos/invalid")).status, 422)
})

test("health works without database configuration", async () => {
  assert.equal((await createApp().request("/api/health")).status, 200)
})
