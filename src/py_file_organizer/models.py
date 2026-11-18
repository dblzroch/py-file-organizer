"""Domain models for py-file-organizer."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path


class OrganizeMode(StrEnum):
    """Strategy for grouping files."""

    extension = "extension"
    date = "date"
    size = "size"


class RuleAction(StrEnum):
    """What a rule does with a matching file."""

    move = "move"


@dataclass
class Rule:
    """A single YAML rule mapping a pattern to a destination folder."""

    pattern: str
    destination: str
    action: RuleAction = RuleAction.move


@dataclass
class Operation:
    """Record of one file move, kept for undo support."""

    source: Path
    destination: Path
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, str]:
        return {
            "source": str(self.source),
            "destination": str(self.destination),
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> "Operation":
        return cls(
            source=Path(data["source"]),
            destination=Path(data["destination"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )


@dataclass
class OrganizeResult:
    """Outcome of an organize run."""

    moved: int
    skipped: int
    operations: list[Operation] = field(default_factory=list)

    def summary(self) -> str:
        return f"{self.moved} moved, {self.skipped} skipped"
