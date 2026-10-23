-- CreateSchema
CREATE SCHEMA IF NOT EXISTS "public";

-- CreateEnum
CREATE TYPE "VideoStatus" AS ENUM ('UPLOADING', 'DETECTING', 'DETECTED', 'SLICING', 'COMPLETED', 'FAILED');

-- CreateTable
CREATE TABLE "videos" (
    "id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "session_id" TEXT NOT NULL,
    "file_hash" TEXT NOT NULL,
    "status" "VideoStatus" NOT NULL DEFAULT 'UPLOADING',
    "error_message" TEXT,
    "size_bytes" BIGINT NOT NULL,
    "duration_sec" DOUBLE PRECISION NOT NULL,
    "mime_type" TEXT NOT NULL,
    "raw_object_key" TEXT NOT NULL,
    "zip_object_key" TEXT,
    "detected_cuts" JSONB,
    "total_slices" INTEGER NOT NULL DEFAULT 0,
    "slices_completed" INTEGER NOT NULL DEFAULT 0,
    "user_email" TEXT,
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "videos_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "slices" (
    "id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "video_id" UUID NOT NULL,
    "slice_index" INTEGER NOT NULL,
    "object_key" TEXT NOT NULL,
    "start_sec" DOUBLE PRECISION NOT NULL,
    "end_sec" DOUBLE PRECISION NOT NULL,
    "size_bytes" BIGINT NOT NULL,
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "slices_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "videos_raw_object_key_key" ON "videos"("raw_object_key");

-- CreateIndex
CREATE UNIQUE INDEX "videos_session_id_file_hash_key" ON "videos"("session_id", "file_hash");

-- CreateIndex
CREATE UNIQUE INDEX "slices_video_id_slice_index_key" ON "slices"("video_id", "slice_index");

-- AddForeignKey
ALTER TABLE "slices" ADD CONSTRAINT "slices_video_id_fkey" FOREIGN KEY ("video_id") REFERENCES "videos"("id") ON DELETE CASCADE ON UPDATE CASCADE;

