import { randomUUID } from "node:crypto"
import { z } from "zod"
import type { VideoStorage } from "../storage/videos.js"

const registrationSchema = z.object({
  session_id: z.uuid(),
  file_hash: z
    .string()
    .regex(/^[a-fA-F0-9]{64}$/)
    .transform((hash) => hash.toLowerCase()),
  size_bytes: z.number().int().positive().max(500_000_000),
  duration_sec: z.number().positive().max(1800),
  mime_type: z.enum(["video/mp4", "video/quicktime"]),
})

// A narrow dependency lets tests exercise the service without Neon credentials.
type VideoStore = Pick<VideoStorage, "createOrRecover" | "findById">

export class VideoService {
  constructor(private readonly storage: VideoStore) {}

  /** Validate declared metadata and create/recover a record; no upload starts yet. */
  async register(input: unknown) {
    const metadata = registrationSchema.parse(input)
    const id = randomUUID()
    const extension = metadata.mime_type === "video/quicktime" ? "mov" : "mp4"
    const { video, created } = await this.storage.createOrRecover({
      id,
      sessionId: metadata.session_id,
      fileHash: metadata.file_hash,
      sizeBytes: BigInt(metadata.size_bytes),
      durationSec: metadata.duration_sec,
      mimeType: metadata.mime_type,
      rawObjectKey: `raw/${id}.${extension}`,
    })
    return { created, video_id: video.id, status: video.status }
  }

  /** Return JSON-safe public progress fields, or null for the route to map to 404. */
  async getById(id: string) {
    const video = await this.storage.findById(id)
    if (!video) return null

    // Whitelist public fields: omit email, session identity, and internal keys.
    return {
      video_id: video.id,
      status: video.status,
      error_message: video.errorMessage,
      size_bytes: video.sizeBytes.toString(),
      duration_sec: video.durationSec,
      detected_cuts: video.detectedCuts,
      progress: {
        total_slices: video.totalSlices,
        slices_completed: video.slicesCompleted,
      },
    }
  }
}
