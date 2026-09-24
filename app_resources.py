"""Paths for bundled artwork and user-specific cached profile art."""

import os
import sys
from pathlib import Path


def asset_path(name: str) -> Path:
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return root / "assets" / name


def avatar_cache_path(login: str = "") -> Path:
    base = Path(os.environ.get("APPDATA", str(Path.home()))) / "TerrariaMapHelper"
    base.mkdir(parents=True, exist_ok=True)
    safe_login = "".join(char for char in login.lower() if char.isascii() and (char.isalnum() or char == "-"))
    return base / f"github-avatar-{safe_login or 'unknown'}.png"
