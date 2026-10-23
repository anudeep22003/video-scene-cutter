"""Local media operations, independent of AWS and database access."""

import json
import math
import subprocess
from pathlib import Path

from scenedetect import ContentDetector, FrameTimecode, detect, split_video_ffmpeg

from workers.storage import Cut


def probe_video(source: Path) -> float:
    """Validate actual local media against V1 limits and return duration in seconds.

    Reject unsupported containers or missing video streams regardless of what
    the browser declared. ffprobe/process errors propagate to the caller.
    """
    if not 0 < source.stat().st_size <= 500_000_000:
        raise ValueError("Video must be between 1 and 500,000,000 bytes")
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_format",
            "-show_streams",
            "-of",
            "json",
            str(source),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    metadata = json.loads(result.stdout)
    duration = float(metadata["format"]["duration"])
    if not math.isfinite(duration) or not 0 < duration <= 1800:
        raise ValueError("Video duration must be between 0 and 1,800 seconds")
    if not any(stream["codec_type"] == "video" for stream in metadata["streams"]):
        raise ValueError("Input has no video stream")
    if not {"mov", "mp4"}.intersection(metadata["format"]["format_name"].split(",")):
        raise ValueError("Only MP4 and QuickTime containers are supported")
    return duration


def detect_cuts(source: Path) -> list[Cut]:
    """Return zero-based scene intervals in seconds; no transitions means one scene."""
    scenes = detect(str(source), ContentDetector(), start_in_scene=True)
    if not scenes:
        raise ValueError("Video contains no decodable scenes")
    return [
        Cut(index=index, start=start.seconds, end=end.seconds)
        for index, (start, end) in enumerate(scenes)
    ]


def validate_cuts(cuts: list[Cut], duration: float, fps: float) -> None:
    """Reject gaps, reordered indices, and cuts that do not span the whole input.

    Allow one frame of end-time drift between ffprobe duration and detected
    frame boundaries; adjacent cuts must still share the same boundary.
    """
    if not cuts:
        raise ValueError("No persisted cuts to slice")
    previous_end = 0.0
    for index, cut in enumerate(cuts):
        start, end = cut["start"], cut["end"]
        if (
            cut["index"] != index
            or not math.isfinite(start)
            or not math.isfinite(end)
            or not 0 <= start < end <= duration + 1 / fps
            or abs(start - previous_end) > 0.000001
        ):
            raise ValueError("Cuts must be ordered, contiguous, and within the video")
        previous_end = end
    if abs(previous_end - duration) > 1 / fps:
        raise ValueError("Cuts must cover the whole video")


def split_cut(source: Path, cut: Cut, fps: float, destination: Path) -> None:
    """Encode one interval as H.264/AAC at destination, allowing silent sources.

    Convert seconds back to source frame timecodes. A nonzero FFmpeg exit or a
    missing/empty output raises before the caller can upload or checkpoint it.
    """
    # One call per clip preserves the upload/checkpoint/delete boundary.
    result = split_video_ffmpeg(
        str(source),
        [
            (
                FrameTimecode(float(cut["start"]), fps),
                FrameTimecode(float(cut["end"]), fps),
            )
        ],
        output_dir=destination.parent,
        output_file_template=destination.name,
        arg_override="-map 0:v:0 -map 0:a:0? -c:v libx264 -preset superfast -crf 22 -c:a aac -movflags +faststart",
    )
    if result != 0 or not destination.is_file() or destination.stat().st_size == 0:
        raise RuntimeError(f"FFmpeg failed to produce slice {cut['index']}")
