"""Git 操作模块 — clone, pull, commit, push"""

import os
import json
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Tuple

from logger import get_logger
from tool_paths import find_executable

log = get_logger()

_CREATION_FLAGS = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


def _commit_identity_args(cache_dir: str) -> tuple[list[str], str]:
    """Use the user's GitHub no-reply identity when Git has no local identity."""
    name_ok, _ = _run_git(["config", "user.name"], cache_dir)
    email_ok, _ = _run_git(["config", "user.email"], cache_dir)
    if name_ok and email_ok:
        return ([], "")
    gh = find_executable("gh")
    if not gh:
        return ([], "请先在使用向导中登录 GitHub")
    try:
        result = subprocess.run([gh, "api", "user", "--jq", "{login: .login, id: .id}"],
                                capture_output=True, text=True, encoding="utf-8",
                                timeout=15, creationflags=_CREATION_FLAGS)
        if result.returncode != 0:
            return ([], "无法取得 GitHub 账号信息，请在设置中重新检测登录")
        profile = json.loads(result.stdout)
        login, user_id = profile.get("login"), profile.get("id")
        if not isinstance(login, str) or not login or not isinstance(user_id, int):
            return ([], "GitHub 账号信息不完整")
        return (["-c", f"user.name={login}", "-c",
                 f"user.email={user_id}+{login}@users.noreply.github.com"], "")
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return ([], "无法取得 GitHub 账号信息，请在设置中重新检测登录")


def _build_env() -> dict[str, str]:
    """构建带认证的子进程环境"""
    env = os.environ.copy()
    env.pop("GIT_ASKPASS", None)
    env["GIT_TERMINAL_PROMPT"] = "0"
    # 只影响本次 Git 命令，不改动用户的全局 Git 设置。
    index = int(env.get("GIT_CONFIG_COUNT", "0"))
    env[f"GIT_CONFIG_KEY_{index}"] = "url.https://github.com/.insteadOf"
    env[f"GIT_CONFIG_VALUE_{index}"] = "git@github.com:"
    env[f"GIT_CONFIG_KEY_{index + 1}"] = "credential.helper"
    env[f"GIT_CONFIG_VALUE_{index + 1}"] = ""
    gh = find_executable("gh")
    if gh:
        env[f"GIT_CONFIG_KEY_{index + 2}"] = "credential.https://github.com.helper"
        env[f"GIT_CONFIG_VALUE_{index + 2}"] = f'!"{gh}" auth git-credential'
    env["GIT_CONFIG_COUNT"] = str(index + (3 if gh else 2))
    return env


def is_git_installed() -> bool:
    git = find_executable("git")
    if not git:
        return False
    try:
        subprocess.run([git, "--version"], capture_output=True,
                       check=True, timeout=10, creationflags=_CREATION_FLAGS)
        return True
    except Exception:
        return False


def _run_git(args: list[str], cwd: str) -> Tuple[bool, str]:
    cmd = "git " + " ".join(args)
    log.debug("执行: %s", cmd)
    env = _build_env()
    git = find_executable("git")
    if not git:
        return (False, "未找到 Git，请先安装 Git")
    start = time.time()
    try:
        result = subprocess.run(
            [git] + args, cwd=cwd, capture_output=True,
            text=True, timeout=120, encoding="utf-8",
            env=env, creationflags=_CREATION_FLAGS,
        )
        elapsed = time.time() - start
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        log.debug("耗时: %.1fs rc=%d", elapsed, result.returncode)
        if stdout:
            log.debug("stdout: %s", stdout[:500])
        if stderr:
            stderr_clean = "\n".join(
                line for line in stderr.split("\n")
                if "gh auth git-credential" not in line
            ).strip()
            if stderr_clean:
                log.debug("stderr: %s", stderr_clean[:500])

        if result.returncode == 0:
            output = stdout or "成功"
            log.info("OK: %s (%.1fs)", cmd, elapsed)
            return (True, output)
        else:
            error = stderr or stdout or "未知错误"
            log.error("FAIL: %s -> %s", cmd, error[:500])
            return (False, error)
    except subprocess.TimeoutExpired:
        log.error("超时: %s (%.1fs)", cmd, time.time() - start)
        return (False, "Git 操作超时，请检查网络")
    except FileNotFoundError:
        return (False, "未找到 Git，请先安装 Git")
    except Exception as e:
        log.exception("异常: %s", cmd)
        return (False, f"Git 操作异常: {e}")


def clone_repo(repo_url: str, cache_dir: str) -> Tuple[bool, str]:
    log.info("=== 克隆仓库 ===")
    log.info("URL: %s", repo_url)
    cache_path = Path(cache_dir)
    if cache_path.exists() and (cache_path / ".git").exists():
        ok, origin = _run_git(["remote", "get-url", "origin"], cache_dir)
        if not ok:
            return (False, f"无法读取当前仓库地址: {origin}")
        if origin.rstrip("/") == repo_url.rstrip("/"):
            return pull_repo(cache_dir)

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    if not cache_path.exists():
        return _run_git(["clone", repo_url, str(cache_path)], str(cache_path.parent))

    # 先完整克隆新仓库，再替换缓存；保留旧缓存以便找回未推送的提交。
    staged = Path(tempfile.mkdtemp(prefix=f"{cache_path.name}-new-", dir=cache_path.parent))
    backup = cache_path.with_name(f"{cache_path.name}.previous-{uuid.uuid4().hex[:8]}")
    try:
        ok, message = _run_git(["clone", repo_url, str(staged)], str(cache_path.parent))
        if not ok:
            return (False, message)
        cache_path.rename(backup)
        try:
            staged.rename(cache_path)
        except OSError:
            backup.rename(cache_path)
            raise
        log.info("旧仓库缓存已保留在 %s", backup)
        return (True, "仓库已切换并更新")
    except OSError as e:
        return (False, f"切换仓库失败: {e}")
    finally:
        if staged.exists():
            shutil.rmtree(staged)


def pull_repo(cache_dir: str) -> Tuple[bool, str]:
    log.info("=== 拉取更新 ===")
    if not (Path(cache_dir) / ".git").exists():
        return (False, "仓库尚未克隆")
    return _run_git(["pull", "--rebase"], cache_dir)


def commit_and_push(cache_dir: str, files: list[str], message: str) -> Tuple[bool, str]:
    log.info("=== 提交推送 ===")
    log.info("文件: %s", files)
    if not (Path(cache_dir) / ".git").exists():
        return (False, "仓库尚未克隆")

    ok, msg = _run_git(["add"] + files, cache_dir)
    if not ok:
        return (False, f"git add 失败: {msg}")

    identity_args, identity_error = _commit_identity_args(cache_dir)
    if identity_error:
        _run_git(["reset", "--"] + files, cache_dir)
        return (False, identity_error)

    ok, msg = _run_git(identity_args + ["commit", "-m", message], cache_dir)
    if not ok:
        if "nothing to commit" not in msg.lower() and "nothing added" not in msg.lower():
            _run_git(["reset", "--"] + files, cache_dir)
            return (False, f"git commit 失败: {msg}")

    ok, msg = _run_git(["push"], cache_dir)
    if not ok:
        return (False, f"git push 失败: {msg}")

    log.info("提交推送成功")
    return (True, "提交并推送成功")
