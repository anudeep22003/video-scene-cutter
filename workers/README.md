# Python Lambda workers

Two handlers use PySceneDetect 0.7.1 with headless OpenCV and FFmpeg. Both accept
an internal invocation payload containing only the video ID:

```json
{ "video_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d" }
```

- `workers.detect.handler`: download raw input, verify size/container/duration
  with ffprobe, detect boundaries, persist them, and return
  `{ video_id, detected_cuts: [{ index, start, end }], total_slices }`.
  It never creates physical clips.
- `workers.slice.handler`: load persisted cuts and completed indices, download
  input, validate intervals, cut/upload/checkpoint one new scene at a time, and
  build an uncompressed ZIP. Completed clips are downloaded into the ZIP on retry.
  It returns `{ video_id, total_slices }` after publishing the archive.

Times are seconds and indices are zero-based. Detection uses
`ContentDetector()` and `start_in_scene=True` so a video without transitions
becomes one scene. Slicing uses `split_video_ffmpeg` with H.264/AAC encoding and
fixed zero-based filenames instead of PySceneDetect's default scene numbering.
No audio stream is required. Limits match the API: 500,000,000 bytes / 1,800 seconds.
The splitter converts seconds to frame timecodes using the source frame rate;
benchmark variable-frame-rate inputs before promising exact boundaries.

## Storage and database contact points

`storage.py` deliberately raises `NotImplementedError` at each integration point.
The media code works locally, but handlers are not production-ready until wired.
Each function has a `WIRE` comment describing its contract:

| Function            | Integration                                                                                                         |
| ------------------- | ------------------------------------------------------------------------------------------------------------------- |
| `download_raw`      | Read `raw_object_key` from the video record and download the stable S3 object into the supplied path.               |
| `save_detection`    | Write verified duration, JSON cuts, total count, and `DETECTED` conditionally.                                      |
| `load_cuts`         | Load authoritative cuts from PostgreSQL.                                                                            |
| `completed_indices` | Read completed indices from the `slices` ledger.                                                                    |
| `save_slice`        | Upload the deterministic S3 key, then insert metadata and increment progress only on a new row, in one transaction. |
| `download_slice`    | Retrieve an already completed clip for archive reconstruction.                                                      |
| `save_export`       | Upload ZIP before publishing its key/`COMPLETED`; durably record separate email work.                               |

Python does not use the TypeScript Prisma client. Choose a Python database adapter
or an internal API for these persistence operations when wiring them.
Handlers also mark the job-ownership contact points. Before deployment, implement
leases/idempotency, durable dispatch, bounded retries, deadline-aware continuation,
and terminal failure reporting. Exceptions currently propagate to Lambda; a
transient failure must not immediately mark the whole job permanently failed.
The API does not dispatch these handlers yet. They do not parse S3/SQS events;
an event adapter must resolve and validate the video identity first.

Both handlers use unique `/tmp` directories and clean up on normal/error exits.
Hard Lambda timeouts can bypass cleanup. Raw input + ZIP + one clip must still
fit in configured ephemeral storage; clip deletion does not bound archive growth.
The retry ledger avoids re-encoding completed clips, but ZIP rebuilding restarts.

## Local verification

Install Python 3.12 (declared in the root `.python-version`) and FFmpeg/ffprobe on
your PATH, then from the repository root:

```sh
make workers-install
make workers-format
make workers-check
```

`make format` and `make check` also include workers once dependencies are installed.
Ruff's target version and line length are committed in `workers/pyproject.toml`.
Tests generate a tiny two-scene video with FFmpeg, run actual detection/slicing,
and substitute local files for cloud storage. They verify single-scene handling,
checkpoint reuse, ZIP contents, invalid cuts, and cleanup after an upload failure.

## Lambda image

The Dockerfile installs FFmpeg/ffprobe and Python dependencies at build time. It
uses Debian Python with AWS's runtime interface client. Build one image for both
functions (Docker must be running):

```sh
docker buildx build --platform linux/amd64 --provenance=false --load \
  -t video-slicer-workers workers
```

Configure the two Lambda functions with image command overrides
`["workers.detect.handler"]` and `["workers.slice.handler"]`. Match the Lambda
architecture to the image; use `linux/arm64` instead if choosing ARM64. Deployment,
IAM, S3, database credentials, notification delivery, and triggers remain unwired.
Configure sufficient memory, timeout, and `/tmp` for measured workloads; standard
Lambda's 15-minute ceiling remains relevant for both workers.

References: [PySceneDetect API](https://www.scenedetect.com/docs/latest/api.html),
[FFmpeg splitting API](https://www.scenedetect.com/docs/api/video_splitter.html),
[Python Lambda images](https://docs.aws.amazon.com/lambda/latest/dg/python-image.html).
