# Repository Guidelines

## Project Structure & Module Organization

`main.py` starts the PySide6 desktop app. Root modules separate configuration, Git operations, map discovery, and upload/download logic. `ui/` contains the main window, panels, setup wizard, settings dialog, and theme. `tests/` holds `unittest` coverage; `assets/` contains the logo and icon; `docs/screenshots/` contains runtime captures. Generated `build/`, `dist/`, and `*.spec` files are ignored.

## Build, Test, and Development Commands

- `python -m pip install -r requirements.txt` installs PySide6 and GitPython.
- `python main.py` runs the app locally. On Windows, `启动助手.vbs` starts it without a console through the `terraria-sync` Conda environment.
- `python -m compileall -q .` checks Python syntax before submitting changes.
- `python -m unittest discover -s tests -v` runs the regression suite.
- `./build.ps1` packages the windowed Windows executable with PyInstaller.

Git and GitHub CLI are required for repository sync; the first-run wizard checks both.

## Coding Style & Naming Conventions

Use four spaces for indentation, `snake_case` for modules, functions, and variables, and `PascalCase` for Qt classes. Keep UI wiring in `ui/` and filesystem or Git work in the root modules. Follow the existing type hints and short docstrings; preserve UTF-8 handling for Chinese map names and interface text. No formatter or linter is configured, so keep changes consistent with nearby code.

## Testing Guidelines

Add focused `tests/test_*.py` cases with Python `unittest`; there is no numeric coverage target. Check upload/download changes with a disposable world directory and test repository. Verify `.wld`, `.wld.bak`, and `.wld.bak2` behavior without using personal save files.

## Commit & Pull Request Guidelines

Recent commits use short imperative subjects such as `Fix: ...`, `Add ...`, and `Restore ...`; keep that style and identify the affected behavior. Pull requests should describe the change, list checks performed, and link a relevant issue when one exists. Include screenshots for UI changes and explain any Git authentication, map file, or packaging impact.

## Configuration & Security

Runtime configuration and logs live under `%APPDATA%\TerrariaMapHelper`; do not commit them, world files, tokens, or repository cache contents. Authentication goes through GitHub CLI over HTTPS; never log credentials or change global Git settings.
