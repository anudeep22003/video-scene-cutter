"""Lambda entry point that detects boundaries without writing physical clips."""

from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID

from workers import storage
from workers.media import detect_cuts, probe_video


def handler(event: dict, context) -> dict:
    video_id = str(UUID(event["video_id"]))
    # WIRE: claim DETECTING ownership idempotently before doing expensive work.
    # Dispatch/retry code must record terminal failures and recover stale leases.
    with TemporaryDirectory(prefix="detect-", dir="/tmp") as directory:
        source = Path(directory) / "source.video"
        storage.download_raw(video_id, source)
        duration = probe_video(source)
        cuts = detect_cuts(source)
        storage.save_detection(video_id, cuts, duration)
        return {"video_id": video_id, "detected_cuts": cuts, "total_slices": len(cuts)}
