import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

import git_manager


class RepositorySwitchTests(unittest.TestCase):
    def test_missing_git_identity_uses_logged_in_github_noreply_address(self):
        with patch.object(git_manager, "_run_git", return_value=(False, "unset")):
            with patch.object(git_manager, "find_executable", return_value="gh"):
                with patch.object(git_manager.subprocess, "run", return_value=SimpleNamespace(
                    returncode=0, stdout='{"login":"mapmaker","id":12345}'
                )):
                    args, error = git_manager._commit_identity_args("unused")
        self.assertEqual(error, "")
        self.assertIn("user.name=mapmaker", args)
        self.assertIn("user.email=12345+mapmaker@users.noreply.github.com", args)

    def test_pull_preserves_untracked_cache_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            remote = root / "remote.git"
            seed = root / "seed"
            cache = root / "cache"
            subprocess.run(
                ["git", "init", "--bare", "--initial-branch=main", str(remote)],
                check=True, capture_output=True,
            )
            subprocess.run(["git", "clone", str(remote), str(seed)],
                           check=True, capture_output=True)
            (seed / "README.md").write_text("map repository", encoding="utf-8")
            subprocess.run(["git", "add", "README.md"], cwd=seed,
                           check=True, capture_output=True)
            subprocess.run(
                ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com",
                 "commit", "-m", "Initial"], cwd=seed, check=True, capture_output=True,
            )
            subprocess.run(["git", "push", "origin", "main"], cwd=seed,
                           check=True, capture_output=True)
            subprocess.run(["git", "clone", str(remote), str(cache)],
                           check=True, capture_output=True)
            pending = cache / "pending-map.wld"
            pending.write_bytes(b"not uploaded")

            with patch.dict(os.environ, {"GIT_CONFIG_GLOBAL": str(root / "global.gitconfig") }):
                ok, message = git_manager.pull_repo(str(cache))

            self.assertTrue(ok, message)
            self.assertEqual(pending.read_bytes(), b"not uploaded")

    def test_auth_environment_does_not_change_global_git_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "global.gitconfig"
            config.write_text("[credential]\n\thelper = manager\n", encoding="utf-8")
            with patch.dict(os.environ, {"GIT_CONFIG_GLOBAL": str(config)}):
                git_manager._build_env()
            self.assertEqual(
                config.read_text(encoding="utf-8"),
                "[credential]\n\thelper = manager\n",
            )

    def test_git_commands_use_github_cli_without_askpass_console(self):
        with patch("git_manager.find_executable", return_value=r"C:\Program Files\GitHub CLI\gh.exe"):
            env = git_manager._build_env()
        helpers = [env[f"GIT_CONFIG_VALUE_{i}"] for i in range(int(env["GIT_CONFIG_COUNT"]))]
        self.assertTrue(any("gh.exe" in value and "auth git-credential" in value for value in helpers))
        self.assertNotIn("GIT_ASKPASS", env)

    def test_switching_url_replaces_old_cache_with_new_repository(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "first.git"
            second = root / "second.git"
            cache = root / "cache"
            for remote in (first, second):
                subprocess.run(
                    ["git", "init", "--bare", str(remote)],
                    check=True, capture_output=True,
                )
            subprocess.run(
                ["git", "clone", str(first), str(cache)],
                check=True, capture_output=True,
            )

            with patch.dict(os.environ, {
                "APPDATA": directory,
                "GIT_CONFIG_GLOBAL": str(root / "global.gitconfig"),
            }):
                ok, message = git_manager.clone_repo(str(second), str(cache))

            origin = subprocess.check_output(
                ["git", "remote", "get-url", "origin"], cwd=cache, text=True,
            ).strip()
            self.assertTrue(ok, message)
            self.assertEqual(origin, str(second))


if __name__ == "__main__":
    unittest.main()
