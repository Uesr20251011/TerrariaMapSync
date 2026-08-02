"""Git 操作模块 — clone, pull, commit, push"""

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Tuple

from logger import get_logger

log = get_logger()

_CREATION_FLAGS = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
_GH_PATH = r"C:\Program Files\GitHub CLI\gh.exe"
_APP_DIR = os.path.join(os.environ.get("APPDATA", ""), "TerrariaMapHelper")
_FROZEN = getattr(sys, "frozen", False)

# ===== 一次性全局 git 配置（仅首次 import 时执行） =====
_did_init = False


def _init_git_config():
    """一次性配置 git（URL 改写 + 清理坏的 credential helper）"""
    global _did_init
    if _did_init:
        return
    _did_init = True

    log.info("初始化 git 全局配置 (一次性)...")
    cmd = ["git", "config", "--global",
           "url.https://github.com/.insteadOf", "git@github.com:"]
    subprocess.run(cmd, capture_output=True, timeout=10, creationflags=_CREATION_FLAGS)

    # 清理可能残留的坏的 credential.helper
    subprocess.run(
        ["git", "config", "--global", "--unset", "credential.helper"],
        capture_output=True, timeout=5, creationflags=_CREATION_FLAGS,
    )
    subprocess.run(
        ["git", "config", "--global", "--unset-all", "credential.helper"],
        capture_output=True, timeout=5, creationflags=_CREATION_FLAGS,
    )


def _ensure_askpass_cmd() -> str:
    """返回 GIT_ASKPASS 环境变量值"""
    if _FROZEN:
        return f'"{sys.executable}" --askpass'
    else:
        script = os.path.join(_APP_DIR, "git-askpass.py")
        os.makedirs(_APP_DIR, exist_ok=True)
        if not os.path.isfile(script):
            with open(script, "w", encoding="ascii") as f:
                f.write(
                    'import subprocess, sys\r\n'
                    f'r = subprocess.run([r"{_GH_PATH}", "auth", "token"],'
                    f' capture_output=True, text=True, timeout=10,'
                    f' creationflags=0x08000000 if sys.platform == "win32" else 0)\r\n'
                    'if r.returncode == 0:\r\n'
                    '    print(r.stdout.strip())\r\n'
                    'else:\r\n'
                    '    sys.exit(1)\r\n'
                )
        return f"{sys.executable} {script}"


def _build_env() -> dict[str, str]:
    """构建带认证的子进程环境"""
    _init_git_config()
    env = os.environ.copy()
    env["GIT_ASKPASS"] = _ensure_askpass_cmd()
    env["GIT_TERMINAL_PROMPT"] = "0"
    return env


def is_git_installed() -> bool:
    try:
        subprocess.run(["git", "--version"], capture_output=True,
                       check=True, timeout=10, creationflags=_CREATION_FLAGS)
        return True
    except Exception:
        return False


def _run_git(args: list[str], cwd: str) -> Tuple[bool, str]:
    cmd = "git " + " ".join(args)
    log.debug("执行: %s", cmd)
    env = _build_env()
    start = time.time()
    try:
        result = subprocess.run(
            ["git"] + args, cwd=cwd, capture_output=True,
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
        log.info("仓库已存在")
        return (True, "仓库已存在")
    if cache_path.exists():
        import shutil
        shutil.rmtree(cache_path, ignore_errors=True)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    return _run_git(["clone", repo_url, str(cache_path)], str(cache_path.parent))


def pull_repo(cache_dir: str) -> Tuple[bool, str]:
    log.info("=== 拉取更新 ===")
    if not (Path(cache_dir) / ".git").exists():
        return (False, "仓库尚未克隆")
    _run_git(["reset", "--hard", "HEAD"], cache_dir)
    _run_git(["clean", "-fd"], cache_dir)
    return _run_git(["pull", "--rebase"], cache_dir)


def commit_and_push(cache_dir: str, files: list[str], message: str) -> Tuple[bool, str]:
    log.info("=== 提交推送 ===")
    log.info("文件: %s", files)
    if not (Path(cache_dir) / ".git").exists():
        return (False, "仓库尚未克隆")

    ok, msg = _run_git(["add"] + files, cache_dir)
    if not ok:
        return (False, f"git add 失败: {msg}")

    ok, msg = _run_git(["commit", "-m", message], cache_dir)
    if not ok:
        if "nothing to commit" not in msg.lower() and "nothing added" not in msg.lower():
            return (False, f"git commit 失败: {msg}")

    ok, msg = _run_git(["push"], cache_dir)
    if not ok:
        return (False, f"git push 失败: {msg}")

    log.info("提交推送成功")
    return (True, "提交并推送成功")
