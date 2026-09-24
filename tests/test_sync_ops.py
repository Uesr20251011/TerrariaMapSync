import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sync_ops


class DownloadMapTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.cache = root / "cache"
        self.worlds = root / "worlds"
        self.cache.mkdir()
        self.worlds.mkdir()
        (self.cache / "20260802120000Map.wld").write_bytes(b"new world")
        (self.worlds / "Map.wld").write_bytes(b"old world")
        (self.worlds / "Map.wld.bak").write_bytes(b"old backup")

    def test_failed_backup_copy_keeps_existing_world_and_reports_failure(self):
        (self.cache / "20260802120000Map.wld.bak").write_bytes(b"new backup")
        real_copy = sync_ops.shutil.copy2

        def fail_backup(src, dst):
            if str(src).endswith(".bak"):
                raise OSError("backup copy failed")
            return real_copy(src, dst)

        with patch.object(sync_ops, "pull_repo", return_value=(True, "ok")):
            with patch.object(sync_ops.shutil, "copy2", side_effect=fail_backup):
                ok, _ = sync_ops.download_map(
                    str(self.worlds), str(self.cache),
                    "20260802120000Map.wld", "Map.wld",
                )

        self.assertFalse(ok)
        self.assertEqual((self.worlds / "Map.wld").read_bytes(), b"old world")
        self.assertEqual((self.worlds / "Map.wld.bak").read_bytes(), b"old backup")

    def test_download_without_backup_removes_stale_local_backup(self):
        with patch.object(sync_ops, "pull_repo", return_value=(True, "ok")):
            ok, _ = sync_ops.download_map(
                str(self.worlds), str(self.cache),
                "20260802120000Map.wld", "Map.wld",
            )

        self.assertTrue(ok)
        self.assertEqual((self.worlds / "Map.wld").read_bytes(), b"new world")
        self.assertFalse((self.worlds / "Map.wld.bak").exists())

    def test_failed_replace_restores_both_existing_files(self):
        (self.cache / "20260802120000Map.wld.bak").write_bytes(b"new backup")
        real_replace = sync_ops.os.replace

        def fail_installing_backup(src, dst):
            if "staged" in str(src) and str(src).endswith(".bak"):
                raise OSError("backup install failed")
            return real_replace(src, dst)

        with patch.object(sync_ops, "pull_repo", return_value=(True, "ok")):
            with patch.object(sync_ops.os, "replace", side_effect=fail_installing_backup):
                ok, _ = sync_ops.download_map(
                    str(self.worlds), str(self.cache),
                    "20260802120000Map.wld", "Map.wld",
                )

        self.assertFalse(ok)
        self.assertEqual((self.worlds / "Map.wld").read_bytes(), b"old world")
        self.assertEqual((self.worlds / "Map.wld.bak").read_bytes(), b"old backup")

    def test_successful_download_keeps_a_recoverable_copy_of_old_world(self):
        with patch.object(sync_ops, "pull_repo", return_value=(True, "ok")):
            ok, _ = sync_ops.download_map(
                str(self.worlds), str(self.cache),
                "20260802120000Map.wld", "Map.wld",
            )
        backups = list((self.worlds / ".TerrariaMapSyncBackups").rglob("Map.wld"))
        self.assertTrue(ok)
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), b"old world")


if __name__ == "__main__":
    unittest.main()
