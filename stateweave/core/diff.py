"""
State Diff Engine — Structural diff between StateWeavePayload instances.
=========================================================================
Computes human-readable diffs showing what changed between two agent states.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from stateweave.schema.v1 import StateWeavePayload

logger = logging.getLogger("stateweave.core.diff")


@dataclass
class DiffEntry:
    """A single difference between two states."""

    path: str
    diff_type: str  # "added", "removed", "modified"
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None

    def __str__(self) -> str:
        if self.diff_type == "added":
            return f"  + {self.path}: {_truncate(self.new_value)}"
        elif self.diff_type == "removed":
            return f"  - {self.path}: {_truncate(self.old_value)}"
        else:
            return f"  ~ {self.path}: {_truncate(self.old_value)} → {_truncate(self.new_value)}"


@dataclass
class StateDiff:
    """Result of diffing two StateWeavePayload instances."""

    entries: List[DiffEntry] = field(default_factory=list)
    summary: str = ""
    state_a_framework: str = ""
    state_b_framework: str = ""

    @property
    def has_changes(self) -> bool:
        return len(self.entries) > 0

    @property
    def added_count(self) -> int:
        return sum(1 for e in self.entries if e.diff_type == "added")

    @property
    def removed_count(self) -> int:
        return sum(1 for e in self.entries if e.diff_type == "removed")

    @property
    def modified_count(self) -> int:
        return sum(1 for e in self.entries if e.diff_type == "modified")

    def to_report(self) -> str:
        """Generate a human-readable diff report."""
        lines = [
            "═" * 60,
            "🔍 STATEWEAVE DIFF REPORT",
            "═" * 60,
            f"  State A: {self.state_a_framework}",
            f"  State B: {self.state_b_framework}",
            f"  Changes: {len(self.entries)} "
            f"(+{self.added_count} -{self.removed_count} ~{self.modified_count})",
            "",
        ]

        if not self.has_changes:
            lines.append("  ✅ States are identical")
        else:
            # Group entries by top-level path
            groups: Dict[str, List[DiffEntry]] = {}
            for entry in self.entries:
                top_key = entry.path.split(".")[0]
                if top_key not in groups:
                    groups[top_key] = []
                groups[top_key].append(entry)

            for group_name, entries in sorted(groups.items()):
                lines.append(f"  [{group_name}]")
                for entry in entries:
                    lines.append(str(entry))
                lines.append("")

        if self.summary:
            lines.append(f"  Summary: {self.summary}")

        lines.append("═" * 60)
        return "\n".join(lines)


def diff_payloads(
    state_a: StateWeavePayload,
    state_b: StateWeavePayload,
) -> StateDiff:
    """Compute the structural diff between two StateWeavePayload instances.

    Args:
        state_a: The "before" state.
        state_b: The "after" state.

    Returns:
        StateDiff with all differences enumerated.
    """
    result = StateDiff(
        state_a_framework=state_a.source_framework,
        state_b_framework=state_b.source_framework,
    )

    dict_a = state_a.model_dump(mode="json")
    dict_b = state_b.model_dump(mode="json")

    _diff_dicts(dict_a, dict_b, "", result.entries)

    # Build summary
    parts = []
    if result.added_count:
        parts.append(f"{result.added_count} added")
    if result.removed_count:
        parts.append(f"{result.removed_count} removed")
    if result.modified_count:
        parts.append(f"{result.modified_count} modified")
    result.summary = ", ".join(parts) if parts else "No changes"

    return result


def _diff_dicts(
    a: Dict[str, Any],
    b: Dict[str, Any],
    prefix: str,
    entries: List[DiffEntry],
) -> None:
    """Recursively diff two dictionaries."""
    all_keys = set(a.keys()) | set(b.keys())

    for key in sorted(all_keys):
        path = f"{prefix}.{key}" if prefix else key
        in_a = key in a
        in_b = key in b

        if in_a and not in_b:
            entries.append(
                DiffEntry(
                    path=path,
                    diff_type="removed",
                    old_value=a[key],
                )
            )
        elif not in_a and in_b:
            entries.append(
                DiffEntry(
                    path=path,
                    diff_type="added",
                    new_value=b[key],
                )
            )
        elif a[key] != b[key]:
            # Both exist but differ
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                _diff_dicts(a[key], b[key], path, entries)
            elif isinstance(a[key], list) and isinstance(b[key], list):
                _diff_lists(a[key], b[key], path, entries)
            else:
                entries.append(
                    DiffEntry(
                        path=path,
                        diff_type="modified",
                        old_value=a[key],
                        new_value=b[key],
                    )
                )


def _diff_lists(
    a: List[Any],
    b: List[Any],
    prefix: str,
    entries: List[DiffEntry],
) -> None:
    """Diff two lists by index."""
    max_len = max(len(a), len(b))
    for i in range(max_len):
        path = f"{prefix}[{i}]"
        if i >= len(a):
            entries.append(
                DiffEntry(
                    path=path,
                    diff_type="added",
                    new_value=b[i],
                )
            )
        elif i >= len(b):
            entries.append(
                DiffEntry(
                    path=path,
                    diff_type="removed",
                    old_value=a[i],
                )
            )
        elif a[i] != b[i]:
            if isinstance(a[i], dict) and isinstance(b[i], dict):
                _diff_dicts(a[i], b[i], path, entries)
            else:
                entries.append(
                    DiffEntry(
                        path=path,
                        diff_type="modified",
                        old_value=a[i],
                        new_value=b[i],
                    )
                )


def _truncate(value: Any, max_len: int = 80) -> str:
    """Truncate a value for display purposes."""
    s = repr(value)
    if len(s) > max_len:
        return s[: max_len - 3] + "..."
    return s
