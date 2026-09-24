import os
import unittest
from unittest.mock import patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication, QMessageBox
from ui.local_panel import LocalPanel
from ui.remote_panel import RemotePanel


class PanelSelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_local_map_is_ready_for_one_click_upload(self):
        panel = LocalPanel()
        panel.refresh_list(["Map.wld"])
        self.assertEqual(panel.map_list.currentItem().text(), "Map")
        self.assertTrue(panel.upload_btn.isEnabled())

    def test_latest_remote_version_is_selected_by_default(self):
        panel = RemotePanel()
        panel.refresh_list({"Map": [{"date": "20260802120000", "wld": "20260802120000Map.wld",
                                     "bak": None, "bak2": None}]})
        self.assertEqual(panel.tree.currentItem().data(0, 1), "20260802120000Map.wld")
        self.assertTrue(panel.download_btn.isEnabled())

    def test_selected_map_uploads_with_one_button_click(self):
        panel = LocalPanel()
        panel.refresh_list(["Map.wld"])
        requested = []
        panel.upload_requested.connect(requested.append)
        with patch("ui.local_panel.QMessageBox.question", return_value=QMessageBox.StandardButton.No):
            panel.upload_btn.click()
        self.assertEqual(requested, ["Map"])

    def test_selected_version_downloads_with_one_button_click(self):
        panel = RemotePanel()
        panel.refresh_list({"Map": [{"date": "20260802120000", "wld": "20260802120000Map.wld",
                                     "bak": None, "bak2": None}]})
        requested = []
        panel.download_requested.connect(lambda dated, original: requested.append((dated, original)))
        with patch("ui.remote_panel.QMessageBox.question", return_value=QMessageBox.StandardButton.No):
            panel.download_btn.click()
        self.assertEqual(requested, [("20260802120000Map.wld", "Map.wld")])


if __name__ == "__main__":
    unittest.main()
