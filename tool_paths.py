"""Locate Git tools even when a Windows installer has not refreshed this process's PATH."""

import os
import shutil
from pathlib import Path


def find_executable(name: str) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    if os.name != "nt":
        return None

    program_files = [os.environ.get("ProgramFiles", r"C:\Program Files"),
                     os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")]
    relative = {
        "git": Path("Git") / "cmd" / "git.exe",
        "gh": Path("GitHub CLI") / "gh.exe",
    }.get(name)
    if relative is None:
        return None
    for base in program_files:
        candidate = Path(base) / relative
        if candidate.is_file():
            return str(candidate)
    return None
