import os
import tempfile
import time
import unittest
from unittest.mock import patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from ui.main_window import GitWorker, MainWindow
from ui.settings_dialog import SettingsDialog


class MainWindowFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.appdata = patch.dict(os.environ, {"APPDATA": self.temp.name})
        self.appdata.start()
        self.addCleanup(self.appdata.stop)
        self.window = MainWindow({
            "worlds_path": "", "repo_url": "",
            "repo_cache_dir": os.path.join(self.temp.name, "cache"),
        })
        self.addCleanup(self.window.close)

    def test_typing_repo_url_does_not_start_sync(self):
        dialog = SettingsDialog(self.window._config)
        with patch.object(self.window, "_sync_repo") as sync:
            for char in "abc":
                dialog.repo_edit.insert(char)
        sync.assert_not_called()
        dialog.close()

    def test_remote_refresh_fetches_new_versions(self):
        with patch.object(self.window, "_sync_repo") as sync:
            self.window.remote_panel.refresh_btn.click()
        sync.assert_called_once_with()

    def test_download_does_not_replace_a_running_worker(self):
        self.window._config["worlds_path"] = self.temp.name
        old_worker = GitWorker(lambda: (time.sleep(0.4), (True, "ok"))[1])
        old_worker.start()
        self.window._worker = old_worker
        def fake_download(*_args):
            return (True, "ok")
        try:
            with patch("ui.main_window.download_map", fake_download):
                self.window._download_map("20260802120000Map.wld", "Map.wld")
            self.assertIs(self.window._worker, old_worker)
        finally:
            self.window._worker.wait(2000)
            old_worker.wait(2000)


if __name__ == "__main__":
    unittest.main()
