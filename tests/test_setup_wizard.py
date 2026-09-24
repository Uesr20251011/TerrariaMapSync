import os
import tempfile
import unittest
from unittest.mock import patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import QEventLoop, QProcess, QTimer
from PySide6.QtWidgets import QApplication
from repository_access import RepositoryConnection
from ui.setup_wizard import LoginPage, RequirementsPage, SetupWizard


class SetupWizardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_installed_tools_are_explicitly_marked_as_not_needing_download(self):
        with patch("ui.setup_wizard.check_git_installation", return_value=(True, "git 2.51")):
            with patch("ui.setup_wizard.check_github_cli", return_value=(True, "gh 2.97")):
                page = RequirementsPage()
        self.assertIn("电脑上已有 Git，无需下载", page.git_status.text())
        self.assertIn("电脑上已有 GitHub CLI，无需下载", page.gh_status.text())
        self.assertTrue(page.git_link.isHidden())
        self.assertTrue(page.gh_link.isHidden())

    def test_login_button_opens_default_browser_and_starts_cli(self):
        page = LoginPage()

        class FakeProcess:
            def __init__(self):
                self.started = None

            def state(self):
                return QProcess.ProcessState.NotRunning

            def start(self, program, args):
                self.started = (program, args)

        fake = FakeProcess()
        page.login_process = fake
        with patch("ui.setup_wizard.find_executable", return_value="gh"):
            with patch("ui.setup_wizard.QDesktopServices.openUrl", return_value=True) as open_url:
                page.start_login()
        self.assertEqual(fake.started[0], "gh")
        self.assertIn("--web", fake.started[1])
        self.assertTrue(open_url.called)
        self.assertEqual(open_url.call_args.args[0].toString(), "https://github.com/login/device")

    def test_login_cli_enter_prompt_is_answered_automatically(self):
        page = LoginPage()

        class FakeProcess:
            def __init__(self):
                self.writes = []

            def readAllStandardOutput(self):
                return b"Press Enter to open github.com in your browser..."

            def write(self, data):
                self.writes.append(data)

        fake = FakeProcess()
        page.login_process = fake
        page._read_login_output()
        page._read_login_output()
        self.assertEqual(fake.writes, [b"\n"])

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
                with patch("ui.setup_wizard.connect_repository",
                           return_value=RepositoryConnection(True, "ok")):
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

    def test_missing_access_offers_copyable_owner_invitation_text(self):
        with tempfile.TemporaryDirectory() as directory:
            config = {"worlds_path": directory, "repo_url": "",
                      "repo_cache_dir": os.path.join(directory, "cache"),
                      "setup_complete": False, "github_login": "map-player"}
            with patch("ui.setup_wizard.check_git_installation", return_value=(True, "git")):
                with patch("ui.setup_wizard.check_github_cli", return_value=(True, "gh")):
                    wizard = SetupWizard(config)
            page = wizard.repository_page
            page.worlds_edit.setText(directory)
            page.repo_edit.setText("https://github.com/owner/maps.git")
            page._checked_values = (directory, page.repo_edit.text())
            page._on_repository_checked(RepositoryConnection(
                False, "仓库地址有误或尚无权限", "请邀请 @map-player"))
            self.assertFalse(page.isComplete())
            self.assertFalse(page.copy_request_button.isHidden())
            page.copy_request_button.click()
            self.assertEqual(QApplication.clipboard().text(), "请邀请 @map-player")
            wizard.close()


if __name__ == "__main__":
    unittest.main()
