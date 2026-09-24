"""Checks used by the first-run guide and the settings page."""

import json
import subprocess
import sys
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from tool_paths import find_executable

GIT_DOWNLOAD_URL = "https://git-scm.com/download/win"
GH_DOWNLOAD_URL = "https://cli.github.com/"
_HIDDEN_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


def is_github_repo_url(value: str) -> bool:
    parsed = urlparse(value.strip())
    parts = [part for part in parsed.path.strip("/").split("/") if part]
    return (parsed.scheme == "https" and parsed.hostname == "github.com"
            and len(parts) == 2 and all(part not in (".", "..") for part in parts)
            and not parsed.username and not parsed.query and not parsed.fragment)


def check_git_installation() -> tuple[bool, str]:
    git = find_executable("git")
    if not git:
        return (False, "未检测到 Git，请安装后点击重新检测")
    try:
        result = subprocess.run([git, "--version"], capture_output=True, text=True,
                                timeout=5, creationflags=_HIDDEN_WINDOW)
    except (OSError, subprocess.TimeoutExpired) as error:
        return (False, f"Git 无法运行: {error}")
    return (result.returncode == 0, result.stdout.strip() or "Git 检测失败")


def check_github_cli() -> tuple[bool, str]:
    gh = find_executable("gh")
    if not gh:
        return (False, "未检测到 GitHub CLI，请安装后点击重新检测")
    try:
        result = subprocess.run([gh, "--version"], capture_output=True, text=True,
                                timeout=5, creationflags=_HIDDEN_WINDOW)
    except (OSError, subprocess.TimeoutExpired) as error:
        return (False, f"GitHub CLI 无法运行: {error}")
    return (result.returncode == 0, result.stdout.splitlines()[0] if result.stdout else "GitHub CLI 检测失败")


def check_github_login() -> tuple[bool, str]:
    gh = find_executable("gh")
    if not gh:
        return (False, "请先安装 GitHub CLI")
    try:
        result = subprocess.run([gh, "auth", "status", "--hostname", "github.com"],
                                capture_output=True, text=True, timeout=15,
                                creationflags=_HIDDEN_WINDOW)
    except (OSError, subprocess.TimeoutExpired) as error:
        return (False, f"登录检测失败: {error}")
    if result.returncode == 0:
        return (True, "GitHub 已登录")
    return (False, "尚未登录 GitHub，或登录状态已失效")


def load_github_profile() -> tuple[str, bytes]:
    """Return public login and avatar; do not read or persist the auth token."""
    gh = find_executable("gh")
    if not gh:
        return ("", b"")
    try:
        result = subprocess.run([gh, "api", "user"], capture_output=True,
                                text=True, encoding="utf-8", timeout=15,
                                creationflags=_HIDDEN_WINDOW)
        if result.returncode != 0:
            return ("", b"")
        profile = json.loads(result.stdout)
        login = str(profile.get("login", ""))
        avatar_url = str(profile.get("avatar_url", ""))
        if not login or urlparse(avatar_url).hostname != "avatars.githubusercontent.com":
            return (login, b"")
        try:
            with urlopen(Request(avatar_url, headers={"User-Agent": "TerrariaMapHelper"}), timeout=10) as response:
                avatar = response.read(1_000_001)
            return (login, avatar if len(avatar) <= 1_000_000 else b"")
        except OSError:
            return (login, b"")
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return ("", b"")
