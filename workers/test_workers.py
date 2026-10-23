import shutil
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from zipfile import ZipFile

from workers import detect, slice
from workers.media import detect_cuts, probe_video, split_cut, validate_cuts

VIDEO_ID = "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d"


class WorkerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workspace = TemporaryDirectory()
        cls.source = Path(cls.workspace.name) / "source.mp4"
        subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-f",
                "lavfi",
                "-i",
                "color=c=black:s=160x120:r=24:d=1",
                "-f",
                "lavfi",
                "-i",
                "color=c=white:s=160x120:r=24:d=1",
                "-filter_complex",
                "[0:v][1:v]concat=n=2:v=1:a=0[out]",
                "-map",
                "[out]",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                str(cls.source),
            ],
            check=True,
            capture_output=True,
        )

    @classmethod
    def tearDownClass(cls):
        cls.workspace.cleanup()

    def test_detection_returns_cuts_and_persists_without_slicing(self):
        with (
            patch(
                "workers.storage.download_raw",
                side_effect=lambda _, path: shutil.copyfile(self.source, path),
            ),
            patch("workers.storage.save_detection") as save,
        ):
            response = detect.handler({"video_id": VIDEO_ID}, None)
        cuts = response["detected_cuts"]
        self.assertEqual(response["total_slices"], 2)
        self.assertAlmostEqual(cuts[0]["end"], 1.0, places=2)
        self.assertAlmostEqual(cuts[1]["end"], 2.0, places=2)
        save.assert_called_once_with(VIDEO_ID, cuts, 2.0)

    def test_no_transition_is_one_full_scene(self):
        cuts = detect_cuts(self.source)
        clip = Path(self.workspace.name) / "single_scene.mp4"
        split_cut(self.source, cuts[0], 24.0, clip)
        scenes = detect_cuts(clip)
        self.assertEqual(len(scenes), 1)
        self.assertAlmostEqual(scenes[0]["start"], 0)
        self.assertAlmostEqual(scenes[0]["end"], 1)

    def test_slicing_resumes_one_clip_and_builds_archive(self):
        cuts = detect_cuts(self.source)
        cached = Path(self.workspace.name) / "cached.mp4"
        split_cut(self.source, cuts[0], 24.0, cached)
        uploaded_indices = []
        archives = []

        def save_clip(video_id, cut, path):
            self.assertEqual(video_id, VIDEO_ID)
            self.assertAlmostEqual(probe_video(path), 1.0, places=1)
            uploaded_indices.append(cut["index"])

        def save_archive(video_id, path):
            self.assertEqual(video_id, VIDEO_ID)
            with ZipFile(path) as archive:
                archives.extend(archive.namelist())
                self.assertIsNone(archive.testzip())
            self.assertFalse(list(path.parent.glob("slice_*.mp4")))

        with (
            patch("workers.storage.load_cuts", return_value=cuts),
            patch("workers.storage.completed_indices", return_value={0}),
            patch(
                "workers.storage.download_raw",
                side_effect=lambda _, path: shutil.copyfile(self.source, path),
            ),
            patch(
                "workers.storage.download_slice",
                side_effect=lambda _, index, path: shutil.copyfile(cached, path),
            ) as download,
            patch("workers.storage.save_slice", side_effect=save_clip),
            patch("workers.storage.save_export", side_effect=save_archive),
            patch("workers.slice.split_cut", wraps=split_cut) as split,
        ):
            response = slice.handler({"video_id": VIDEO_ID}, None)
        self.assertEqual(response["total_slices"], 2)
        self.assertEqual(uploaded_indices, [1])
        self.assertEqual(archives, ["slice_0000.mp4", "slice_0001.mp4"])
        self.assertEqual(download.call_count, 1)
        self.assertEqual(split.call_count, 1)

    def test_failed_upload_cleans_workspace_without_publishing_export(self):
        paths = []

        def download_raw(_, path):
            paths.append(path)
            shutil.copyfile(self.source, path)

        with (
            patch("workers.storage.load_cuts", return_value=detect_cuts(self.source)),
            patch("workers.storage.completed_indices", return_value=set()),
            patch("workers.storage.download_raw", side_effect=download_raw),
            patch(
                "workers.storage.save_slice", side_effect=RuntimeError("upload failed")
            ),
            patch("workers.storage.save_export") as save_export,
        ):
            with self.assertRaisesRegex(RuntimeError, "upload failed"):
                slice.handler({"video_id": VIDEO_ID}, None)
        save_export.assert_not_called()
        self.assertFalse(paths[0].parent.exists())

    def test_invalid_cuts_and_failed_ffmpeg_are_rejected(self):
        for cuts in [
            [],
            [{"index": 0, "start": 1, "end": 2}],
            [{"index": 0, "start": 0, "end": float("nan")}],
        ]:
            with self.assertRaises(ValueError):
                validate_cuts(cuts, 2, 24.0)
        with patch("workers.media.split_video_ffmpeg", return_value=1):
            with self.assertRaises(RuntimeError):
                split_cut(
                    self.source,
                    {"index": 0, "start": 0, "end": 1},
                    24.0,
                    Path(self.workspace.name) / "failed.mp4",
                )


if __name__ == "__main__":
    unittest.main()
