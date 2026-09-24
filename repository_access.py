"""Recover a repository invitation and explain missing private-repository access."""

import json
import subprocess
import sys
from dataclasses import dataclass
from urllib.parse import urlparse

from git_manager import clone_repo
from setup_services import is_github_repo_url
from tool_paths import find_executable

_HIDDEN_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


@dataclass(frozen=True)
class RepositoryConnection:
    success: bool
    message: str
    request_text: str = ""


def _run_gh(args: list[str]) -> tuple[bool, str]:
    gh = find_executable("gh")
    if not gh:
        return (False, "未找到 GitHub CLI")
    try:
        result = subprocess.run([gh, "api", *args], capture_output=True, text=True,
                                encoding="utf-8", timeout=15, creationflags=_HIDDEN_WINDOW)
        return (result.returncode == 0, result.stdout.strip() if result.returncode == 0
                else result.stderr.strip())
    except (OSError, subprocess.TimeoutExpired) as error:
        return (False, str(error))


def _is_access_error(message: str) -> bool:
    text = message.lower()
    return any(phrase in text for phrase in (
        "repository not found", "requested url returned error: 401",
        "requested url returned error: 403", "requested url returned error: 404",
        "authentication failed", "permission denied", "could not read username",
    ))


def _repo_name(repo_url: str) -> str:
    parts = urlparse(repo_url).path.strip("/").split("/")
    name = parts[1][:-4] if parts[1].lower().endswith(".git") else parts[1]
    return f"{parts[0]}/{name}"


def _request_text(repo_name: str, login_hint: str) -> str:
    ok, login = _run_gh(["user", "--jq", ".login"])
    account = (login if ok and login else login_hint).strip().lstrip("@")
    account = account or "请填写你的 GitHub 用户名"
    return (
        f"你好，我想用泰拉瑞亚地图同步助手同步 {repo_name}。"
        f"我的 GitHub 用户名是 @{account}。"
        "请在该仓库的 Settings → Collaborators（组织仓库为 Collaborators & teams）"
        "中邀请我，并授予可上传地图的写入权限。"
        "收到邀请后，我会在应用里重新检测连接。"
    )


def connect_repository(repo_url: str, cache_dir: str,
                       login_hint: str = "") -> RepositoryConnection:
    """Clone/pull, accepting an existing invitation for this exact repository."""
    success, message = clone_repo(repo_url, cache_dir)
    if success or not is_github_repo_url(repo_url) or not _is_access_error(message):
        return RepositoryConnection(success, message)

    repo_name = _repo_name(repo_url)
    listed, payload = _run_gh(["user/repository_invitations"])
    if listed:
        try:
            invitations = json.loads(payload)
        except ValueError:
            invitations = []
        if isinstance(invitations, list):
            for invitation in invitations:
                if not isinstance(invitation, dict):
                    continue
                repository = invitation.get("repository", {})
                if (isinstance(repository, dict)
                        and str(repository.get("full_name", "")).casefold() == repo_name.casefold()
                        and isinstance(invitation.get("id"), int)):
                    accepted, _ = _run_gh([
                        "-X", "PATCH", f"user/repository_invitations/{invitation['id']}"
                    ])
                    if accepted:
                        success, retry_message = clone_repo(repo_url, cache_dir)
                        if success:
                            return RepositoryConnection(True, f"已自动接受仓库邀请；{retry_message}")
                        message = retry_message
                    else:
                        return RepositoryConnection(
                            False, "发现待处理邀请，但自动接受失败；请在 GitHub 通知中接受邀请后重试")
                    break

    if not _is_access_error(message):
        return RepositoryConnection(False, message)
    return RepositoryConnection(
        False,
        "仓库地址有误或尚无权限。请核对地址；若为私有仓库，请让拥有者邀请你，"
        "然后重新检测连接。GitHub 无法由申请者直接提交仓库访问申请。",
        _request_text(repo_name, login_hint),
    )
