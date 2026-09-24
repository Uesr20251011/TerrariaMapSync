import json
import subprocess
import unittest
from unittest.mock import patch

from setup_services import check_github_login, is_github_repo_url, load_github_profile


class SetupServicesTests(unittest.TestCase):
    def test_repository_url_must_be_a_github_https_repository(self):
        self.assertTrue(is_github_repo_url("https://github.com/owner/maps.git"))
        self.assertTrue(is_github_repo_url("https://github.com/owner/maps"))
        self.assertFalse(is_github_repo_url("https://example.com/owner/maps"))
        self.assertFalse(is_github_repo_url("https://github.com/owner"))

    def test_login_check_reports_missing_cli(self):
        with patch("setup_services.find_executable", return_value=None):
            ok, _ = check_github_login()
        self.assertFalse(ok)

    def test_login_check_uses_github_cli_status(self):
        with patch("setup_services.find_executable", return_value="gh.exe"):
            with patch("setup_services.subprocess.run", return_value=subprocess.CompletedProcess([], 0, "", "")):
                ok, _ = check_github_login()
        self.assertTrue(ok)

    def test_profile_load_returns_login_and_avatar_bytes(self):
        response = subprocess.CompletedProcess(
            [], 0, json.dumps({"login": "builder", "avatar_url": "https://avatars.githubusercontent.com/u/1"}), "",
        )
        class FakeResponse:
            def __enter__(self):
                return self
            def __exit__(self, *_args):
                pass
            def read(self, _size):
                return b"image-data"
        with patch("setup_services.find_executable", return_value="gh.exe"):
            with patch("setup_services.subprocess.run", return_value=response):
                with patch("setup_services.urlopen", return_value=FakeResponse()):
                    login, avatar = load_github_profile()
        self.assertEqual(login, "builder")
        self.assertEqual(avatar, b"image-data")

    def test_profile_keeps_login_when_avatar_is_unavailable(self):
        response = subprocess.CompletedProcess(
            [], 0, json.dumps({"login": "builder", "avatar_url": "https://avatars.githubusercontent.com/u/1"}), "",
        )
        with patch("setup_services.find_executable", return_value="gh.exe"):
            with patch("setup_services.subprocess.run", return_value=response):
                with patch("setup_services.urlopen", side_effect=OSError("offline")):
                    login, avatar = load_github_profile()
        self.assertEqual((login, avatar), ("builder", b""))


if __name__ == "__main__":
    unittest.main()
