"""Lambda entry point that cuts persisted scenes and rebuilds a ZIP on retry."""

from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID
from zipfile import ZIP_STORED, ZipFile

from scenedetect import open_video

from workers import storage
from workers.media import probe_video, split_cut, validate_cuts


def handler(event: dict, context) -> dict:
    video_id = str(UUID(event["video_id"]))
    # WIRE: claim SLICING ownership; prevent overlapping workers for one video.
    # Before deployment, add deadline-aware continuation with durable dispatch.
    cuts = storage.load_cuts(video_id)
    completed = storage.completed_indices(video_id)
    with TemporaryDirectory(prefix="slice-", dir="/tmp") as directory:
        workspace = Path(directory)
        source = workspace / "source.video"
        storage.download_raw(video_id, source)
        duration = probe_video(source)
        fps = open_video(str(source)).frame_rate
        validate_cuts(cuts, duration, fps)
        archive_path = workspace / "slices.zip"
        with ZipFile(archive_path, "w", compression=ZIP_STORED) as archive:
            for cut in cuts:
                clip = workspace / f"slice_{cut['index']:04d}.mp4"
                if cut["index"] in completed:
                    storage.download_slice(video_id, cut["index"], clip)
                else:
                    split_cut(source, cut, fps, clip)
                    storage.save_slice(video_id, cut, clip)
                archive.write(clip, arcname=clip.name)
                clip.unlink()
        storage.save_export(video_id, archive_path)
    return {"video_id": video_id, "total_slices": len(cuts)}
