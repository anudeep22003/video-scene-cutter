"""WIRE: implement these S3/DB contact points before deploying either worker."""

from pathlib import Path
from typing import TypedDict


class Cut(TypedDict):
    index: int
    start: float
    end: float


def download_raw(video_id: str, destination: Path) -> None:
    # WIRE: look up raw_object_key in videos, then download that exact S3 object.
    # Use a stable object version/identity; never accept an arbitrary client URL.
    raise NotImplementedError("Wire raw video lookup and S3 download")


def save_detection(video_id: str, cuts: list[Cut], duration_sec: float) -> None:
    # WIRE: persist verified duration, detected_cuts, total_slices, DETECTED.
    # Condition updates on the detection job's ownership and expected state.
    raise NotImplementedError("Wire detection result persistence")


def load_cuts(video_id: str) -> list[Cut]:
    # WIRE: read authoritative detected_cuts from videos, not the invocation body.
    raise NotImplementedError("Wire persisted scene lookup")


def completed_indices(video_id: str) -> set[int]:
    # WIRE: query the slices ledger for this video to resume completed clips.
    raise NotImplementedError("Wire slice checkpoint lookup")


def save_slice(video_id: str, cut: Cut, source: Path) -> None:
    # WIRE: upload to slices/{video_id}/slice_{index:04d}.mp4 first.
    # Then insert metadata/size and increment progress ONLY if a row was inserted,
    # in one DB transaction. Deterministic keys make upload-before-DB retries safe.
    raise NotImplementedError("Wire clip upload and checkpoint transaction")


def download_slice(video_id: str, index: int, destination: Path) -> None:
    # WIRE: download a completed clip from its ledger object_key for ZIP rebuild.
    raise NotImplementedError("Wire completed clip download")


def save_export(video_id: str, source: Path) -> None:
    # WIRE: upload exports/{video_id}/slices.zip, then publish its key + COMPLETED.
    # Persist a separate notification job/state for email delivery retries.
    raise NotImplementedError("Wire archive upload and export completion")
