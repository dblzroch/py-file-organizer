"""YAML rule loading for py-file-organizer."""

import logging
from pathlib import Path

import yaml  # type: ignore[import-untyped]

from py_file_organizer.models import Rule, RuleAction

logger = logging.getLogger(__name__)

DEFAULT_RULES_FILE = Path("rules.yaml")


def load_rules(path: Path | None = None) -> list[Rule]:
    """Load organizing rules from a YAML file.

    Expected format:
        rules:
          - pattern: "*.pdf"
            destination: "documents"
          - pattern: "*.{jpg,png}"
            destination: "images"

    Args:
        path: YAML file path. Defaults to ``rules.yaml`` in the cwd.

    Returns:
        List of :class:`Rule` objects. Empty list if file missing.
    """
    rules_path = path or DEFAULT_RULES_FILE
    if not rules_path.exists():
        logger.info("No rules file at %s; returning empty rule set", rules_path)
        return []

    with rules_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    raw_rules = data.get("rules", [])
    rules: list[Rule] = []
    for entry in raw_rules:
        rules.append(
            Rule(
                pattern=entry["pattern"],
                destination=entry["destination"],
                action=RuleAction(entry.get("action", "move")),
            )
        )

    logger.info("Loaded %d rules from %s", len(rules), rules_path)
    return rules


def init_rules_file(path: Path = DEFAULT_RULES_FILE) -> None:
    """Write a sample ``rules.yaml`` if it does not exist."""
    if path.exists():
        return

    sample = """rules:
  - pattern: "*.pdf"
    destination: "documents"
  - pattern: "*.{doc,docx,txt,md}"
    destination: "documents"
  - pattern: "*.{jpg,jpeg,png,gif,webp}"
    destination: "images"
  - pattern: "*.{mp4,mov,avi,mkv}"
    destination: "videos"
  - pattern: "*.{mp3,wav,ogg}"
    destination: "audio"
  - pattern: "*.{zip,rar,7z,tar,gz}"
    destination: "archives"
  - pattern: "*.{exe,msi,dmg,pkg}"
    destination: "installers"
"""
    path.write_text(sample, encoding="utf-8")
    logger.info("Wrote sample rules to %s", path)
