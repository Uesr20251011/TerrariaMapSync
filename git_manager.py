"""Git 操作模块 — clone, pull, commit, push"""

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Tuple

from logger import get_logger

log = get_logger()

_GH_PATH = r"C:\Program Files\GitHub CLI\gh.exe"
_ASKPASS_DIR = os.path.join(os.environ.get("APPDATA", ""), "TerrariaMapHelper")
_ASKPASS_SCRIPT = os.path.join(_ASKPASS_DIR, "git-askpass.py")


def _ensure_askpass_script() -> str:
    """确保 askpass Python 脚本存在，返回 GIT_ASKPASS 值"""
    os.makedirs(_ASKPASS_DIR, exist_ok=True)

    if not os.path.isfile(_ASKPASS_SCRIPT):
        log.info("创建 git-askpass 脚本: %s", _ASKPASS_SCRIPT)
        with open(_ASKPASS_SCRIPT, "w", encoding="ascii") as f:
            f.write(
                'import subprocess, sys\r\n'
                f'r = subprocess.run([r"{_GH_PATH}", "auth", "token"],'
                f' capture_output=True, text=True, timeout=10)\r\n'
                'if r.returncode == 0:\r\n'
                '    print(r.stdout.strip())\r\n'
                'else:\r\n'
                '    sys.exit(1)\r\n'
            )

    return f"{sys.executable} {_ASKPASS_SCRIPT}"


def _setup_auth() -> dict[str, str]:
    """准备带认证信息的环境变量"""
    env = os.environ.copy()
    env["GIT_ASKPASS"] = _ensure_askpass_script()
    env["GIT_TERMINAL_PROMPT"] = "0"

    subprocess.run(
        ["git", "config", "--global",
         "url.https://github.com/.insteadOf", "git@github.com:"],
        capture_output=True, timeout=10,
    )

    return env


def is_git_installed() -> bool:
    """检测系统是否安装了 Git"""
    try:
        subprocess.run(
            ["git", "--version"],
            capture_output=True, check=True, timeout=10,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _run_git(args: list[str], cwd: str) -> Tuple[bool, str]:
    """执行 git 命令，返回 (success, message)"""
    cmd = "git " + " ".join(args)
    log.debug("执行: %s  (cwd: %s)", cmd, cwd)

    env = _setup_auth()
    start = time.time()

    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=120,
            encoding="utf-8",
            env=env,
        )
        elapsed = time.time() - start
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        log.debug("耗时: %.1fs  rc=%d", elapsed, result.returncode)
        if stdout:
            log.debug("stdout: %s", stdout[:500])
        if stderr:
            log.debug("stderr: %s", stderr[:500])

        if result.returncode == 0:
            output = stdout or stderr or "成功"
            log.info("成功: %s -> %s", cmd, output[:200])
            return (True, output)
        else:
            error = stderr or stdout or "未知错误"
            log.error("失败: %s -> %s", cmd, error[:500])
            return (False, error)

    except FileNotFoundError:
        log.critical("Git 未安装")
        return (False, "未找到 Git，请先安装 Git")
    except subprocess.TimeoutExpired:
        log.error("超时: %s (%.1fs)", cmd, time.time() - start)
        return (False, "Git 操作超时，请检查网络")
    except Exception as e:
        log.exception("异常: %s", cmd)
        return (False, f"Git 操作异常: {e}")


def clone_repo(repo_url: str, cache_dir: str) -> Tuple[bool, str]:
    """克隆仓库到本地缓存目录"""
    log.info("=== 开始克隆 ===")
    log.info("URL: %s", repo_url)
    log.info("目标: %s", cache_dir)

    cache_path = Path(cache_dir)

    if cache_path.exists() and (cache_path / ".git").exists():
        log.info("仓库已存在，跳过克隆")
        return (True, "仓库已存在")

    if cache_path.exists():
        import shutil
        log.info("清理旧目录: %s", cache_path)
        shutil.rmtree(cache_path, ignore_errors=True)

    cache_path.parent.mkdir(parents=True, exist_ok=True)

    return _run_git(["clone", repo_url, str(cache_path)], str(cache_path.parent))


def pull_repo(cache_dir: str) -> Tuple[bool, str]:
    """拉取仓库最新内容"""
    log.info("=== 拉取更新 ===")

    if not (Path(cache_dir) / ".git").exists():
        log.error("仓库未克隆: %s", cache_dir)
        return (False, "仓库尚未克隆，请先设置仓库地址")

    return _run_git(["pull", "--rebase"], cache_dir)


def commit_and_push(cache_dir: str, files: list[str], message: str) -> Tuple[bool, str]:
    """添加文件、提交并推送到远程仓库"""
    log.info("=== 提交并推送 ===")
    log.info("文件: %s", files)
    log.info("信息: %s", message)

    if not (Path(cache_dir) / ".git").exists():
        log.error("仓库未克隆")
        return (False, "仓库尚未克隆")

    # git add
    ok, msg = _run_git(["add"] + files, cache_dir)
    if not ok:
        log.error("git add 失败: %s", msg)
        return (False, f"git add 失败: {msg}")

    # git commit
    ok, msg = _run_git(["commit", "-m", message], cache_dir)
    if not ok:
        if "nothing to commit" in msg.lower() or "nothing added" in msg.lower():
            log.info("无变更需要提交")
            pass
        else:
            log.error("git commit 失败: %s", msg)
            return (False, f"git commit 失败: {msg}")

    # git push
    ok, msg = _run_git(["push"], cache_dir)
    if not ok:
        log.error("git push 失败: %s", msg)
        return (False, f"git push 失败: {msg}")

    log.info("提交推送成功")
    return (True, "提交并推送成功")
