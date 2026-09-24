import os
import tempfile
import unittest
from unittest.mock import patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication
from ui.setup_wizard import SetupWizard


class SetupWizardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_repository_is_checked_before_setup_is_complete(self):
        with tempfile.TemporaryDirectory() as directory:
            config = {"worlds_path": directory, "repo_url": "",
                      "repo_cache_dir": os.path.join(directory, "cache"),
                      "setup_complete": False, "github_login": ""}
            with patch("ui.setup_wizard.check_git_installation", return_value=(True, "git")):
                with patch("ui.setup_wizard.check_github_cli", return_value=(True, "gh")):
                    wizard = SetupWizard(config)
            page = wizard.repository_page
            page.worlds_edit.setText(directory)
            page.repo_edit.setText("https://github.com/owner/maps.git")
            self.assertFalse(config["setup_complete"])
            self.assertFalse(page.isComplete())

            with patch("ui.setup_wizard.save_config"):
                with patch("ui.setup_wizard.clone_repo", return_value=(True, "ok")):
                    page.check_repository()
                    loop = QEventLoop()
                    page.completeChanged.connect(loop.quit)
                    QTimer.singleShot(2000, loop.quit)
                    loop.exec()
            self.assertTrue(page.isComplete())
            self.assertFalse(config["setup_complete"])
            with patch("ui.setup_wizard.save_config"):
                wizard.accept()
            self.assertTrue(config["setup_complete"])
            wizard.close()


if __name__ == "__main__":
    unittest.main()
