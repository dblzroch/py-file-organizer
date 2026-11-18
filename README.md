# py-file-organizer

> Batch file organizer: sort files by extension, date or size with YAML rules, dry-run and undo.

[![CI](https://github.com/dblzroch/py-file-organizer/actions/workflows/ci.yml/badge.svg)](https://github.com/dblzroch/py-file-organizer/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](pyproject.toml)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

Organize a messy folder into subfolders by file extension, modification date or size range.
Rules are declared in YAML. Supports dry-run (preview without moving) and undo of the
last N operations.

## Quickstart

```bash
# Clone
git clone https://github.com/dblzroch/py-file-organizer.git
cd py-file-organizer

# Install (uv)
uv sync --dev

# Preview what would happen (dry-run)
uv run file-organize --dry-run Downloads

# Organize by extension
uv run file-organize --mode extension Downloads

# Undo the last operation
uv run file-organize undo
```

## Commands

| Command | Description |
|---|---|
| `file-organize <folder> [--mode extension|date|size] [--dry-run]` | Organize files in a folder |
| `file-organize undo [--steps N]` | Undo the last N move operations |
| `file-organize init-rules` | Generate a sample `rules.yaml` config |

## How it works

- **CLI**: [Typer](https://typer.tiangolo.com/) commands.
- **Rules**: YAML config file (`rules.yaml`) mapping patterns to destination subfolders.
- **Safety**: dry-run mode shows planned moves without touching the disk.
- **Undo**: operation log enables reverting the last N moves.
- **Tests**: `pytest` with coverage gate at 80%.
- **CI**: GitHub Actions runs ruff, mypy and pytest on every push/PR.

## Tests & quality

```bash
make test      # pytest with coverage
make lint      # ruff + mypy
make fmt       # ruff format
```

## License

MIT
