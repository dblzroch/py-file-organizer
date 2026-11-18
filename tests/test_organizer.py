"""Tests for py-file-organizer models, rules, organizer and CLI."""

from datetime import datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

from py_file_organizer.cli import app
from py_file_organizer.models import (
    Operation,
    OrganizeMode,
    OrganizeResult,
    Rule,
    RuleAction,
)
from py_file_organizer.organizer import Organizer
from py_file_organizer.rules import init_rules_file, load_rules


# ------------------------------------------------------------------
# Models
# ------------------------------------------------------------------
def test_task_rule_defaults():
    rule = Rule(pattern="*.pdf", destination="documents")
    assert rule.pattern == "*.pdf"
    assert rule.destination == "documents"
    assert rule.action == RuleAction.move


def test_operation_roundtrip():
    op = Operation(source=Path("/a/b.txt"), destination=Path("/c/b.txt"))
    data = op.to_dict()
    restored = Operation.from_dict(data)
    assert restored.source == op.source
    assert restored.destination == op.destination


def test_organize_result_summary():
    result = OrganizeResult(moved=3, skipped=2)
    assert "3 moved" in result.summary()
    assert "2 skipped" in result.summary()


# ------------------------------------------------------------------
# Rules
# ------------------------------------------------------------------
def test_load_rules_missing_file():
    assert load_rules(Path("/nonexistent/rules.yaml")) == []


def test_init_rules_file_creates_sample(tmp_path):
    target = tmp_path / "rules.yaml"
    init_rules_file(target)
    assert target.exists()
    content = target.read_text(encoding="utf-8")
    assert "rules:" in content
    assert "*.pdf" in content


def test_load_rules_parses_yaml(tmp_path):
    target = tmp_path / "rules.yaml"
    target.write_text(
        "rules:\n  - pattern: '*.png'\n    destination: 'images'\n",
        encoding="utf-8",
    )
    rules = load_rules(target)
    assert len(rules) == 1
    assert rules[0].pattern == "*.png"
    assert rules[0].destination == "images"


# ------------------------------------------------------------------
# Organizer
# ------------------------------------------------------------------
def test_organize_by_extension(tmp_path):
    folder = tmp_path / "messy"
    folder.mkdir()
    (folder / "a.txt").write_text("hello")
    (folder / "b.pdf").write_text("world")

    organizer = Organizer(operations_log=tmp_path / "ops.json")
    result = organizer.organize(folder, OrganizeMode.extension, [], dry_run=False)

    assert result.moved == 2
    assert (folder / "txt" / "a.txt").exists()
    assert (folder / "pdf" / "b.pdf").exists()
    assert not (folder / "a.txt").exists()


def test_organize_dry_run(tmp_path):
    folder = tmp_path / "messy"
    folder.mkdir()
    (folder / "a.txt").write_text("hello")

    organizer = Organizer(operations_log=tmp_path / "ops.json")
    result = organizer.organize(folder, OrganizeMode.extension, [], dry_run=True)

    assert result.moved == 1
    assert (folder / "a.txt").exists()  # untouched


def test_organize_skips_non_files(tmp_path):
    folder = tmp_path / "messy"
    folder.mkdir()
    sub = folder / "subdir"
    sub.mkdir()
    (sub / "nested.txt").write_text("x")

    organizer = Organizer(operations_log=tmp_path / "ops.json")
    result = organizer.organize(folder, OrganizeMode.extension, [], dry_run=False)

    assert result.moved == 0
    assert result.skipped == 0


def test_undo_reverts_move(tmp_path):
    folder = tmp_path / "messy"
    folder.mkdir()
    src = folder / "a.txt"
    src.write_text("hello")

    ops_log = tmp_path / "ops.json"
    organizer = Organizer(operations_log=ops_log)
    organizer.organize(folder, OrganizeMode.extension, [], dry_run=False)

    assert (folder / "txt" / "a.txt").exists()
    undone = organizer.undo(steps=1)
    assert undone == 1
    assert src.exists()
    assert not (folder / "txt" / "a.txt").exists()


def test_undo_nothing_to_undo(tmp_path):
    organizer = Organizer(operations_log=tmp_path / "ops.json")
    assert organizer.undo(steps=1) == 0


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------
def test_cli_organize(tmp_path):
    folder = tmp_path / "messy"
    folder.mkdir()
    (folder / "a.txt").write_text("hello")

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["organize", str(folder), "--mode", "extension", "--dry-run"],
    )
    assert result.exit_code == 0
    assert "Dry-run" in result.output


def test_cli_undo(tmp_path):
    runner = CliRunner()
    result = runner.invoke(app, ["undo", "--steps", "1"])
    assert result.exit_code == 0


def test_cli_init_rules(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["init-rules"])
    assert result.exit_code == 0
    assert Path("rules.yaml").exists()


# ------------------------------------------------------------------
# Organizer — additional coverage
# ------------------------------------------------------------------
def test_organize_by_date(tmp_path):
    folder = tmp_path / "messy"
    folder.mkdir()
    (folder / "a.txt").write_text("hello")

    organizer = Organizer(operations_log=tmp_path / "ops.json")
    result = organizer.organize(folder, OrganizeMode.date, [], dry_run=False)

    assert result.moved == 1
    year_month = datetime.now().strftime("%Y-%m")
    assert (folder / year_month / "a.txt").exists()


def test_organize_by_size(tmp_path):
    folder = tmp_path / "messy"
    folder.mkdir()
    (folder / "small.txt").write_text("x")  # < 1 KB → tiny
    (folder / "big.bin").write_text("y" * 2_000_000)  # 2 MB → medium

    organizer = Organizer(operations_log=tmp_path / "ops.json")
    result = organizer.organize(folder, OrganizeMode.size, [], dry_run=False)

    assert result.moved == 2
    assert (folder / "tiny" / "small.txt").exists()
    assert (folder / "medium" / "big.bin").exists()


def test_organize_with_rules(tmp_path):
    folder = tmp_path / "messy"
    folder.mkdir()
    (folder / "report.pdf").write_text("hello")

    rules = [Rule(pattern="*.pdf", destination="documents")]
    organizer = Organizer(operations_log=tmp_path / "ops.json")
    result = organizer.organize(folder, OrganizeMode.extension, rules, dry_run=False)

    assert result.moved == 1
    assert (folder / "documents" / "report.pdf").exists()


def test_organize_rule_with_alternation(tmp_path):
    folder = tmp_path / "messy"
    folder.mkdir()
    (folder / "photo.jpg").write_text("x")
    (folder / "photo.png").write_text("y")

    rules = [Rule(pattern="*.{jpg,png}", destination="images")]
    organizer = Organizer(operations_log=tmp_path / "ops.json")
    result = organizer.organize(folder, OrganizeMode.extension, rules, dry_run=False)

    assert result.moved == 2
    assert (folder / "images" / "photo.jpg").exists()
    assert (folder / "images" / "photo.png").exists()


def test_organize_nonexistent_folder(tmp_path):
    organizer = Organizer(operations_log=tmp_path / "ops.json")
    with pytest.raises(NotADirectoryError):
        organizer.organize(tmp_path / "nope", OrganizeMode.extension, [])


def test_organize_name_collision(tmp_path):
    folder = tmp_path / "messy"
    folder.mkdir()
    (folder / "a.txt").write_text("first")
    # Create existing destination to force collision
    (folder / "txt").mkdir()
    (folder / "txt" / "a.txt").write_text("existing")

    organizer = Organizer(operations_log=tmp_path / "ops.json")
    result = organizer.organize(folder, OrganizeMode.extension, [], dry_run=False)

    assert result.moved == 1
    assert (folder / "txt" / "a (1).txt").exists()


def test_undo_multiple_steps(tmp_path):
    folder = tmp_path / "messy"
    folder.mkdir()
    (folder / "a.txt").write_text("a")
    (folder / "b.txt").write_text("b")

    ops_log = tmp_path / "ops.json"
    organizer = Organizer(operations_log=ops_log)
    organizer.organize(folder, OrganizeMode.extension, [], dry_run=False)

    undone = organizer.undo(steps=2)
    assert undone == 2
    assert (folder / "a.txt").exists()
    assert (folder / "b.txt").exists()


def test_undo_destination_missing(tmp_path):
    folder = tmp_path / "messy"
    folder.mkdir()
    src = folder / "a.txt"
    src.write_text("hello")

    ops_log = tmp_path / "ops.json"
    organizer = Organizer(operations_log=ops_log)
    organizer.organize(folder, OrganizeMode.extension, [], dry_run=False)

    # Remove destination before undo
    dest = folder / "txt" / "a.txt"
    dest.unlink()

    undone = organizer.undo(steps=1)
    assert undone == 0  # destination missing, skipped


# ------------------------------------------------------------------
# CLI — additional coverage
# ------------------------------------------------------------------
def test_cli_organize_not_a_directory(tmp_path):
    runner = CliRunner()
    result = runner.invoke(app, ["organize", str(tmp_path / "nope")])
    assert result.exit_code == 1


def test_cli_organize_real(tmp_path):
    folder = tmp_path / "messy"
    folder.mkdir()
    (folder / "a.txt").write_text("hello")

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["organize", str(folder), "--mode", "extension"],
    )
    assert result.exit_code == 0
    assert "Done" in result.output or "Moved" in result.output
