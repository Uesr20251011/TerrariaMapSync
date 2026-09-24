import json
import unittest
from unittest.mock import patch

from repository_access import connect_repository


REPO_URL = "https://github.com/map-owner/shared-worlds.git"


class RepositoryAccessTests(unittest.TestCase):
    def test_pending_invitation_is_accepted_then_clone_is_retried(self):
        invitation = [{"id": 42, "repository": {"full_name": "map-owner/shared-worlds"}}]
        with patch("repository_access.clone_repo", side_effect=[
            (False, "remote: Repository not found."), (True, "仓库已更新")
        ]) as clone:
            with patch("repository_access._run_gh", side_effect=[
                (True, json.dumps(invitation)), (True, ""),
            ]) as gh:
                result = connect_repository(REPO_URL, "cache")
        self.assertTrue(result.success)
        self.assertIn("已自动接受", result.message)
        self.assertEqual(clone.call_count, 2)
        gh.assert_any_call(["-X", "PATCH", "user/repository_invitations/42"])

    def test_without_invitation_app_prepares_owner_request_without_claiming_it_was_sent(self):
        with patch("repository_access.clone_repo", return_value=(False, "Repository not found")):
            with patch("repository_access._run_gh", side_effect=[
                (True, "[]"), (True, "map-player\n"),
            ]):
                result = connect_repository(REPO_URL, "cache")
        self.assertFalse(result.success)
        self.assertIn("地址有误或尚无权限", result.message)
        self.assertIn("@map-player", result.request_text)
        self.assertIn("map-owner/shared-worlds", result.request_text)
        self.assertNotIn("已发送", result.message)

    def test_unrelated_network_error_does_not_suggest_permission_request(self):
        with patch("repository_access.clone_repo", return_value=(False, "Could not resolve host")):
            with patch("repository_access._run_gh") as gh:
                result = connect_repository(REPO_URL, "cache")
        self.assertFalse(result.success)
        self.assertEqual(result.request_text, "")
        gh.assert_not_called()


if __name__ == "__main__":
    unittest.main()
