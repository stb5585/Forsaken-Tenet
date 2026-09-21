"""Tests for the committed asset budget gate."""

from pathlib import Path

from tools.check_asset_budget import AssetBudget, check_budget, load_budget


def test_committed_asset_budget_passes():
    """Current assets fit both the aggregate and per-file budgets."""
    budget = load_budget()
    result = check_budget(budget)
    assert result.total_bytes <= budget.total_limit_bytes
    assert result.oversized_files == ()


def test_asset_budget_reports_oversized_file(tmp_path: Path):
    """The scanner reports files beyond the individual cap."""
    (tmp_path / "large.bin").write_bytes(b"12345")
    budget = AssetBudget(tmp_path, 2, 10, 4, frozenset())
    result = check_budget(budget)
    assert result.total_bytes == 5
    assert result.oversized_files == ((tmp_path / "large.bin", 5),)
