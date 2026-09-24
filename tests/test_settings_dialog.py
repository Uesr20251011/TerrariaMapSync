import os
import tempfile
import unittest
from unittest.mock import patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from ui.settings_dialog import SettingsDialog


class SettingsDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_settings_show_current_values_and_can_rerun_wizard(self):
        with tempfile.TemporaryDirectory() as directory:
            config = {"worlds_path": directory,
                      "repo_url": "https://github.com/owner/maps.git",
                      "repo_cache_dir": os.path.join(directory, "cache"),
                      "setup_complete": True, "github_login": "builder"}
            dialog = SettingsDialog(config)
            self.assertEqual(dialog.worlds_edit.text(), directory)
            self.assertEqual(dialog.repo_edit.text(), config["repo_url"])
            self.assertIn("builder", dialog.account.login_label.text())
            with patch("ui.settings_dialog.SetupWizard") as wizard:
                dialog.rerun_button.click()
            wizard.assert_called_once()
            dialog.close()

    def test_changing_repository_requires_new_connection_check(self):
        with tempfile.TemporaryDirectory() as directory:
            config = {"worlds_path": directory,
                      "repo_url": "https://github.com/owner/old.git",
                      "repo_cache_dir": os.path.join(directory, "cache"),
                      "setup_complete": True, "github_login": ""}
            dialog = SettingsDialog(config)
            dialog.repo_edit.setText("https://github.com/owner/new.git")
            with patch("ui.settings_dialog.save_config"):
                self.assertTrue(dialog.save_fields())
            self.assertFalse(config["setup_complete"])
            dialog.close()

    def test_failed_auth_clears_stale_account_and_setup_state(self):
        with tempfile.TemporaryDirectory() as directory:
            config = {"worlds_path": directory,
                      "repo_url": "https://github.com/owner/maps.git",
                      "repo_cache_dir": os.path.join(directory, "cache"),
                      "setup_complete": True, "github_login": "old-account"}
            dialog = SettingsDialog(config)
            result = {key: (False, "failed") for key in ("git", "cli", "auth", "repo")}
            result.update(login="", avatar=b"")
            with patch("ui.settings_dialog.save_config"):
                dialog._connection_checked(result)
            self.assertEqual(config["github_login"], "")
            self.assertFalse(config["setup_complete"])
            dialog.close()

    def test_private_repository_guidance_can_be_copied(self):
        with tempfile.TemporaryDirectory() as directory:
            config = {"worlds_path": directory,
                      "repo_url": "https://github.com/owner/maps.git",
                      "repo_cache_dir": os.path.join(directory, "cache"),
                      "setup_complete": False, "github_login": "player"}
            dialog = SettingsDialog(config)
            result = {key: (True, "ok") for key in ("git", "cli", "auth")}
            result.update(repo=(False, "需要仓库邀请"), login="player", avatar=b"",
                          request_text="请邀请 @player")
            with patch("ui.settings_dialog.save_config"):
                dialog._connection_checked(result)
            self.assertFalse(dialog.copy_request_button.isHidden())
            dialog.copy_request_button.click()
            self.assertEqual(QApplication.clipboard().text(), "请邀请 @player")
            dialog.close()


if __name__ == "__main__":
    unittest.main()
