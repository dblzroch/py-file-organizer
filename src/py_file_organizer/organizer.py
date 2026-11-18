"""File organization engine: move, undo, dry-run."""

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path

from py_file_organizer.models import (
    Operation,
    OrganizeMode,
    OrganizeResult,
    Rule,
)

logger = logging.getLogger(__name__)

OPERATIONS_LOG = (
    Path.home() / ".local" / "share" / "py-file-organizer" / "operations.json"
)


class Organizer:
    """Organizes files into subfolders and keeps a log for undo."""

    def __init__(self, operations_log: Path = OPERATIONS_LOG):
        self.operations_log = operations_log
        self.operations_log.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def organize(
        self,
        folder: Path,
        mode: OrganizeMode,
        rules: list[Rule],
        dry_run: bool = False,
    ) -> OrganizeResult:
        """Move files in ``folder`` according to ``mode`` and ``rules``.

        Args:
            folder: Directory to organize.
            mode: Grouping strategy.
            rules: YAML rules (checked before mode-based fallback).
            dry_run: If True, only log planned moves without touching disk.

        Returns:
            :class:`OrganizeResult` with counts and operations.
        """
        if not folder.is_dir():
            raise NotADirectoryError(f"Not a directory: {folder}")

        operations: list[Operation] = []
        moved = 0
        skipped = 0

        for entry in sorted(folder.iterdir()):
            if not entry.is_file():
                continue

            destination = self._destination_for(entry, folder, rules, mode)
            if destination is None:
                skipped += 1
                continue

            if dry_run:
                logger.info("[dry-run] would move %s -> %s", entry, destination)
                operations.append(Operation(source=entry, destination=destination))
                moved += 1
                continue

            self._move_file(entry, destination)
            operations.append(Operation(source=entry, destination=destination))
            moved += 1

        result = OrganizeResult(moved=moved, skipped=skipped, operations=operations)

        if not dry_run:
            self._append_log(operations)

        return result

    def undo(self, steps: int = 1) -> int:
        """Revert the last ``steps`` move operations.

        Returns:
            Number of operations undone.
        """
        operations = self._read_log()
        if not operations:
            logger.warning("No operations to undo")
            return 0

        to_undo = operations[-steps:]
        undone = 0

        for op in reversed(to_undo):
            if not op.destination.exists():
                logger.warning("Destination missing, skipping undo: %s", op.destination)
                continue

            try:
                shutil.move(str(op.destination), str(op.source))
                undone += 1
                logger.info("Undid move: %s <- %s", op.source, op.destination)
            except OSError as exc:
                logger.error("Failed to undo %s: %s", op.destination, exc)

        # Remove undone entries from the log
        remaining = operations[: len(operations) - steps]
        self._write_log(remaining)
        return undone

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _destination_for(
        self,
        file: Path,
        folder: Path,
        rules: list[Rule],
        mode: OrganizeMode,
    ) -> Path | None:
        """Return the destination path for a file, or None to skip."""
        # Rule-based match first
        for rule in rules:
            if self._matches_rule(file.name, rule.pattern):
                return folder / rule.destination / file.name

        # Mode-based fallback
        if mode == OrganizeMode.extension:
            subfolder = file.suffix.lstrip(".") or "no-extension"
            return folder / subfolder / file.name

        if mode == OrganizeMode.date:
            mtime = datetime.fromtimestamp(file.stat().st_mtime)
            subfolder = mtime.strftime("%Y-%m")
            return folder / subfolder / file.name

        if mode == OrganizeMode.size:
            size = file.stat().st_size
            bucket = self._size_bucket(size)
            return folder / bucket / file.name

        return None

    @staticmethod
    def _matches_rule(filename: str, pattern: str) -> bool:
        """Simple glob match for rule patterns (supports {a,b} alternation)."""
        import fnmatch

        # Handle {a,b,c} alternation
        if "{" in pattern and "}" in pattern:
            start = pattern.index("{")
            end = pattern.index("}")
            prefix = pattern[:start]
            suffix = pattern[end + 1 :]
            options = pattern[start + 1 : end].split(",")
            return any(
                fnmatch.fnmatch(filename, f"{prefix}{opt}{suffix}") for opt in options
            )

        return fnmatch.fnmatch(filename, pattern)

    @staticmethod
    def _size_bucket(size: int) -> str:
        """Group files by size into human-readable buckets."""
        if size < 1024:
            return "tiny"
        if size < 1024 * 1024:
            return "small"
        if size < 100 * 1024 * 1024:
            return "medium"
        return "large"

    def _move_file(self, source: Path, destination: Path) -> None:
        """Move ``source`` to ``destination``, creating parent dirs."""
        destination.parent.mkdir(parents=True, exist_ok=True)
        # Handle name collisions
        if destination.exists():
            stem = source.stem
            suffix = source.suffix
            counter = 1
            while destination.exists():
                destination = destination.parent / f"{stem} ({counter}){suffix}"
                counter += 1
        shutil.move(str(source), str(destination))
        logger.info("Moved %s -> %s", source, destination)

    def _append_log(self, operations: list[Operation]) -> None:
        """Append operations to the JSON log."""
        existing = self._read_log()
        existing.extend(operations)
        self._write_log(existing)

    def _read_log(self) -> list[Operation]:
        """Read all operations from the JSON log."""
        if not self.operations_log.exists():
            return []
        try:
            data = json.loads(self.operations_log.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []
        return [Operation.from_dict(item) for item in data]

    def _write_log(self, operations: list[Operation]) -> None:
        """Write operations to the JSON log."""
        payload = [op.to_dict() for op in operations]
        self.operations_log.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
