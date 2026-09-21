#!/usr/bin/env python3
"""Enforce repository asset size budgets from a committed manifest."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = Path(__file__).with_name("asset_budget.json")


@dataclass(frozen=True)
class AssetBudget:
    """Validated asset size constraints."""

    asset_root: Path
    baseline_bytes: int
    total_allowance_bytes: int
    per_file_limit_bytes: int
    excluded_suffixes: frozenset[str]

    @property
    def total_limit_bytes(self) -> int:
        """Return the maximum allowed combined asset size."""
        return self.baseline_bytes + self.total_allowance_bytes


@dataclass(frozen=True)
class AssetBudgetResult:
    """Sizes and violations observed by one budget scan."""

    total_bytes: int
    file_count: int
    oversized_files: tuple[tuple[Path, int], ...]


def _positive_int(data: dict[str, Any], key: str) -> int:
    value = data.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{key} must be a non-negative integer")
    return value


def load_budget(manifest_path: Path = DEFAULT_MANIFEST) -> AssetBudget:
    """Load and validate an asset budget manifest."""
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("asset budget manifest must contain an object")
    root_value = data.get("asset_root")
    if not isinstance(root_value, str) or not root_value:
        raise ValueError("asset_root must be a non-empty string")
    suffixes = data.get("excluded_suffixes", [])
    if not isinstance(suffixes, list) or not all(isinstance(value, str) for value in suffixes):
        raise ValueError("excluded_suffixes must be a list of strings")
    return AssetBudget(
        asset_root=REPOSITORY_ROOT / root_value,
        baseline_bytes=_positive_int(data, "baseline_bytes"),
        total_allowance_bytes=_positive_int(data, "total_allowance_bytes"),
        per_file_limit_bytes=_positive_int(data, "per_file_limit_bytes"),
        excluded_suffixes=frozenset(suffixes),
    )


def check_budget(budget: AssetBudget) -> AssetBudgetResult:
    """Scan assets and return exact totals and per-file violations."""
    if not budget.asset_root.is_dir():
        raise FileNotFoundError(f"asset root does not exist: {budget.asset_root}")
    files = sorted(
        path
        for path in budget.asset_root.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.suffix.lower() not in budget.excluded_suffixes
    )
    sizes = [(path, path.stat().st_size) for path in files]
    return AssetBudgetResult(
        total_bytes=sum(size for _, size in sizes),
        file_count=len(sizes),
        oversized_files=tuple(
            (path, size) for path, size in sizes if size > budget.per_file_limit_bytes
        ),
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run the asset budget check and return a command-line status code."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args(argv)
    budget = load_budget(args.manifest)
    result = check_budget(budget)
    print(
        f"assets: {result.file_count} files, {result.total_bytes:,} bytes "
        f"(limit {budget.total_limit_bytes:,})"
    )
    for path, size in result.oversized_files:
        print(f"oversized: {path.relative_to(REPOSITORY_ROOT)} ({size:,} bytes)")
    if result.total_bytes > budget.total_limit_bytes:
        print(f"asset total exceeds budget by {result.total_bytes - budget.total_limit_bytes:,} bytes")
        return 1
    return 1 if result.oversized_files else 0


if __name__ == "__main__":
    raise SystemExit(main())
